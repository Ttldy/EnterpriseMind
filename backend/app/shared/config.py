from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model_provider: str = "demo"
    external_model_base_url: str = ""
    external_model_api_key: str = ""
    external_model_name: str = ""


settings = Settings()