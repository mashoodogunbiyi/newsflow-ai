"""Opt-in PostgreSQL proof of the NFA-33 synchronisation workflow."""

import asyncio
from collections.abc import Iterator
from datetime import timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from pydantic import SecretStr

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.models.article_sync import SyncJobStatus, SyncTriggerType
from app.providers.fixture_provider import FixtureNewsProvider
from app.repositories.article_sync import (
    ActiveSyncJobError,
    SqlAlchemyArticleSyncRepository,
)
from app.repositories.articles import SqlAlchemyArticleRepository
from app.services.article_deduplication import ArticleDeduplicationService
from app.services.article_sync import ArticleSyncService
from tests.support.postgres import (
    DisposablePostgres,
    postgres_resources,
    require_disposable_database,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def article_sync_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[DisposablePostgres]:
    """Rebuild only the explicitly named disposable sync database."""

    database_url = require_disposable_database(
        required_name="newsflow_article_sync_test"
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


def test_postgresql_sync_tracks_jobs_checkpoints_and_article_evidence(
    article_sync_postgres: DisposablePostgres,
) -> None:
    resources = article_sync_postgres

    async def scenario() -> None:
        database = SqlAlchemyDatabase(SecretStr(resources.database_url))
        repository = SqlAlchemyArticleSyncRepository(database)
        service = ArticleSyncService(
            provider=FixtureNewsProvider(),
            source_profile_key="fixture-v1",
            ingestion=ArticleDeduplicationService(
                SqlAlchemyArticleRepository(database)
            ),
            repository=repository,
            page_size=2,
            retry_base_seconds=0,
            lease_duration=timedelta(minutes=5),
        )
        admin_id = uuid4()
        user_id = uuid4()
        try:
            async with database.session() as session:
                async with session.begin():
                    await session.execute(
                        sa.text(
                            """
                            INSERT INTO source_profiles (
                                profile_key,
                                source_name,
                                contract_version,
                                profile_type,
                                status,
                                authorisation_decision_ref,
                                access_method,
                                approved_at
                            )
                            VALUES (
                                'fixture-v1',
                                'NewsFlow AI synthetic fixture',
                                '1.0',
                                'fixture',
                                'enabled',
                                'NFA-SRC-AUTH-001',
                                'fixture',
                                '2026-10-01T00:00:00Z'
                            )
                            """
                        )
                    )
                    await session.execute(
                        sa.text(
                            """
                            INSERT INTO users (
                                id, email, password_hash, status, role
                            )
                            VALUES
                                (
                                    :admin_id,
                                    'sync.admin@example.invalid',
                                    :password_hash,
                                    'active',
                                    'admin'
                                ),
                                (
                                    :user_id,
                                    'sync.user@example.invalid',
                                    :password_hash,
                                    'active',
                                    'user'
                                )
                            """
                        ),
                        {
                            "admin_id": admin_id,
                            "user_id": user_id,
                            "password_hash": (
                                "!disabled-sync-test-password-"
                                "0000000000000000000000000000000000000000"
                            ),
                        },
                    )

            assert await repository.user_is_admin(admin_id) is True
            assert await repository.user_is_admin(user_id) is False

            first_job = await service.start_job(
                trigger_type=SyncTriggerType.MANUAL,
                requested_by_user_id=admin_id,
            )
            first = await service.run_job(first_job.id)

            assert first.status == SyncJobStatus.COMPLETED
            assert first.statistics.retrieved == 3
            assert first.statistics.created == 3
            assert first.statistics.provider_attempts == 2

            second_job = await service.start_job(
                trigger_type=SyncTriggerType.MANUAL,
                requested_by_user_id=admin_id,
            )
            second = await service.run_job(second_job.id)

            assert second.status == SyncJobStatus.COMPLETED
            assert second.statistics.retrieved == 0

            pending = await service.start_job(
                trigger_type=SyncTriggerType.MANUAL,
                requested_by_user_id=admin_id,
            )
            with pytest.raises(ActiveSyncJobError):
                await service.start_job(
                    trigger_type=SyncTriggerType.MANUAL,
                    requested_by_user_id=admin_id,
                )
            assert pending.status == SyncJobStatus.PENDING

            async with database.session() as session:
                counts = {
                    table: await session.scalar(
                        sa.text(f"SELECT count(*) FROM {table}")
                    )
                    for table in (
                        "articles",
                        "article_snapshots",
                        "article_provenance_events",
                        "article_rights_versions",
                        "article_sync_jobs",
                        "article_sync_checkpoints",
                    )
                }

            assert counts == {
                "articles": 3,
                "article_snapshots": 3,
                "article_provenance_events": 3,
                "article_rights_versions": 3,
                "article_sync_jobs": 3,
                "article_sync_checkpoints": 1,
            }
        finally:
            await database.close()

    asyncio.run(scenario())
