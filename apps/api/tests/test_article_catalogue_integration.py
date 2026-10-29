"""Opt-in PostgreSQL proof of the NFA-34 article catalogue."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from alembic import command
from pydantic import SecretStr

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.models.article_catalogue import ArticleCatalogueQuery
from app.providers.fixture_provider import FixtureNewsProvider
from app.providers.models import ArticleQuery
from app.repositories.article_catalogue import SqlAlchemyArticleCatalogueRepository
from app.repositories.articles import SqlAlchemyArticleRepository
from app.services.article_catalogue import (
    ArticleCatalogueNotFoundError,
    ArticleCatalogueService,
)
from app.services.article_deduplication import ArticleDeduplicationService
from tests.support.postgres import (
    DisposablePostgres,
    postgres_resources,
    require_disposable_database,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def article_catalogue_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[DisposablePostgres]:
    """Rebuild only the explicitly named disposable catalogue database."""

    database_url = require_disposable_database(
        required_name="newsflow_article_catalogue_test"
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


def test_postgresql_catalogue_filters_pages_and_hides_restricted_articles(
    article_catalogue_postgres: DisposablePostgres,
) -> None:
    resources = article_catalogue_postgres
    indexes = {
        index["name"]
        for index in sa.inspect(resources.engine).get_indexes("article_snapshots")
    }
    assert "ix_article_snapshots_publication_article" in indexes

    async def scenario() -> None:
        database = SqlAlchemyDatabase(SecretStr(resources.database_url))
        ingestion = ArticleDeduplicationService(SqlAlchemyArticleRepository(database))
        provider = FixtureNewsProvider()
        catalogue = ArticleCatalogueService(
            SqlAlchemyArticleCatalogueRepository(database),
            clock=lambda: datetime(2026, 10, 29, 15, 0, tzinfo=UTC),
        )
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

            page = await provider.fetch_articles(ArticleQuery(limit=100))
            created = [await ingestion.ingest(article) for article in page.items]

            newest = await catalogue.list_articles(
                ArticleCatalogueQuery(limit=2, sort="newest")
            )
            assert [item.category for item in newest.items] == [
                "Science",
                "Business",
            ]
            assert newest.next_cursor is not None

            continuation = await catalogue.list_articles(
                ArticleCatalogueQuery(
                    limit=2,
                    sort="newest",
                    cursor=newest.next_cursor,
                )
            )
            assert [item.category for item in continuation.items] == ["Technology"]
            assert continuation.next_cursor is None

            search = await catalogue.list_articles(
                ArticleCatalogueQuery(search="energy-efficient")
            )
            assert len(search.items) == 1
            assert "energy-efficient" in search.items[0].title

            filtered = await catalogue.list_articles(
                ArticleCatalogueQuery(
                    provider="fixture-v1",
                    published_from=datetime(2026, 10, 13, tzinfo=UTC),
                    published_to=datetime(2026, 10, 14, 23, 59, tzinfo=UTC),
                    sort="oldest",
                )
            )
            assert [item.category for item in filtered.items] == [
                "Business",
                "Science",
            ]

            injection = await catalogue.list_articles(
                ArticleCatalogueQuery(search="%' OR 1=1 --")
            )
            assert injection.items == []

            restricted_id = created[0].article_id
            async with database.session() as session:
                async with session.begin():
                    await session.execute(
                        sa.text(
                            """
                            UPDATE article_rights_versions
                            SET display_allowed = false
                            WHERE article_id = :article_id
                            """
                        ),
                        {"article_id": restricted_id},
                    )

            with pytest.raises(ArticleCatalogueNotFoundError):
                await catalogue.get_article(restricted_id)
            visible = await catalogue.list_articles(ArticleCatalogueQuery())
            assert restricted_id not in {item.id for item in visible.items}
        finally:
            await database.close()

    asyncio.run(scenario())
