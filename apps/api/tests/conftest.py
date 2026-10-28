"""Shared pytest fixtures for isolated NewsFlow AI backend tests."""

from collections.abc import Iterator

import pytest
from alembic import command
from fastapi.testclient import TestClient

from app.security import Argon2PasswordHasher
from tests.support.account_security import (
    AccountSecurityContext,
    AccountSecurityRepository,
    make_account_security_application,
)
from tests.support.postgres import (
    DisposablePostgres,
    postgres_resources,
    require_disposable_database,
)


@pytest.fixture
def account_security_context() -> Iterator[AccountSecurityContext]:
    """Provide fresh accounts, sessions, resources, and client cookies per test."""

    repository = AccountSecurityRepository()
    password_hasher = Argon2PasswordHasher()
    application = make_account_security_application(
        repository=repository,
        password_hasher=password_hasher,
    )
    with TestClient(application) as client:
        yield AccountSecurityContext(
            client=client,
            repository=repository,
            password_hasher=password_hasher,
        )


@pytest.fixture
def account_security_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[DisposablePostgres]:
    """Rebuild a specifically named disposable database around one integration test."""

    database_url = require_disposable_database(
        required_name="newsflow_account_security_test"
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "test")
    resources = postgres_resources(database_url)
    command.downgrade(resources.alembic_config, "base")
    command.upgrade(resources.alembic_config, "head")
    try:
        yield resources
    finally:
        command.downgrade(resources.alembic_config, "base")
        resources.engine.dispose()
