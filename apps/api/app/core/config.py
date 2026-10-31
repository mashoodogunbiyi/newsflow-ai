"""Environment-based application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.ai_config import OpenAIServiceConfiguration
from app.core.image_generation_config import OpenAIImageGenerationConfiguration


def find_environment_file() -> Path:
    """Locate the repository .env file without assuming a fixed directory depth."""

    for directory in Path(__file__).resolve().parents:
        if (directory / ".env.example").is_file():
            return directory / ".env"
    return Path.cwd() / ".env"


ENVIRONMENT_FILE = find_environment_file()


class ConfigurationError(RuntimeError):
    """Base error for missing or unsafe application configuration."""


class DatabaseConfigurationError(ConfigurationError):
    """Raised when required database configuration is missing or invalid."""


class OpenAIConfigurationError(ConfigurationError):
    """Raised when required OpenAI configuration is missing or invalid."""


class Settings(BaseSettings):
    """Validated settings loaded from environment variables or the root .env file."""

    model_config = SettingsConfigDict(
        env_file=ENVIRONMENT_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    news_source_mode: Literal["disabled", "fixture"] = "disabled"
    frontend_origin: str = Field(
        default="http://localhost:3000",
        pattern=r"^https?://[^/]+$",
    )
    database_url: SecretStr | None = None
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)
    registration_rate_limit_attempts: int = Field(default=5, ge=1, le=100)
    registration_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    login_rate_limit_attempts: int = Field(default=5, ge=1, le=100)
    login_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    session_lifetime_minutes: int = Field(default=60, ge=5, le=10_080)
    article_sync_interval_seconds: int = Field(default=14_400, ge=60, le=86_400)
    article_sync_page_size: int = Field(default=50, ge=1, le=100)
    article_sync_max_retries: int = Field(default=2, ge=0, le=5)
    article_sync_retry_base_seconds: float = Field(default=1.0, ge=0, le=60)
    article_sync_lease_seconds: int = Field(default=300, ge=30, le=3600)
    manual_sync_rate_limit_attempts: int = Field(default=2, ge=1, le=20)
    manual_sync_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    generation_rate_limit_attempts: int = Field(default=10, ge=1, le=100)
    generation_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    generation_daily_limit: int = Field(default=50, ge=1, le=10_000)
    generation_concurrent_limit: int = Field(default=2, ge=1, le=20)
    generation_attempt_timeout_seconds: int = Field(default=180, ge=10, le=1800)
    generation_usage_retention_days: int = Field(default=90, ge=1, le=730)
    generation_audit_retention_days: int = Field(default=90, ge=1, le=730)
    generation_monitoring_window_hours: int = Field(default=24, ge=1, le=168)
    ingestion_metrics_enabled: bool = True
    ingestion_metrics_window_hours: int = Field(default=24, ge=1, le=168)
    ingestion_failure_threshold: int = Field(default=3, ge=1, le=20)
    ingestion_success_stale_seconds: int = Field(
        default=21_600,
        ge=60,
        le=604_800,
    )
    ingestion_long_running_seconds: int = Field(default=600, ge=30, le=86_400)
    ingestion_rejection_rate_percent: int = Field(default=25, ge=1, le=100)
    openai_api_key: SecretStr | None = None
    openai_model: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    openai_request_timeout: float = Field(default=30.0, ge=1.0, le=300.0)
    openai_max_output_tokens: int = Field(default=800, ge=1, le=100_000)
    openai_max_retries: int = Field(default=2, ge=0, le=5)
    openai_image_model: str | None = Field(
        default="gpt-image-2.5-flare",
        min_length=1,
        max_length=200,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    image_generation_timeout: float = Field(default=120, ge=1, le=300)
    image_generation_max_concurrent_requests: int = Field(default=2, ge=1, le=10)
    image_generation_max_retries: int = Field(default=1, ge=0, le=2)
    image_generation_retry_base_seconds: float = Field(default=1, ge=0, le=10)
    image_generation_max_response_bytes: int = Field(
        default=26_214_400,
        ge=1_048_576,
        le=52_428_800,
    )
    image_generation_duplicate_cache_size: int = Field(default=100, ge=1, le=1_000)
    seed_data_enabled: bool = False

    @field_validator("openai_model", "openai_image_model", mode="before")
    @classmethod
    def empty_optional_model_is_unconfigured(cls, value: object) -> object:
        """Let non-AI API features start when Compose supplies an empty value."""

        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def session_cookie_secure(self) -> bool:
        """Require HTTPS-only session cookies outside local and test environments."""

        return self.app_env in {"staging", "production"}

    def require_database_url(self) -> SecretStr:
        """Return the configured database URL or fail with a safe message."""

        if self.database_url is None:
            raise DatabaseConfigurationError(
                "DATABASE_URL must be set before the API can start."
            )

        database_url = self.database_url.get_secret_value().strip()
        if not database_url:
            raise DatabaseConfigurationError(
                "DATABASE_URL must be set before the API can start."
            )
        if any(
            marker in database_url.lower()
            for marker in (
                "<database-",
                "your_local_",
                "your-local-",
                "your_database_",
                "your-database-",
            )
        ):
            raise DatabaseConfigurationError(
                "DATABASE_URL still contains example placeholders. "
                "Replace them in the ignored .env file before the API starts."
            )
        return self.database_url

    def require_openai_api_key(self) -> SecretStr:
        """Return the configured OpenAI key or fail without exposing its value."""

        if self.openai_api_key is None:
            raise OpenAIConfigurationError(
                "OPENAI_API_KEY must be set before an OpenAI feature can run."
            )

        api_key = self.openai_api_key.get_secret_value().strip()
        if not api_key:
            raise OpenAIConfigurationError(
                "OPENAI_API_KEY must be set before an OpenAI feature can run."
            )
        if api_key.lower() in {
            "your_api_key_here",
            "your_openai_api_key_here",
            "replace_with_your_openai_api_key",
        }:
            raise OpenAIConfigurationError(
                "OPENAI_API_KEY still contains the example placeholder. "
                "Replace it in the ignored .env file before using OpenAI features."
            )
        return self.openai_api_key

    def require_openai_configuration(self) -> OpenAIServiceConfiguration:
        """Return a complete bounded OpenAI configuration for one service."""

        api_key = self.require_openai_api_key()
        model = (self.openai_model or "").strip()
        if not model:
            raise OpenAIConfigurationError(
                "OPENAI_MODEL must be set before an OpenAI feature can run."
            )
        if model.lower() in {
            "your_openai_model_here",
            "your_approved_openai_model_here",
            "replace_with_your_openai_model",
        }:
            raise OpenAIConfigurationError(
                "OPENAI_MODEL still contains the example placeholder. "
                "Replace it in the ignored .env file before using OpenAI features."
            )
        return OpenAIServiceConfiguration(
            api_key=api_key,
            model=model,
            request_timeout=self.openai_request_timeout,
            max_output_tokens=self.openai_max_output_tokens,
            max_retries=self.openai_max_retries,
        )

    def require_openai_image_configuration(
        self,
    ) -> OpenAIImageGenerationConfiguration:
        """Return the reviewed and bounded OpenAI image configuration."""

        api_key = self.require_openai_api_key()
        model = (self.openai_image_model or "").strip()
        if not model:
            raise OpenAIConfigurationError(
                "OPENAI_IMAGE_MODEL must be set before image generation can run."
            )
        if model.lower() in {
            "your_openai_image_model_here",
            "your_approved_openai_image_model_here",
            "replace_with_your_openai_image_model",
        }:
            raise OpenAIConfigurationError(
                "OPENAI_IMAGE_MODEL still contains the example placeholder. "
                "Replace it in the ignored .env file before generating images."
            )
        try:
            return OpenAIImageGenerationConfiguration(
                api_key=api_key,
                model=model,
                request_timeout_seconds=self.image_generation_timeout,
                max_concurrent_requests=(self.image_generation_max_concurrent_requests),
                max_retries=self.image_generation_max_retries,
                retry_base_seconds=self.image_generation_retry_base_seconds,
                max_response_bytes=self.image_generation_max_response_bytes,
                duplicate_cache_size=self.image_generation_duplicate_cache_size,
            )
        except ValueError as exc:
            raise OpenAIConfigurationError(
                "OPENAI_IMAGE_MODEL is not an approved image model."
            ) from exc


@lru_cache
def get_settings() -> Settings:
    """Load and cache application settings."""

    return Settings()
