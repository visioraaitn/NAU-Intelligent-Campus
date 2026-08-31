from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _csv(value: object) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


CsvList = Annotated[list[str], NoDecode, BeforeValidator(_csv)]


class Settings(BaseSettings):
    """Environment-only operational settings.

    Prompts, patterns, and model policies are loaded from version-controlled files;
    secrets and deployment addresses remain environment values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "IIT Academic Assistant"
    app_secret_key: SecretStr = Field(default=SecretStr("change-me"), min_length=8)
    api_v1_prefix: str = "/api/v1"
    public_base_url: str = "http://localhost:8000"

    postgres_host: str = "postgres"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "iit_academic"
    postgres_user: str = "iit"
    postgres_password: SecretStr = SecretStr("change-me")
    postgres_pool_size: int = Field(default=10, ge=1, le=100)
    postgres_max_overflow: int = Field(default=20, ge=0, le=200)

    redis_url: SecretStr = SecretStr("redis://redis:6379/0")
    session_ttl_seconds: int = Field(default=86_400, ge=300, le=2_592_000)
    session_lock_ttl_seconds: int = Field(default=120, ge=15, le=900)
    recent_history_limit: int = Field(default=24, ge=2, le=100)

    chroma_host: str = "chroma"
    chroma_port: int = Field(default=8000, ge=1, le=65535)
    chroma_collection: str = "iit_academic_v1"

    inference_base_url: str = "http://inference:8010"
    inference_service_token: SecretStr = SecretStr("change-me")
    inference_timeout_seconds: float = Field(default=90.0, ge=1.0, le=600.0)

    admin_username: str = "admin"
    admin_password_hash: SecretStr = SecretStr("")
    jwt_secret: SecretStr = SecretStr("change-me")
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_access_ttl: int = Field(default=900, ge=60, le=86_400)
    jwt_refresh_ttl: int = Field(default=604_800, ge=900, le=2_592_000)
    secure_cookies: bool = False

    cors_origins: CsvList = ["http://localhost:5173", "http://localhost:8080"]
    trusted_hosts: CsvList = ["localhost", "127.0.0.1", "backend"]
    max_request_bytes: int = Field(default=32_768, ge=1_024, le=1_048_576)
    chat_rate_limit_per_minute: int = Field(default=20, ge=1, le=1_000)
    admin_rate_limit_per_minute: int = Field(default=60, ge=1, le=1_000)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_raw_messages: bool = False

    rag_queue_key: str = "iit:rag:jobs"
    rag_processing_key: str = "iit:rag:processing"
    rag_dead_letter_key: str = "iit:rag:dead"
    rag_max_attempts: int = Field(default=5, ge=1, le=20)
    rag_retry_base_seconds: float = Field(default=2.0, ge=0.1, le=60.0)
    rag_status_ttl_seconds: int = Field(default=604_800, ge=3_600, le=2_592_000)

    esprit_model_id: str = ""
    esprit_model_path: str = ""
    qwen_model_id: str = ""
    qwen_model_path: str = ""
    embed_model_id: str = ""
    embed_model_path: str = ""
    rerank_model_id: str = ""
    rerank_model_path: str = ""
    hf_home: str = "/models/huggingface"
    models_local_only: bool = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        password = self.postgres_password.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def config_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def validate_runtime_settings(settings: Settings) -> None:
    """Refuse placeholder credentials and unsafe cookie policy in production."""

    if not settings.is_production:
        return

    strong_secret_fields = {
        "APP_SECRET_KEY": settings.app_secret_key.get_secret_value(),
        "JWT_SECRET": settings.jwt_secret.get_secret_value(),
        "INFERENCE_SERVICE_TOKEN": settings.inference_service_token.get_secret_value(),
    }
    weak = [
        name
        for name, value in strong_secret_fields.items()
        if len(value) < 32 or _is_placeholder(value)
    ]
    if _is_placeholder(settings.postgres_password.get_secret_value()):
        weak.append("POSTGRES_PASSWORD")
    if _is_placeholder(settings.redis_url.get_secret_value()):
        weak.append("REDIS_URL")
    password_hash = settings.admin_password_hash.get_secret_value()
    if not password_hash.startswith("$argon2id$") or _is_placeholder(password_hash):
        weak.append("ADMIN_PASSWORD_HASH")
    if weak:
        raise RuntimeError(
            "Production security configuration is incomplete: "
            + ", ".join(sorted(set(weak)))
        )
    if not settings.secure_cookies:
        raise RuntimeError("SECURE_COOKIES must be enabled in production")
    if "*" in settings.cors_origins or "*" in settings.trusted_hosts:
        raise RuntimeError("Wildcard CORS origins and trusted hosts are forbidden")
    if not settings.models_local_only:
        raise RuntimeError("MODELS_LOCAL_ONLY must be enabled in production")
    if hmac_compare(
        settings.app_secret_key.get_secret_value(),
        settings.jwt_secret.get_secret_value(),
    ):
        raise RuntimeError("APP_SECRET_KEY and JWT_SECRET must be independent")


def validate_inference_settings(settings: Settings) -> None:
    """Validate only secrets and offline policy owned by the inference process."""

    if not settings.is_production:
        return
    token = settings.inference_service_token.get_secret_value()
    if len(token) < 32 or _is_placeholder(token):
        raise RuntimeError("Production INFERENCE_SERVICE_TOKEN is incomplete")
    if not settings.models_local_only:
        raise RuntimeError("MODELS_LOCAL_ONLY must be enabled in production")


def hmac_compare(first: str, second: str) -> bool:
    """Small local helper avoids leaking secret values through validation errors."""

    import hmac

    return hmac.compare_digest(first, second)


def _is_placeholder(value: str) -> bool:
    folded = value.strip().lower()
    return (
        not folded
        or folded in {"change-me", "changeme"}
        or "replace_" in folded
        or "replace-" in folded
    )
