from functools import lru_cache
from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EnterpriseMind"
    database_url: str = (
        "postgresql+asyncpg://" "enterprisemind:enterprisemind" "@127.0.0.1:5432/enterprisemind"
    )
    readonly_database_url: str = (
        "postgresql+asyncpg://"
        "enterprisemind_reader:reader-local-password"
        "@127.0.0.1:5432/enterprisemind"
    )

    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30

    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "enterprise_knowledge"
    embedding_dimensions: int = 384
    retrieval_minimum_score: float = 0.20

    redis_url: str = "redis://127.0.0.1:6379/0"
    upload_directory: Path = Path("uploads")
    maximum_upload_bytes: int = 10 * 1024 * 1024

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = 120.0

    external_model_base_url: str = "https://api.example.com/v1"
    external_model_api_key: str = ""
    external_model_name: str = "external-chat-model"
    external_model_timeout_seconds: float = 30.0

    allow_external_for_internal: bool = False
    sql_max_rows: int = 200
    sql_timeout_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
