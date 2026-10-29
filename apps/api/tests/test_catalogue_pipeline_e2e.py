"""NFA-36 complete synthetic provider-to-catalogue PostgreSQL proof."""

import asyncio
import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from io import StringIO
from typing import Any
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.core.logging_config import StructuredJsonFormatter
from app.database.sqlalchemy import SqlAlchemyDatabase
from app.main import create_app
from app.models.article_rights import (
    ArticleRightsPolicy,
    ArticleUseOperation,
    RightsDecisionReason,
)
from app.models.article_sync import SyncJobStatus
from app.providers.base import NewsProvider
from app.providers.fixture_provider import FixtureNewsProvider
from app.providers.models import (
    ArticleQuery,
    NewsArticle,
    ProviderCapabilities,
    ProviderPage,
)
from app.repositories.article_catalogue import SqlAlchemyArticleCatalogueRepository
from app.repositories.article_rights import SqlAlchemyArticleRightsRepository
from app.repositories.article_sync import SqlAlchemyArticleSyncRepository
from app.repositories.articles import (
    ArticleIngestionAction,
    ArticleRepositoryError,
    SqlAlchemyArticleRepository,
)
from app.services.article_catalogue import ArticleCatalogueService
from app.services.article_deduplication import ArticleDeduplicationService
from app.services.article_rights import ArticleRightsService
from app.services.article_sync import ArticleSyncService
from tests.support.article_pipeline import (
    invalid_article_cases,
    synthetic_article_records,
)
from tests.support.postgres import (
    DisposablePostgres,
    postgres_resources,
    require_disposable_database,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 29, 15, 0, tzinfo=UTC)
VALID_PASSWORD = "Pipeline-Test-Password-42!"
PUBLIC_ARTICLE_FIELDS = {
    "id",
    "title",
    "description",
    "source_url",
    "provider",
    "published_at",
    "category",
    "attribution",
}


@pytest.fixture
def catalogue_pipeline_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[DisposablePostgres]:
    """Rebuild only the explicitly approved NFA-36 pipeline database."""

    database_url = require_disposable_database(required_name="newsflow_pipeline_test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NEWS_SOURCE_MODE", "fixture")
    resources = postgres_resources(database_url)
    command.downgrade(resources.alembic_config, "base")
    command.upgrade(resources.alembic_config, "head")
    try:
        yield resources
    finally:
        command.downgrade(resources.alembic_config, "base")
        resources.engine.dispose()


class FailingIngestion:
    """Simulate a safe persistence failure after provider retrieval."""

    async def ingest(self, article: NewsArticle):
        del article
        raise ArticleRepositoryError(
            "DATABASE_URL=postgresql://pipeline:secret-password@database/newsflow"
        )


class CountingProvider:
    """Prove source authorisation is checked before provider access."""

    def __init__(self, provider: NewsProvider) -> None:
        self._provider = provider
        self.fetch_calls = 0

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._provider.capabilities

    async def fetch_articles(self, query: ArticleQuery) -> ProviderPage:
        self.fetch_calls += 1
        return await self._provider.fetch_articles(query)

    async def fetch_article(self, source_item_id: str) -> NewsArticle:
        self.fetch_calls += 1
        return await self._provider.fetch_article(source_item_id)


def _insert_approved_source(resources: DisposablePostgres) -> None:
    with resources.engine.begin() as connection:
        connection.execute(
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


def _sync_service(
    database: SqlAlchemyDatabase,
    repository: SqlAlchemyArticleSyncRepository,
    records: list[dict[str, Any]],
    *,
    ingestion: object | None = None,
) -> ArticleSyncService:
    active_ingestion = ingestion or ArticleDeduplicationService(
        SqlAlchemyArticleRepository(database)
    )
    return ArticleSyncService(
        provider=FixtureNewsProvider(records),
        source_profile_key="fixture-v1",
        ingestion=active_ingestion,  # type: ignore[arg-type]
        repository=repository,
        page_size=2,
        max_retries=1,
        retry_base_seconds=0,
        lease_duration=timedelta(minutes=5),
    )


def _trigger_sync(client: TestClient) -> dict[str, Any]:
    csrf_token = client.cookies.get("newsflow_csrf")
    response = client.post(
        "/api/v1/admin/articles/sync",
        headers={"X-CSRF-Token": csrf_token or ""},
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    status_response = client.get(f"/api/v1/admin/articles/sync/{job_id}")
    assert status_response.status_code == 200
    return status_response.json()


def _counts(resources: DisposablePostgres) -> dict[str, int]:
    with resources.engine.connect() as connection:
        return {
            table: int(
                connection.execute(
                    sa.text(f"SELECT count(*) FROM {table}")
                ).scalar_one()
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


def test_complete_synthetic_ingestion_and_catalogue_pipeline(
    catalogue_pipeline_postgres: DisposablePostgres,
    caplog: pytest.LogCaptureFixture,
) -> None:
    resources = catalogue_pipeline_postgres
    _insert_approved_source(resources)
    database = SqlAlchemyDatabase(SecretStr(resources.database_url))
    sync_repository = SqlAlchemyArticleSyncRepository(database)
    initial_service = _sync_service(
        database,
        sync_repository,
        synthetic_article_records("valid"),
    )
    catalogue_service = ArticleCatalogueService(
        SqlAlchemyArticleCatalogueRepository(database),
        clock=lambda: NOW,
    )
    settings = Settings(
        _env_file=None,
        app_env="test",
        news_source_mode="fixture",
        database_url=SecretStr(resources.database_url),
        log_format="console",
        registration_rate_limit_attempts=20,
        login_rate_limit_attempts=20,
        manual_sync_rate_limit_attempts=20,
    )
    application = create_app(
        settings=settings,
        article_catalogue_service=catalogue_service,
        article_sync_repository=sync_repository,
        article_sync_service=initial_service,
    )

    sync_logger = logging.getLogger("app.services.article_sync")
    # Alembic's in-process test configuration disables existing non-Alembic
    # loggers. Production migrations run separately, so re-enable this logger
    # before exercising and inspecting the application workflow.
    sync_logger.disabled = False
    sync_log_stream = StringIO()
    sync_log_handler = logging.StreamHandler(sync_log_stream)
    sync_log_handler.setFormatter(StructuredJsonFormatter())
    with caplog.at_level(logging.INFO, logger="app.services.article_sync"):
        sync_logger.addHandler(sync_log_handler)
        with TestClient(application) as client:
            registration = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "pipeline.admin@example.com",
                    "password": VALID_PASSWORD,
                },
            )
            assert registration.status_code == 201
            administrator_id = UUID(registration.json()["id"])
            with resources.engine.begin() as connection:
                connection.execute(
                    sa.text("UPDATE users SET role = 'admin' WHERE id = :user_id"),
                    {"user_id": administrator_id},
                )

            login = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "pipeline.admin@example.com",
                    "password": VALID_PASSWORD,
                },
            )
            assert login.status_code == 200

            first_job = _trigger_sync(client)
            assert first_job["status"] == SyncJobStatus.COMPLETED.value
            assert first_job["articles_retrieved"] == 3
            assert first_job["articles_created"] == 3
            assert first_job["articles_updated"] == 0
            assert first_job["articles_skipped"] == 0
            assert first_job["articles_rejected"] == 0
            assert first_job["provider_attempts"] == 2

            collection = client.get("/api/articles?limit=100&sort=oldest")
            assert collection.status_code == 200
            items = collection.json()["items"]
            assert len(items) == 3
            assert all(set(item) == PUBLIC_ARTICLE_FIELDS for item in items)
            assert all("permitted_content" not in item for item in items)
            assert all(item["provider"] == "fixture-v1" for item in items)
            assert all(item["attribution"]["text"] for item in items)

            technology_item = next(
                item for item in items if item["category"] == "Technology"
            )
            detail = client.get(f"/api/articles/{technology_item['id']}")
            assert detail.status_code == 200
            assert detail.json() == technology_item
            assert detail.headers["Cache-Control"] == "private, no-store"

            first_counts = _counts(resources)
            assert first_counts == {
                "articles": 3,
                "article_snapshots": 3,
                "article_provenance_events": 3,
                "article_rights_versions": 3,
                "article_sync_jobs": 1,
                "article_sync_checkpoints": 1,
            }

            application.state.article_sync_service = _sync_service(
                database,
                sync_repository,
                synthetic_article_records("updated"),
            )
            update_job = _trigger_sync(client)
            assert update_job["status"] == SyncJobStatus.COMPLETED.value
            assert update_job["articles_retrieved"] == 1
            assert update_job["articles_updated"] == 1
            assert update_job["articles_created"] == 0

            updated_detail = client.get(f"/api/articles/{technology_item['id']}")
            assert updated_detail.status_code == 200
            assert "publishes updated" in updated_detail.json()["title"]

            application.state.article_sync_service = _sync_service(
                database,
                sync_repository,
                synthetic_article_records("duplicates"),
            )
            duplicate_job = _trigger_sync(client)
            assert duplicate_job["status"] == SyncJobStatus.COMPLETED.value
            assert duplicate_job["articles_retrieved"] == 2
            assert duplicate_job["articles_created"] == 1
            assert duplicate_job["articles_skipped"] == 1

            repeated_job = _trigger_sync(client)
            assert repeated_job["status"] == SyncJobStatus.COMPLETED.value
            assert repeated_job["articles_retrieved"] == 0
            assert _counts(resources)["articles"] == 4

            invalid_record = invalid_article_cases()[-1]["record"]
            application.state.article_sync_service = _sync_service(
                database,
                sync_repository,
                [invalid_record],
            )
            before_invalid = _counts(resources)
            invalid_job = _trigger_sync(client)
            after_invalid = _counts(resources)
            assert invalid_job["status"] == SyncJobStatus.FAILED.value
            assert invalid_job["error_code"] == "PROVIDER_DATA_INVALID"
            assert invalid_job["error_category"] == "article_validation_error"
            assert after_invalid["articles"] == before_invalid["articles"]
            assert (
                after_invalid["article_snapshots"]
                == before_invalid["article_snapshots"]
            )

            application.state.article_sync_service = _sync_service(
                database,
                sync_repository,
                synthetic_article_records("database_failure"),
                ingestion=FailingIngestion(),
            )
            before_database_failure = _counts(resources)
            database_job = _trigger_sync(client)
            after_database_failure = _counts(resources)
            assert database_job["status"] == SyncJobStatus.FAILED.value
            assert database_job["error_category"] == "database_error"
            assert database_job["failed_stage"] == "database"
            assert (
                after_database_failure["articles"]
                == before_database_failure["articles"]
            )
            assert after_database_failure["article_sync_checkpoints"] == 1

            metrics = client.get("/api/admin/sync/metrics?window_hours=168")
            assert metrics.status_code == 200
            assert metrics.json()["articles_created"] == 4
            assert metrics.json()["articles_updated"] == 1
            assert metrics.json()["articles_skipped"] == 1
            assert metrics.json()["provider_request_failures"] >= 1
            assert metrics.json()["database_failures"] >= 1

            counting_provider = CountingProvider(
                FixtureNewsProvider(synthetic_article_records("database_failure"))
            )
            application.state.article_sync_service = ArticleSyncService(
                provider=counting_provider,
                source_profile_key="fixture-v1",
                ingestion=ArticleDeduplicationService(
                    SqlAlchemyArticleRepository(database)
                ),
                repository=sync_repository,
                retry_base_seconds=0,
                lease_duration=timedelta(minutes=5),
            )
            with resources.engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE source_profiles SET status = 'disabled' "
                        "WHERE profile_key = 'fixture-v1'"
                    )
                )
            disabled = client.post(
                "/api/v1/admin/articles/sync",
                headers={"X-CSRF-Token": client.cookies.get("newsflow_csrf") or ""},
            )
            assert disabled.status_code == 503
            assert disabled.json()["error"]["code"] == ("article_sync_source_disabled")
            assert counting_provider.fetch_calls == 0
            with resources.engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE source_profiles SET status = 'enabled' "
                        "WHERE profile_key = 'fixture-v1'"
                    )
                )
        sync_logger.removeHandler(sync_log_handler)

    asyncio.run(database.close())

    with resources.engine.connect() as connection:
        provenance_rows = connection.execute(
            sa.text(
                "SELECT ingestion_action, source_integration_ref, "
                "authorisation_reference FROM article_provenance_events "
                "ORDER BY created_at, id"
            )
        ).all()
        rights_rows = connection.execute(
            sa.text(
                "SELECT verification_status, storage_allowed, display_allowed, "
                "attribution_text FROM article_rights_versions"
            )
        ).all()
        checkpoint = connection.execute(
            sa.text(
                "SELECT last_successful_publication_at "
                "FROM article_sync_checkpoints WHERE provider_id = 'fixture'"
            )
        ).scalar_one()

    assert {row.ingestion_action for row in provenance_rows} >= {
        "created",
        "updated",
        "skipped",
    }
    assert all(row.source_integration_ref == "fixture-v1" for row in provenance_rows)
    assert all(
        row.authorisation_reference == "NFA-SRC-AUTH-001" for row in provenance_rows
    )
    assert all(row.verification_status == "verified" for row in rights_rows)
    assert all(row.storage_allowed and row.display_allowed for row in rights_rows)
    assert all(row.attribution_text for row in rights_rows)
    assert checkpoint == datetime(2026, 10, 24, 12, 0, tzinfo=UTC)

    structured_logs = [
        json.loads(line) for line in sync_log_stream.getvalue().splitlines()
    ]
    log_text = sync_log_stream.getvalue()
    logged_events = {record.get("event") for record in structured_logs}
    assert "secret-password" not in log_text
    assert "restricted-test-value" not in log_text
    assert {
        "article_sync_started",
        "article_sync_completed",
        "article_sync_failed",
    } <= logged_events
    assert any(record.get("job_id") == first_job["id"] for record in structured_logs)


def test_postgresql_rights_service_denies_restricted_ai_processing(
    catalogue_pipeline_postgres: DisposablePostgres,
) -> None:
    resources = catalogue_pipeline_postgres
    _insert_approved_source(resources)

    async def scenario() -> None:
        database = SqlAlchemyDatabase(SecretStr(resources.database_url))
        ingestion = ArticleDeduplicationService(SqlAlchemyArticleRepository(database))
        rights_repository = SqlAlchemyArticleRightsRepository(database)
        rights_service = ArticleRightsService(rights_repository)
        try:
            provider = FixtureNewsProvider(synthetic_article_records("valid")[:1])
            article = (await provider.fetch_articles(ArticleQuery(limit=1))).items[0]
            created = await ingestion.ingest(article)
            current = await rights_repository.get_current(created.article_id)
            assert current is not None
            values = current.record.model_dump(
                exclude={"id", "article_id", "version_number", "superseded_at"}
            )
            values.update(
                {
                    "ai_processing_allowed": False,
                    "derivative_output_allowed": False,
                    "effective_from": NOW,
                    "rights_last_verified_at": NOW,
                }
            )
            await rights_service.update_rights(
                article_id=created.article_id,
                policy=ArticleRightsPolicy.model_validate(values),
            )

            decision = await rights_service.can_use_article(
                article_id=created.article_id,
                operation=ArticleUseOperation.USE_FOR_AI_GENERATION,
                checked_at=NOW,
            )
            assert decision.allowed is False
            assert decision.reason == RightsDecisionReason.OPERATION_RESTRICTED
        finally:
            await database.close()

    asyncio.run(scenario())


def test_concurrent_pipeline_ingestion_creates_one_postgresql_article(
    catalogue_pipeline_postgres: DisposablePostgres,
) -> None:
    resources = catalogue_pipeline_postgres
    _insert_approved_source(resources)

    async def scenario() -> None:
        database = SqlAlchemyDatabase(SecretStr(resources.database_url))
        ingestion = ArticleDeduplicationService(SqlAlchemyArticleRepository(database))
        try:
            provider = FixtureNewsProvider(synthetic_article_records("valid")[:1])
            article = (await provider.fetch_articles(ArticleQuery(limit=1))).items[0]
            results = await asyncio.gather(
                ingestion.ingest(article),
                ingestion.ingest(article),
            )

            assert {result.action for result in results} == {
                ArticleIngestionAction.CREATED,
                ArticleIngestionAction.SKIPPED,
            }
            assert len({result.article_id for result in results}) == 1
        finally:
            await database.close()

    asyncio.run(scenario())

    counts = _counts(resources)
    assert counts["articles"] == 1
    assert counts["article_snapshots"] == 1
    assert counts["article_provenance_events"] == 2
