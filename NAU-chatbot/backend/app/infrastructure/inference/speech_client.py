from __future__ import annotations

import httpx

from app.core.config import Settings
from app.core.exceptions import AppError, DependencyUnavailableError


class HttpSpeechClient:
    def __init__(self, settings: Settings) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.speech_inference_base_url.rstrip("/"),
            timeout=httpx.Timeout(settings.inference_timeout_seconds),
            headers={
                "X-Inference-Token": settings.inference_service_token.get_secret_value()
            },
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def transcribe_audio(
        self,
        audio: bytes,
        *,
        content_type: str,
        filename: str,
    ) -> str:
        safe_filename = filename.encode("ascii", errors="ignore").decode() or "recording.webm"
        try:
            response = await self._client.post(
                "/v1/speech/transcribe",
                content=audio,
                headers={
                    "Content-Type": content_type,
                    "X-Audio-Filename": safe_filename,
                },
            )
            if response.status_code in {415, 422}:
                raise AppError(
                    "SPEECH_TRANSCRIPTION_FAILED",
                    "Impossible de transcrire cet enregistrement audio.",
                    422,
                )
            response.raise_for_status()
            result = response.json()
            text = result.get("text") if isinstance(result, dict) else None
            if not isinstance(text, str) or not text.strip():
                raise ValueError("empty speech transcription")
            return text.strip()
        except AppError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise DependencyUnavailableError("speech") from exc

    async def close(self) -> None:
        await self._client.aclose()
