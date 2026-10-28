"""Safety-gated disposable PostgreSQL support for integration tests."""

import os
from dataclasses import dataclass
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config
from sqlalchemy import Engine

API_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DisposablePostgres:
    """Resources for one migrated PostgreSQL integration-test database."""

    database_url: str
    alembic_config: Config
    engine: Engine


def require_disposable_database(*, required_name: str) -> str:
    """Return a deliberately approved test URL or skip/fail safely."""

    database_url = os.getenv("TEST_DATABASE_URL")
    reset_allowed = os.getenv("ALLOW_DATABASE_RESET_FOR_TESTS", "").lower()
    if not database_url or reset_allowed != "true":
        pytest.skip(
            "Set TEST_DATABASE_URL and ALLOW_DATABASE_RESET_FOR_TESTS=true "
            "for a disposable PostgreSQL database."
        )
    if required_name not in database_url:
        pytest.fail(
            "TEST_DATABASE_URL must name a disposable database containing "
            f"'{required_name}'."
        )
    return database_url


def sqlalchemy_url(database_url: str) -> str:
    """Use the Psycopg SQLAlchemy dialect without changing credentials."""

    return database_url.replace("postgresql://", "postgresql+psycopg://", 1)


def postgres_resources(database_url: str) -> DisposablePostgres:
    """Create migration and synchronous inspection resources for a test URL."""

    return DisposablePostgres(
        database_url=database_url,
        alembic_config=Config(str(API_ROOT / "alembic.ini")),
        engine=sa.create_engine(sqlalchemy_url(database_url)),
    )
