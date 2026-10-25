"""Opt-in PostgreSQL integration test for secure user registration."""

import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.integration

API_ROOT = Path(__file__).resolve().parents[1]
VALID_PASSWORD = "Integration-Password-42!"


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    reset_allowed = os.getenv("ALLOW_DATABASE_RESET_FOR_TESTS", "").lower()
    if not database_url or reset_allowed != "true":
        pytest.skip(
            "Set TEST_DATABASE_URL and ALLOW_DATABASE_RESET_FOR_TESTS=true "
            "for a disposable PostgreSQL database."
        )
    if "newsflow_registration_test" not in database_url:
        pytest.fail(
            "TEST_DATABASE_URL must name a disposable database containing "
            "'newsflow_registration_test'."
        )
    return database_url


def _sqlalchemy_url(database_url: str) -> str:
    return database_url.replace("postgresql://", "postgresql+psycopg://", 1)


def test_registration_persists_argon2id_hash_and_enforces_unique_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _test_database_url()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "test")

    alembic_config = Config(str(API_ROOT / "alembic.ini"))
    engine = sa.create_engine(_sqlalchemy_url(database_url))
    settings = Settings(
        _env_file=None,
        database_url=SecretStr(database_url),
        registration_rate_limit_attempts=10,
    )

    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    try:
        with TestClient(create_app(settings=settings)) as client:
            successful_response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "Integration.User@Example.com",
                    "password": VALID_PASSWORD,
                },
            )
            duplicate_response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "integration.user@example.com",
                    "password": VALID_PASSWORD,
                },
            )

        assert successful_response.status_code == 201
        assert successful_response.json()["email"] == "integration.user@example.com"
        assert duplicate_response.status_code == 409

        with engine.connect() as connection:
            row = connection.execute(
                sa.text("SELECT email, password_hash FROM users WHERE email = :email"),
                {"email": "integration.user@example.com"},
            ).one()

        assert row.email == "integration.user@example.com"
        assert row.password_hash != VALID_PASSWORD
        assert row.password_hash.startswith("$argon2id$")
        assert VALID_PASSWORD not in successful_response.text
        assert "password_hash" not in successful_response.text
        assert VALID_PASSWORD not in duplicate_response.text
        assert "password_hash" not in duplicate_response.text
    finally:
        engine.dispose()
        command.downgrade(alembic_config, "base")
