from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.core.config import Settings
from app.core.dependencies import (
    client_bucket,
    rate_limiter,
    settings_dependency,
    speech_inference_dependency,
)
from app.core.exceptions import AppError
from app.infrastructure.inference import HttpSpeechClient
from app.models.schemas.speech import SpeechTranscriptionResponse
from app.services.memory.rate_limiter import RedisRateLimiter


router = APIRouter(prefix="/speech", tags=["speech"])
AudioUpload = Annotated[UploadFile, File(description="Audio à transcrire")]

ALLOWED_AUDIO_MIME_TYPES = frozenset(
    {
        "audio/webm",
        "video/webm",
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/vnd.wave",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "video/mp4",
        "audio/x-m4a",
        "audio/m4a",
        "audio/ogg",
        "application/ogg",
        "application/octet-stream",
    }
)
ALLOWED_AUDIO_SUFFIXES = frozenset(
    {".webm", ".wav", ".mp3", ".mp4", ".m4a", ".ogg", ".oga"}
)


async def _read_audio(audio: UploadFile, max_bytes: int) -> bytes:
    content_type = (audio.content_type or "").lower().split(";", 1)[0].strip()
    suffix = Path(audio.filename or "").suffix.lower()
    if content_type not in ALLOWED_AUDIO_MIME_TYPES:
        raise AppError(
            "UNSUPPORTED_AUDIO_TYPE",
            "Ce format audio n’est pas pris en charge.",
            415,
        )
    if content_type == "application/octet-stream" and suffix not in ALLOWED_AUDIO_SUFFIXES:
        raise AppError(
            "UNSUPPORTED_AUDIO_TYPE",
            "Ce format audio n’est pas pris en charge.",
            415,
        )

    chunks: list[bytes] = []
    received = 0
    while chunk := await audio.read(1_048_576):
        received += len(chunk)
        if received > max_bytes:
            raise AppError(
                "AUDIO_TOO_LARGE",
                "L’enregistrement audio est trop volumineux.",
                413,
            )
        chunks.append(chunk)
    if received == 0:
        raise AppError("EMPTY_AUDIO", "L’enregistrement audio est vide.", 422)
    return b"".join(chunks)


@router.post("/transcribe", response_model=SpeechTranscriptionResponse)
async def transcribe_audio(
    request: Request,
    audio: AudioUpload,
    inference: HttpSpeechClient = Depends(speech_inference_dependency),
    limiter: RedisRateLimiter = Depends(rate_limiter),
    settings: Settings = Depends(settings_dependency),
) -> SpeechTranscriptionResponse:
    await limiter.enforce(
        client_bucket(request, "speech", settings),
        settings.speech_rate_limit_per_minute,
    )
    try:
        payload = await _read_audio(audio, settings.speech_max_upload_bytes)
        text = await inference.transcribe_audio(
            payload,
            content_type=audio.content_type or "application/octet-stream",
            filename=audio.filename or "recording.webm",
        )
        return SpeechTranscriptionResponse(text=text)
    finally:
        await audio.close()
