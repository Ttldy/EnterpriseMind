from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EnterpriseMind"
    database_url: str = (
        "postgresql+asyncpg://enterprisemind:enterprisemind" "@127.0.0.1:5432/enterprisemind"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
