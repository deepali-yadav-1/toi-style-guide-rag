from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TOI Style Guide RAG"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_base_url: str | None = None
    openai_timeout_seconds: float = 60.0
    openai_connect_timeout_seconds: float = 10.0
    openai_trust_env: bool = False
    openai_verify_ssl: bool = True
    openai_ca_bundle: str | None = None
    embedding_batch_size: int = 64
    openai_max_retries: int = 5

    database_url: str = Field(..., alias="DATABASE_URL")
    embedding_dimension: int = 1536
    retrieval_top_k: int = 6
    max_chat_history_messages: int = 8

    documents_dir: Path = Path("..")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return value
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
