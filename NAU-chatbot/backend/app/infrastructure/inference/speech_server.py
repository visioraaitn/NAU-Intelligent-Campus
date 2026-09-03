from __future__ import annotations

import hmac
import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status

from app.core.config import get_settings, validate_inference_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.services.speech import (
    AudioConversionError,
    EmptyTranscriptionError,
    WhisperInferenceError,
    WhisperService,
    WhisperUnavailableError,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    validate_inference_settings(settings)
    configure_logging(settings)
    speech = WhisperService()
    app.state.speech = speech
    app.state.load_error = None
    try:
        await speech.load()
    except Exception as exc:
        app.state.load_error = type(exc).__name__
        logger.exception("WHISPER_MODEL_LOAD_FAILED")
    yield


app = FastAPI(
    title="IIT Internal Speech Inference",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_bytes=get_settings().speech_max_upload_bytes,
)


def authorize(x_inference_token: str = Header(default="")) -> None:
    expected = get_settings().inference_service_token.get_secret_value()
    if not expected or not hmac.compare_digest(x_inference_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.get("/health")
async def health(request: Request) -> dict[str, object]:
    speech: WhisperService = request.app.state.speech
    return {"ready": speech.ready, "error": request.app.state.load_error}


@app.post("/v1/speech/transcribe", dependencies=[Depends(authorize)])
async def transcribe_speech(
    request: Request,
    x_audio_filename: str = Header(default="recording.webm"),
) -> dict[str, str]:
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="empty audio")

    suffix = Path(x_audio_filename).suffix.lower()
    if suffix not in {".webm", ".wav", ".mp3", ".mp4", ".m4a", ".ogg", ".oga"}:
        suffix = ".audio"

    service: WhisperService = request.app.state.speech
    with tempfile.TemporaryDirectory(prefix="iit-whisper-") as directory:
        source_path = Path(directory) / f"source{suffix}"
        try:
            source_path.write_bytes(audio)
            return {"text": await service.transcribe(source_path)}
        except (AudioConversionError, EmptyTranscriptionError) as exc:
            logger.warning(
                "WHISPER_AUDIO_REJECTED",
                extra={"event_fields": {"error": type(exc).__name__}},
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="audio transcription failed",
            ) from exc
        except (WhisperUnavailableError, WhisperInferenceError) as exc:
            cause = exc.__cause__
            logger.error(
                "WHISPER_TRANSCRIPTION_UNAVAILABLE",
                extra={
                    "event_fields": {
                        "error": type(exc).__name__,
                        "cause": type(cause).__name__ if cause else None,
                        "detail": str(cause) if cause else str(exc),
                    }
                },
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="speech service unavailable",
            ) from exc
        finally:
            source_path.unlink(missing_ok=True)
