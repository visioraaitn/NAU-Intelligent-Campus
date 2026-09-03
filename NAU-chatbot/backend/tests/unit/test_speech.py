from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, UploadFile

from app.api.routers import speech
from app.core.dependencies import rate_limiter, settings_dependency, speech_inference_dependency
from app.core.exceptions import AppError
from app.services.speech import AudioConversionError, WhisperService


class FakeLimiter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    async def enforce(self, bucket: str, limit: int) -> None:
        self.calls.append((bucket, limit))


class FakeInference:
    def __init__(self, text: str = "ena nheb na3ref les formations") -> None:
        self.text = text
        self.calls: list[tuple[bytes, str, str]] = []

    async def transcribe_audio(
        self,
        audio: bytes,
        *,
        content_type: str,
        filename: str,
    ) -> str:
        self.calls.append((audio, content_type, filename))
        return self.text


def upload(content: bytes, content_type: str, filename: str = "recording.webm") -> UploadFile:
    return UploadFile(
        BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.unit
async def test_reads_valid_browser_audio() -> None:
    assert await speech._read_audio(upload(b"webm-data", "audio/webm;codecs=opus"), 100) == b"webm-data"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("content", "content_type", "max_bytes", "code"),
    [
        (b"", "audio/webm", 100, "EMPTY_AUDIO"),
        (b"data", "text/plain", 100, "UNSUPPORTED_AUDIO_TYPE"),
        (b"too-large", "audio/webm", 4, "AUDIO_TOO_LARGE"),
    ],
)
async def test_rejects_invalid_audio(
    content: bytes,
    content_type: str,
    max_bytes: int,
    code: str,
) -> None:
    with pytest.raises(AppError) as error:
        await speech._read_audio(upload(content, content_type), max_bytes)
    assert error.value.code == code


@pytest.mark.unit
def test_public_endpoint_requires_audio_file(test_settings) -> None:
    app = FastAPI()
    app.include_router(speech.router, prefix="/api/v1")
    app.dependency_overrides[speech_inference_dependency] = lambda: FakeInference()
    app.dependency_overrides[rate_limiter] = lambda: FakeLimiter()
    app.dependency_overrides[settings_dependency] = lambda: test_settings

    response = TestClient(app).post("/api/v1/speech/transcribe")

    assert response.status_code == 422


@pytest.mark.unit
async def test_endpoint_returns_only_transcribed_text(test_settings) -> None:
    inference = FakeInference("  transcription correcte  ")
    limiter = FakeLimiter()
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={})
    audio = upload(b"browser-audio", "audio/webm;codecs=opus")

    response = await speech.transcribe_audio(
        request,
        audio,
        inference,
        limiter,
        test_settings,
    )

    assert response.text == "  transcription correcte  "
    assert inference.calls == [
        (b"browser-audio", "audio/webm;codecs=opus", "recording.webm")
    ]
    assert limiter.calls
    assert audio.file.closed


@pytest.mark.unit
def test_load_pipeline_keeps_validated_whisper_parameters(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeTorch:
        float16 = "float16"
        float32 = "float32"
        cuda = SimpleNamespace(is_available=lambda: True)

    class FakeModel:
        def to(self, device: str) -> None:
            calls["model_device"] = device

        def eval(self) -> None:
            calls["model_eval"] = True

    processor = SimpleNamespace(tokenizer="tokenizer", feature_extractor="feature_extractor")

    class FakeProcessorClass:
        @staticmethod
        def from_pretrained(model_id: str):
            calls["processor"] = model_id
            return processor

    class FakeModelClass:
        @staticmethod
        def from_pretrained(model_id: str, **kwargs):
            calls["model"] = (model_id, kwargs)
            return FakeModel()

    def fake_pipeline(**kwargs):
        calls["pipeline"] = kwargs
        return "asr"

    monkeypatch.setitem(sys.modules, "torch", FakeTorch())
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoModelForSpeechSeq2Seq=FakeModelClass,
            AutoProcessor=FakeProcessorClass,
            pipeline=fake_pipeline,
        ),
    )

    assert WhisperService._load_pipeline() == "asr"
    assert calls["processor"] == "oddadmix/Whisperv3-tunisian-codeswitch"
    assert calls["model"] == (
        "oddadmix/Whisperv3-tunisian-codeswitch",
        {"dtype": "float16", "low_cpu_mem_usage": True},
    )
    assert calls["model_device"] == "cuda:0"
    assert calls["model_eval"] is True
    assert calls["pipeline"] == {
        "task": "automatic-speech-recognition",
        "model": ANY,
        "tokenizer": "tokenizer",
        "feature_extractor": "feature_extractor",
        "dtype": "float16",
        "device": 0,
    }


@pytest.mark.unit
def test_transcription_keeps_validated_generation_parameters(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    class InferenceMode:
        def __enter__(self):
            return None

        def __exit__(self, *args):
            return False

    class FakeAsr:
        def __call__(self, audio_path: str, **kwargs):
            calls["audio_path"] = audio_path
            calls["kwargs"] = kwargs
            return {"text": "  transcription  "}

    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(inference_mode=lambda: InferenceMode()),
    )
    service = WhisperService()
    service._asr = FakeAsr()
    audio_path = tmp_path / "audio.wav"

    assert service._transcribe_sync(audio_path) == "transcription"
    assert calls == {
        "audio_path": str(audio_path),
        "kwargs": {
            "generate_kwargs": {"language": "ar", "task": "transcribe"},
            "return_timestamps": False,
        },
    }


@pytest.mark.unit
def test_ffmpeg_conversion_uses_exact_validated_command(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source.webm"
    output = tmp_path / "output.wav"
    source.write_bytes(b"audio")
    captured: list[str] = []

    def fake_run(command, **kwargs):
        del kwargs
        captured.extend(command)
        output.write_bytes(b"wav")
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr("app.services.speech.whisper_service.subprocess.run", fake_run)

    WhisperService._convert_to_whisper_wav(source, output)

    assert captured == [
        "ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
        "-acodec", "pcm_s16le", str(output),
    ]


@pytest.mark.unit
async def test_transcribe_cleans_converted_file_on_failure(monkeypatch, tmp_path: Path) -> None:
    service = WhisperService()
    service._asr = object()
    source = tmp_path / "source.webm"
    source.write_bytes(b"audio")
    outputs: list[Path] = []

    def fake_convert(input_path: Path, output_path: Path) -> None:
        assert input_path == source
        outputs.append(output_path)
        output_path.write_bytes(b"wav")

    def fail_transcription(output_path: Path) -> str:
        assert output_path.is_file()
        raise RuntimeError("inference failure")

    monkeypatch.setattr(service, "_convert_to_whisper_wav", fake_convert)
    monkeypatch.setattr(service, "_transcribe_sync", fail_transcription)

    with pytest.raises(RuntimeError, match="inference failure"):
        await service.transcribe(source)

    assert len(outputs) == 1
    assert not outputs[0].exists()
    assert source.exists()


@pytest.mark.unit
def test_ffmpeg_failure_is_safe(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source.webm"
    output = tmp_path / "output.wav"
    source.write_bytes(b"audio")
    monkeypatch.setattr(
        "app.services.speech.whisper_service.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stderr=b"decoder error"),
    )

    with pytest.raises(AudioConversionError):
        WhisperService._convert_to_whisper_wav(source, output)
    assert not output.exists()


@pytest.mark.unit
async def test_internal_endpoint_removes_original_temporary_audio() -> None:
    from app.infrastructure.inference.speech_server import transcribe_speech

    captured_paths: list[Path] = []

    class FakeSpeechService:
        async def transcribe(self, source_path: Path) -> str:
            captured_paths.append(source_path)
            assert source_path.read_bytes() == b"browser-audio"
            return "texte"

    async def body() -> bytes:
        return b"browser-audio"

    request = SimpleNamespace(
        body=body,
        app=SimpleNamespace(state=SimpleNamespace(speech=FakeSpeechService())),
    )

    assert await transcribe_speech(request, "recording.webm") == {"text": "texte"}
    assert len(captured_paths) == 1
    assert not captured_paths[0].exists()
