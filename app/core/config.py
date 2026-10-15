"""
Centralized application configuration.

All settings are loaded from environment variables (or a local .env file) via
pydantic-settings, which provides validated, typed access to configuration
throughout the application.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5432/iot_telemetry"
    )

    # ── API ───────────────────────────────────────────────────────────────
    APP_NAME: str = "IoT Telemetry Processing Engine"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["*"]

    # ── Pagination defaults ───────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 1000


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
