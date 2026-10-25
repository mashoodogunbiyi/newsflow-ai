"""Opt-in PostgreSQL integration test for NFA-23 authentication sessions."""

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
    if "newsflow_authentication_test" not in database_url:
        pytest.fail(
            "TEST_DATABASE_URL must name a disposable database containing "
            "'newsflow_authentication_test'."
        )
    return database_url


def _sqlalchemy_url(database_url: str) -> str:
    return database_url.replace("postgresql://", "postgresql+psycopg://", 1)


def test_login_current_user_logout_and_expiry_with_postgresql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _test_database_url()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "test")

    alembic_config = Config(str(API_ROOT / "alembic.ini"))
    engine = sa.create_engine(_sqlalchemy_url(database_url))
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=SecretStr(database_url),
        registration_rate_limit_attempts=10,
        login_rate_limit_attempts=10,
    )

    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    try:
        with TestClient(create_app(settings=settings)) as client:
            registration = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "Authentication.User@Example.com",
                    "password": VALID_PASSWORD,
                },
            )
            login = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "authentication.user@example.com",
                    "password": VALID_PASSWORD,
                },
            )
            current_user = client.get("/api/v1/auth/me")
            csrf_token = client.cookies.get("newsflow_csrf")
            logout = client.post(
                "/api/v1/auth/logout",
                headers={"X-CSRF-Token": csrf_token or ""},
            )
            after_logout = client.get("/api/v1/auth/me")

        assert registration.status_code == 201
        assert login.status_code == 200
        assert current_user.status_code == 200
        assert current_user.json()["email"] == "authentication.user@example.com"
        assert logout.status_code == 204
        assert after_logout.status_code == 401

        with engine.begin() as connection:
            session = connection.execute(
                sa.text(
                    "SELECT token_hash, csrf_token_hash, expires_at, revoked_at "
                    "FROM sessions"
                )
            ).one()
            assert len(session.token_hash) == 32
            assert len(session.csrf_token_hash) == 32
            assert session.revoked_at is not None
            assert session.expires_at > session.revoked_at

            connection.execute(
                sa.text(
                    "UPDATE sessions SET revoked_at = NULL, "
                    "created_at = now() - interval '2 minutes', "
                    "expires_at = now() - interval '1 minute'"
                )
            )

        expired_cookie = login.cookies.get("newsflow_session")
        with TestClient(create_app(settings=settings)) as client:
            client.cookies.set("newsflow_session", expired_cookie or "")
            expired = client.get("/api/v1/auth/me")
        assert expired.status_code == 401
    finally:
        engine.dispose()
        command.downgrade(alembic_config, "base")
