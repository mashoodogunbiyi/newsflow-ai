"""Opt-in PostgreSQL proof of atomic article deduplication."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from pydantic import SecretStr

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.models.article_rights import ArticleUseOperation, RightsDecisionReason
from app.providers.normalisation import ArticleNormalisationService
from app.repositories.article_rights import SqlAlchemyArticleRightsRepository
from app.repositories.articles import (
    ArticleIngestionAction,
    SqlAlchemyArticleRepository,
)
from app.services.article_deduplication import ArticleDeduplicationService
from app.services.article_rights import ArticleRightsService
from tests.support.postgres import (
    DisposablePostgres,
    postgres_resources,
    require_disposable_database,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def article_deduplication_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[DisposablePostgres]:
    """Rebuild only a deliberately named disposable deduplication database."""

    database_url = require_disposable_database(
        required_name="newsflow_article_deduplication_test"
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


def normalised_article(**changes: object):
    """Return a synthetic NFA-6 article without using a live provider."""

    record: dict[str, object] = {
        "record_key": "fixture-postgres-deduplication-001",
        "headline": "Synthetic PostgreSQL deduplication example",
        "link": "https://example.invalid/newsflow-ai/postgres-deduplication-001",
        "published_at": "2026-10-20T09:00:00Z",
        "topic": "technology",
        "summary": "Fictional metadata for a disposable database test.",
        "body": "Original synthetic content used only for NFA-31 testing.",
        "collected_at": "2026-10-20T09:05:00Z",
        "changed_at": None,
    }
    record.update(changes)
    return ArticleNormalisationService().normalise(record)


def test_postgresql_deduplicates_updates_and_preserves_snapshots(
    article_deduplication_postgres: DisposablePostgres,
) -> None:
    resources = article_deduplication_postgres
    constraints = {
        constraint["name"]
        for constraint in sa.inspect(resources.engine).get_unique_constraints(
            "articles"
        )
    }
    assert {
        "uq_articles_source_identity",
        "uq_articles_canonical_url",
    } <= constraints

    async def scenario() -> None:
        database = SqlAlchemyDatabase(SecretStr(resources.database_url))
        service = ArticleDeduplicationService(SqlAlchemyArticleRepository(database))
        profile_id = uuid4()
        user_id = uuid4()
        generated_post_id = uuid4()
        try:
            async with database.session() as session:
                async with session.begin():
                    await session.execute(
                        sa.text(
                            """
                            INSERT INTO source_profiles (
                                id,
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
                                :id,
                                'fixture-v1',
                                'NewsFlow AI synthetic fixture',
                                '1.0',
                                'fixture',
                                'enabled',
                                'NFA-SRC-AUTH-001',
                                'fixture',
                                now()
                            )
                            """
                        ),
                        {"id": profile_id},
                    )

            article = normalised_article()
            created = await service.ingest(article)
            repeated = await service.ingest(article)
            assert created.action == ArticleIngestionAction.CREATED
            assert repeated.action == ArticleIngestionAction.SKIPPED
            assert repeated.article_id == created.article_id
            assert repeated.snapshot_id == created.snapshot_id

            rights_service = ArticleRightsService(
                SqlAlchemyArticleRightsRepository(database)
            )
            display_decision = await rights_service.can_use_article(
                article_id=created.article_id,
                operation=ArticleUseOperation.DISPLAY_METADATA,
            )
            export_decision = await rights_service.can_use_article(
                article_id=created.article_id,
                operation=ArticleUseOperation.EXPORT_SOURCE_INFORMATION,
            )
            provenance = await rights_service.provenance_for_article(created.article_id)

            assert display_decision.allowed is True
            assert display_decision.attribution_text
            assert export_decision.allowed is False
            assert export_decision.reason == RightsDecisionReason.OPERATION_RESTRICTED
            assert [event.ingestion_action for event in provenance] == [
                "created",
                "skipped",
            ]

            async with database.session() as session:
                async with session.begin():
                    await session.execute(
                        sa.text(
                            """
                            INSERT INTO users (
                                id,
                                email,
                                password_hash,
                                status
                            )
                            VALUES (
                                :user_id,
                                'nfa31.owner@example.invalid',
                                :password_hash,
                                'active'
                            )
                            """
                        ),
                        {
                            "user_id": user_id,
                            "password_hash": (
                                "!disabled-nfa31-test-password-"
                                "0000000000000000000000000000000000000000"
                            ),
                        },
                    )
                    await session.execute(
                        sa.text(
                            """
                            INSERT INTO generated_posts (
                                id,
                                user_id,
                                article_snapshot_id,
                                status
                            )
                            VALUES (
                                :post_id,
                                :user_id,
                                :snapshot_id,
                                'draft'
                            )
                            """
                        ),
                        {
                            "post_id": generated_post_id,
                            "user_id": user_id,
                            "snapshot_id": created.snapshot_id,
                        },
                    )

            updated_article = article.model_copy(
                update={
                    "title": "Synthetic PostgreSQL deduplication example - updated",
                    "modified_at": datetime(2026, 10, 20, 10, 0, tzinfo=UTC),
                }
            )
            updated = await service.ingest(updated_article)
            assert updated.action == ArticleIngestionAction.UPDATED
            assert updated.article_id == created.article_id
            assert updated.snapshot_id != created.snapshot_id

            similar_title = normalised_article(
                record_key="fixture-postgres-deduplication-002",
                headline=updated_article.title,
                link=("https://example.invalid/newsflow-ai/postgres-deduplication-002"),
            )
            distinct = await service.ingest(similar_title)
            assert distinct.action == ArticleIngestionAction.CREATED
            assert distinct.article_id != created.article_id

            concurrent_article = normalised_article(
                record_key="fixture-postgres-deduplication-concurrent",
                link=(
                    "https://example.invalid/newsflow-ai/"
                    "postgres-deduplication-concurrent"
                ),
            )
            concurrent_results = await asyncio.gather(
                service.ingest(concurrent_article),
                service.ingest(concurrent_article),
            )
            assert {result.action for result in concurrent_results} == {
                ArticleIngestionAction.CREATED,
                ArticleIngestionAction.SKIPPED,
            }
            assert len({result.article_id for result in concurrent_results}) == 1

            async with database.session() as session:
                article_count = await session.scalar(
                    sa.text("SELECT count(*) FROM articles")
                )
                original_snapshot_count = await session.scalar(
                    sa.text(
                        "SELECT count(*) FROM article_snapshots "
                        "WHERE article_id = :article_id"
                    ),
                    {"article_id": created.article_id},
                )
                linked_snapshot_id = await session.scalar(
                    sa.text(
                        "SELECT article_snapshot_id FROM generated_posts "
                        "WHERE id = :post_id"
                    ),
                    {"post_id": generated_post_id},
                )
                provenance_count = await session.scalar(
                    sa.text(
                        "SELECT count(*) FROM article_provenance_events "
                        "WHERE article_id = :article_id"
                    ),
                    {"article_id": created.article_id},
                )
                rights_count = await session.scalar(
                    sa.text(
                        "SELECT count(*) FROM article_rights_versions "
                        "WHERE article_id = :article_id"
                    ),
                    {"article_id": created.article_id},
                )

            assert article_count == 3
            assert original_snapshot_count == 2
            assert linked_snapshot_id == created.snapshot_id
            assert provenance_count == 3
            assert rights_count == 1
        finally:
            await database.close()

    asyncio.run(scenario())
