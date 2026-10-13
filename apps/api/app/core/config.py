"""Environment-based application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Validated settings loaded from environment variables or the root .env file."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: SecretStr | None = None
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)

    def require_database_url(self) -> SecretStr:
        """Return the configured database URL or fail with a safe message."""

        if self.database_url is None or not self.database_url.get_secret_value().strip():
            raise DatabaseConfigurationError(
                "DATABASE_URL must be set before the API can start."
            )
        return self.database_url


class DatabaseConfigurationError(RuntimeError):
    """Raised when required database configuration is missing or invalid."""


@lru_cache
def get_settings() -> Settings:
    """Load and cache application settings."""

    return Settings()
