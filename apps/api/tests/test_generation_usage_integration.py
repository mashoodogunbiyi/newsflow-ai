"""Opt-in PostgreSQL proof of shared NFA-43 generation controls."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from pydantic import SecretStr

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.models.generation_usage import GenerationErrorCategory
from app.repositories.generation_usage import SqlAlchemyGenerationUsageRepository
from app.services.generation_usage import (
    GenerationConcurrencyLimitExceeded,
    GenerationDuplicateInProgress,
    GenerationLimitExceeded,
    GenerationUsageService,
)
from tests.support.postgres import (
    DisposablePostgres,
    postgres_resources,
    require_disposable_database,
)

pytestmark = pytest.mark.integration
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


@pytest.fixture
def generation_usage_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[DisposablePostgres]:
    """Rebuild only an explicitly approved disposable usage database."""

    database_url = require_disposable_database(
        required_name="newsflow_generation_usage_test"
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


def test_postgresql_enforces_duplicate_concurrency_and_daily_limits(
    generation_usage_postgres: DisposablePostgres,
) -> None:
    resources = generation_usage_postgres

    async def scenario() -> None:
        database = SqlAlchemyDatabase(SecretStr(resources.database_url))
        owner_id = uuid4()
        service = GenerationUsageService(
            repository=SqlAlchemyGenerationUsageRepository(database),
            daily_limit=2,
            concurrent_limit=1,
            attempt_timeout=timedelta(minutes=3),
            retention=timedelta(days=90),
            clock=lambda: NOW,
        )
        try:
            async with database.session() as session:
                async with session.begin():
                    await session.execute(
                        sa.text(
                            "INSERT INTO users "
                            "(id, email, password_hash, status, role) "
                            "VALUES (:id, :email, :password_hash, 'active', 'user')"
                        ),
                        {
                            "id": owner_id,
                            "email": "nfa43@example.invalid",
                            "password_hash": (
                                "!disabled-nfa43-test-password-"
                                "0000000000000000000000000000000000000000"
                            ),
                        },
                    )

            first = await service.start_attempt(
                owner_id=owner_id,
                request_fingerprint="a" * 64,
            )
            with pytest.raises(GenerationDuplicateInProgress):
                await service.start_attempt(
                    owner_id=owner_id,
                    request_fingerprint="a" * 64,
                )
            with pytest.raises(GenerationConcurrencyLimitExceeded):
                await service.start_attempt(
                    owner_id=owner_id,
                    request_fingerprint="b" * 64,
                )

            await service.fail_attempt(
                attempt=first,
                category=GenerationErrorCategory.AI_TIMEOUT,
            )
            second = await service.start_attempt(
                owner_id=owner_id,
                request_fingerprint="b" * 64,
            )
            await service.fail_attempt(
                attempt=second,
                category=GenerationErrorCategory.AI_RATE_LIMIT_ERROR,
            )
            with pytest.raises(GenerationLimitExceeded):
                await service.start_attempt(
                    owner_id=owner_id,
                    request_fingerprint="c" * 64,
                )

            async with database.session() as session:
                rows = (
                    await session.execute(
                        sa.text(
                            "SELECT status, error_category "
                            "FROM generation_usage_events ORDER BY created_at, id"
                        )
                    )
                ).all()
            assert set(rows) == {
                ("failed", "ai_timeout"),
                ("failed", "ai_rate_limit_error"),
            }
        finally:
            await database.close()

    asyncio.run(scenario())
