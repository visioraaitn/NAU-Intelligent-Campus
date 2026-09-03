from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)

MODEL_ID = "oddadmix/Whisperv3-tunisian-codeswitch"


class WhisperUnavailableError(RuntimeError):
    pass


class AudioConversionError(RuntimeError):
    pass


class WhisperInferenceError(RuntimeError):
    pass


class EmptyTranscriptionError(RuntimeError):
    pass


class WhisperService:
    """Own the validated Tunisian Whisper pipeline and serialize inference."""

    def __init__(self) -> None:
        self._asr: Any | None = None
        self._inference_lock = asyncio.Semaphore(1)

    @property
    def ready(self) -> bool:
        return self._asr is not None

    async def load(self) -> None:
        if self._asr is not None:
            return
        self._asr = await asyncio.to_thread(self._load_pipeline)

    @staticmethod
    def _load_pipeline() -> Any:
        import torch
        from transformers import (
            AutoModelForSpeechSeq2Seq,
            AutoProcessor,
            pipeline,
        )

        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        pipeline_device = 0 if torch.cuda.is_available() else -1
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        logger.info(
            "WHISPER_MODEL_LOADING",
            extra={"event_fields": {"model_id": MODEL_ID, "device": device}},
        )

        processor = AutoProcessor.from_pretrained(MODEL_ID)
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            MODEL_ID,
            dtype=dtype,
            low_cpu_mem_usage=True,
        )
        model.to(device)
        model.eval()

        asr = pipeline(
            task="automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            dtype=dtype,
            device=pipeline_device,
        )
        logger.info(
            "WHISPER_MODEL_READY",
            extra={"event_fields": {"model_id": MODEL_ID, "device": device}},
        )
        return asr

    async def transcribe(self, input_path: str | Path) -> str:
        source_path = Path(input_path)
        if not source_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {source_path}")
        if self._asr is None:
            raise WhisperUnavailableError("Whisper is not loaded")

        output_path = source_path.with_name(
            f"whisper_ready_{uuid4().hex[:8]}.wav"
        )
        try:
            await asyncio.to_thread(
                self._convert_to_whisper_wav,
                source_path,
                output_path,
            )
            async with self._inference_lock:
                text = await asyncio.to_thread(self._transcribe_sync, output_path)
            if not text:
                raise EmptyTranscriptionError("Whisper returned an empty transcription")
            return text
        finally:
            output_path.unlink(missing_ok=True)

    @staticmethod
    def _convert_to_whisper_wav(input_path: Path, output_path: Path) -> None:
        command = [
            "ffmpeg",
            "-y",
            "-i",
            os.fspath(input_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-acodec",
            "pcm_s16le",
            os.fspath(output_path),
        ]
        try:
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except FileNotFoundError as exc:
            raise WhisperUnavailableError("FFmpeg is not installed") from exc

        if process.returncode != 0:
            logger.error(
                "WHISPER_FFMPEG_FAILED",
                extra={
                    "event_fields": {
                        "return_code": process.returncode,
                        "stderr": process.stderr.decode("utf-8", errors="ignore")[-2000:],
                    }
                },
            )
            raise AudioConversionError("FFmpeg could not convert the uploaded audio")
        if not output_path.is_file():
            raise AudioConversionError("FFmpeg did not create the WAV output")

    def _transcribe_sync(self, whisper_audio: Path) -> str:
        import torch

        try:
            with torch.inference_mode():
                result = self._asr(
                    os.fspath(whisper_audio),
                    generate_kwargs={
                        "language": "ar",
                        "task": "transcribe",
                    },
                    return_timestamps=False,
                )
            return str(result["text"]).strip()
        except (EmptyTranscriptionError, WhisperUnavailableError):
            raise
        except Exception as exc:
            logger.exception("WHISPER_INFERENCE_FAILED")
            raise WhisperInferenceError("Whisper inference failed") from exc
