"""Development seed safety tests that do not require PostgreSQL."""

import pytest

from app.core.config import Settings
from app.database.seed import (
    SEED_ARTICLE_TEXT,
    SEED_ARTICLE_URL,
    SEED_PASSWORD_HASH,
    SEED_USER_EMAIL,
    SeedSafetyError,
    validate_seed_settings,
)


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_seed_rejects_non_development_environments(app_env: str) -> None:
    settings = Settings(
        _env_file=None,
        app_env=app_env,
        seed_data_enabled=True,
    )

    with pytest.raises(SeedSafetyError, match="development or test"):
        validate_seed_settings(settings)


def test_seed_requires_explicit_opt_in() -> None:
    settings = Settings(
        _env_file=None,
        app_env="development",
        seed_data_enabled=False,
    )

    with pytest.raises(SeedSafetyError, match="SEED_DATA_ENABLED"):
        validate_seed_settings(settings)


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_seed_allows_explicit_safe_environment(app_env: str) -> None:
    settings = Settings(
        _env_file=None,
        app_env=app_env,
        seed_data_enabled=True,
    )

    validate_seed_settings(settings)


def test_seed_fixture_is_synthetic_and_has_no_usable_account() -> None:
    combined_fixture = " ".join(
        [SEED_USER_EMAIL, SEED_ARTICLE_URL, SEED_ARTICLE_TEXT]
    ).lower()

    assert SEED_USER_EMAIL.endswith(".invalid")
    assert "example.invalid" in SEED_ARTICLE_URL
    assert "synthetic" in SEED_ARTICLE_TEXT.lower()
    assert "cnn.com" not in combined_fixture
    assert SEED_PASSWORD_HASH.startswith("!disabled-synthetic")
    assert len(SEED_PASSWORD_HASH) >= 60
