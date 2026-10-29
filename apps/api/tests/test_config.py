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
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("OPENAI_API_KEY", openai_api_key)

    settings = Settings(_env_file=None)

    assert settings.require_database_url().get_secret_value() == database_url
    assert settings.require_openai_api_key().get_secret_value() == openai_api_key


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
