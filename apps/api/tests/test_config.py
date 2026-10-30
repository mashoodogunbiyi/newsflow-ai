"""Secure configuration tests."""

import pytest

from app.core.config import (
    ENVIRONMENT_FILE,
    DatabaseConfigurationError,
    OpenAIConfigurationError,
    Settings,
)


def test_environment_file_is_found_without_fixed_path_depth() -> None:
    assert ENVIRONMENT_FILE.name == ".env"
    assert ENVIRONMENT_FILE.parent.joinpath(".env.example").is_file()


def test_settings_load_secrets_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = "postgresql://test-user:test-password@localhost:5432/newsflow"
    openai_api_key = "test-openai-key-loaded-from-environment"
    openai_model = "test-openai-model"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("OPENAI_API_KEY", openai_api_key)
    monkeypatch.setenv("OPENAI_MODEL", openai_model)
    monkeypatch.setenv("OPENAI_REQUEST_TIMEOUT", "45")
    monkeypatch.setenv("OPENAI_MAX_OUTPUT_TOKENS", "600")
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "1")

    settings = Settings(_env_file=None)

    assert settings.require_database_url().get_secret_value() == database_url
    assert settings.require_openai_api_key().get_secret_value() == openai_api_key
    openai_configuration = settings.require_openai_configuration()
    assert openai_configuration.model == openai_model
    assert openai_configuration.request_timeout == 45
    assert openai_configuration.max_output_tokens == 600
    assert openai_configuration.max_retries == 1


def test_secret_values_are_masked_in_settings_representation() -> None:
    database_url = "postgresql://test-user:private-password@localhost:5432/newsflow"
    openai_api_key = "private-test-openai-key"
    settings = Settings(
        _env_file=None,
        database_url=database_url,
        openai_api_key=openai_api_key,
    )

    settings_representation = repr(settings)

    assert database_url not in settings_representation
    assert openai_api_key not in settings_representation
    assert "**********" in settings_representation


def test_missing_openai_api_key_produces_clear_safe_error() -> None:
    settings = Settings(_env_file=None, openai_api_key=None)

    with pytest.raises(
        OpenAIConfigurationError,
        match="OPENAI_API_KEY must be set",
    ) as error:
        settings.require_openai_api_key()

    assert "key=" not in str(error.value).lower()


def test_openai_api_key_placeholder_is_rejected() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="your_openai_api_key_here",
    )

    with pytest.raises(
        OpenAIConfigurationError,
        match="example placeholder",
    ):
        settings.require_openai_api_key()


def test_missing_openai_model_produces_clear_safe_error() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="test-openai-key",
        openai_model=None,
    )

    with pytest.raises(
        OpenAIConfigurationError,
        match="OPENAI_MODEL must be set",
    ):
        settings.require_openai_configuration()


def test_openai_model_placeholder_is_rejected() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="test-openai-key",
        openai_model="your_approved_openai_model_here",
    )

    with pytest.raises(
        OpenAIConfigurationError,
        match="OPENAI_MODEL still contains the example placeholder",
    ):
        settings.require_openai_configuration()


def test_openai_settings_have_bounded_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.openai_request_timeout == 30
    assert settings.openai_max_output_tokens == 800
    assert settings.openai_max_retries == 2


def test_database_url_placeholder_is_rejected() -> None:
    settings = Settings(
        _env_file=None,
        database_url=(
            "postgresql://your_local_user:your_local_password@localhost:5432/newsflow"
        ),
    )

    with pytest.raises(
        DatabaseConfigurationError,
        match="example placeholders",
    ):
        settings.require_database_url()


def test_seed_data_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None)

    assert settings.seed_data_enabled is False


def test_news_source_is_disabled_unless_fixture_mode_is_explicit() -> None:
    assert Settings(_env_file=None).news_source_mode == "disabled"
    assert Settings(_env_file=None, news_source_mode="fixture").news_source_mode == (
        "fixture"
    )


def test_registration_rate_limit_has_safe_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.registration_rate_limit_attempts == 5
    assert settings.registration_rate_limit_window_seconds == 60


def test_authentication_settings_have_safe_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.login_rate_limit_attempts == 5
    assert settings.login_rate_limit_window_seconds == 60
    assert settings.session_lifetime_minutes == 60
    assert settings.frontend_origin == "http://localhost:3000"
    assert settings.session_cookie_secure is False
    assert Settings(_env_file=None, app_env="production").session_cookie_secure is True


def test_article_sync_settings_have_bounded_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.article_sync_interval_seconds == 14_400
    assert settings.article_sync_page_size == 50
    assert settings.article_sync_max_retries == 2
    assert settings.article_sync_retry_base_seconds == 1
    assert settings.article_sync_lease_seconds == 300
    assert settings.manual_sync_rate_limit_attempts == 2
    assert settings.manual_sync_rate_limit_window_seconds == 60
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"
    assert settings.ingestion_metrics_enabled is True
    assert settings.ingestion_metrics_window_hours == 24
    assert settings.ingestion_failure_threshold == 3
    assert settings.ingestion_success_stale_seconds == 21_600
    assert settings.ingestion_long_running_seconds == 600
    assert settings.ingestion_rejection_rate_percent == 25


def test_linkedin_generation_rate_limit_has_bounded_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.generation_rate_limit_attempts == 10
    assert settings.generation_rate_limit_window_seconds == 60
    assert settings.generation_daily_limit == 50
    assert settings.generation_concurrent_limit == 2
    assert settings.generation_attempt_timeout_seconds == 180
    assert settings.generation_usage_retention_days == 90
    assert settings.generation_audit_retention_days == 90
    assert settings.generation_monitoring_window_hours == 24


def test_empty_optional_openai_model_does_not_block_non_ai_startup() -> None:
    settings = Settings(_env_file=None, openai_model="")

    assert settings.openai_model is None
