from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables (or a .env file)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="LEDGERLY_")

    database_url: str = "sqlite:///./ledgerly.db"
    secret_key: str = "dev-only-insecure-key-change-me-in-production"
    access_token_minutes: int = 60 * 24


@lru_cache
def get_settings() -> Settings:
    return Settings()
