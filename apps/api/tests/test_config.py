"""Secure configuration tests."""

import pytest

from app.core.config import (
    DatabaseConfigurationError,
    ENVIRONMENT_FILE,
    OpenAIConfigurationError,
    Settings,
)


def test_environment_file_is_found_without_fixed_path_depth() -> None:
    assert ENVIRONMENT_FILE.name == ".env"
    assert ENVIRONMENT_FILE.parent.joinpath(".env.example").is_file()


def test_settings_load_secrets_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
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
