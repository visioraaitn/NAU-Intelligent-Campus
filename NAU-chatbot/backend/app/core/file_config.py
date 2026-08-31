from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings


class StrictConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelRoleConfig(StrictConfig):
    provider: Literal["huggingface", "vllm"] = "huggingface"
    model_id: str
    local_path: str = ""
    revision: str | None = None
    quantization: Literal["4bit", "8bit", "none"] = "none"
    device: str = "auto"
    role: str
    max_concurrency: int = Field(default=1, ge=1, le=32)
    trust_remote_code: bool = False
    local_files_only: bool = True


class ModelsConfig(StrictConfig):
    esprit: ModelRoleConfig
    final: ModelRoleConfig
    embedding: ModelRoleConfig
    reranker: ModelRoleConfig


class RagFileConfig(StrictConfig):
    collection: str = "iit_academic_v1"
    candidate_count: int = Field(default=24, ge=1, le=100)
    result_count: int = Field(default=6, ge=1, le=20)
    minimum_rerank_score: float = -10.0
    chunk_max_chars: int = Field(default=1_500, ge=200, le=8_000)
    index_batch_size: int = Field(default=64, ge=1, le=128)


class SecurityFileConfig(StrictConfig):
    max_message_chars: int = Field(default=4_000, ge=128, le=20_000)
    max_history_messages: int = Field(default=24, ge=2, le=100)
    redact_log_fields: list[str]
    allowed_jwt_algorithms: list[str]


class DialogueFileConfig(StrictConfig):
    default_max_lines: int = Field(default=6, ge=1, le=12)
    detail_max_lines: int = Field(default=8, ge=2, le=16)
    cta_cooldown_turns: int = Field(default=3, ge=1, le=20)
    cta_max_count: int = Field(default=2, ge=0, le=10)
    qualification_attempts: int = Field(default=1, ge=1, le=3)
    interest_keywords: dict[str, list[str]]


class PatternFile(StrictConfig):
    patterns: dict[str, list[str]] = Field(default_factory=dict)
    terms: dict[str, list[str]] = Field(default_factory=dict)


def _yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


@lru_cache(maxsize=1)
def models_config() -> ModelsConfig:
    settings = get_settings()
    data = _yaml(settings.config_root / "config/models.yaml")
    overrides = {
        "esprit": (settings.esprit_model_id, settings.esprit_model_path),
        "final": (settings.qwen_model_id, settings.qwen_model_path),
        "embedding": (settings.embed_model_id, settings.embed_model_path),
        "reranker": (settings.rerank_model_id, settings.rerank_model_path),
    }
    for role, (model_id, local_path) in overrides.items():
        if model_id:
            data[role]["model_id"] = model_id
        if local_path:
            data[role]["local_path"] = local_path
        data[role]["local_files_only"] = settings.models_local_only
    return ModelsConfig.model_validate(data)


@lru_cache(maxsize=1)
def rag_config() -> RagFileConfig:
    return RagFileConfig.model_validate(_yaml(get_settings().config_root / "config/rag.yaml"))


@lru_cache(maxsize=1)
def security_file_config() -> SecurityFileConfig:
    return SecurityFileConfig.model_validate(_yaml(get_settings().config_root / "config/security.yaml"))


@lru_cache(maxsize=1)
def dialogue_config() -> DialogueFileConfig:
    return DialogueFileConfig.model_validate(_yaml(get_settings().config_root / "config/dialogue.yaml"))


@lru_cache(maxsize=16)
def pattern_file(name: str) -> PatternFile:
    if not name.replace("_", "").isalnum():
        raise ValueError("invalid pattern file name")
    return PatternFile.model_validate(
        _yaml(get_settings().config_root / "patterns" / f"{name}.yaml")
    )


@lru_cache(maxsize=16)
def prompt_text(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError("invalid prompt name")
    text = (get_settings().config_root / "prompts" / f"{name}.txt").read_text(
        encoding="utf-8"
    )
    if not text.strip():
        raise ValueError(f"empty prompt: {name}")
    return text.strip()
