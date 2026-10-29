"""NFA-33 reusable article synchronisation workflow tests."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.models.article_sync import (
    SyncCheckpoint,
    SyncErrorCategory,
    SyncJobRecord,
    SyncJobStatus,
    SyncStatistics,
    SyncTriggerType,
)
from app.providers.exceptions import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    SourceNotAuthorisedError,
)
from app.providers.fixture_provider import FixtureNewsProvider
from app.providers.models import (
    ArticleQuery,
    NewsArticle,
    ProviderCapabilities,
    ProviderPage,
)
from app.repositories.article_sync import ActiveSyncJobError, ArticleSyncRepositoryError
from app.repositories.articles import (
    ArticleIdentityConflictError,
    ArticleIngestionAction,
    ArticleIngestionResult,
)
from app.services.article_sync import (
    ArticleSyncScheduler,
    ArticleSyncService,
    ArticleSyncUnavailableError,
)

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


def run(coroutine):
    """Run one asynchronous operation."""

    return asyncio.run(coroutine)


class RecordingProvider:
    """Wrap the synthetic provider and optionally fail initial requests."""

    def __init__(
        self,
        *,
        failures: list[Exception] | None = None,
    ) -> None:
        self._provider = FixtureNewsProvider()
        self.failures = list(failures or [])
        self.queries: list[ArticleQuery] = []

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._provider.capabilities

    async def fetch_articles(self, query: ArticleQuery) -> ProviderPage:
        self.queries.append(query)
        if self.failures:
            raise self.failures.pop(0)
        return await self._provider.fetch_articles(query)

    async def fetch_article(self, source_item_id: str) -> NewsArticle:
        return await self._provider.fetch_article(source_item_id)


@dataclass
class InMemoryIngestion:
    """Return deterministic actions without using PostgreSQL."""

    existing: set[str] = field(default_factory=set)
    reject: set[str] = field(default_factory=set)

    async def ingest(self, article: NewsArticle) -> ArticleIngestionResult:
        if article.source_item_id in self.reject:
            raise ArticleIdentityConflictError("Synthetic identity conflict.")
        action = (
            ArticleIngestionAction.SKIPPED
            if article.source_item_id in self.existing
            else ArticleIngestionAction.CREATED
        )
        self.existing.add(article.source_item_id)
        return ArticleIngestionResult(
            article_id=uuid4(),
            snapshot_id=uuid4(),
            action=action,
        )


@dataclass
class InMemorySyncRepository:
    """Durable-state fake following the repository protocol."""

    enabled: bool = True
    admins: set[UUID] = field(default_factory=set)
    jobs: dict[UUID, SyncJobRecord] = field(default_factory=dict)
    checkpoint: SyncCheckpoint | None = None
    next_scheduled_at: datetime | None = None
    stale_recoveries: int = 0

    async def source_profile_enabled(self, profile_key: str) -> bool:
        return self.enabled and profile_key == "fixture-v1"

    async def user_is_admin(self, user_id: UUID) -> bool:
        return user_id in self.admins

    async def recover_stale_jobs(self, *, checked_at: datetime) -> int:
        recovered = 0
        for job_id, job in list(self.jobs.items()):
            if (
                job.status in {SyncJobStatus.PENDING, SyncJobStatus.RUNNING}
                and job.lease_expires_at is not None
                and job.lease_expires_at <= checked_at
            ):
                self.jobs[job_id] = job.model_copy(
                    update={
                        "status": SyncJobStatus.INTERRUPTED,
                        "completed_at": checked_at,
                        "lease_expires_at": None,
                        "error_code": "SYNC_INTERRUPTED",
                        "error_summary": (
                            "The previous worker stopped before completing."
                        ),
                        "updated_at": checked_at,
                    }
                )
                recovered += 1
        self.stale_recoveries += recovered
        return recovered

    async def create_job(
        self,
        *,
        provider_id: str,
        trigger_type: SyncTriggerType,
        requested_by_user_id: UUID | None,
        scheduled_for: datetime | None,
        created_at: datetime,
        lease_duration: timedelta,
    ) -> SyncJobRecord:
        if any(
            job.provider_id == provider_id
            and job.status in {SyncJobStatus.PENDING, SyncJobStatus.RUNNING}
            for job in self.jobs.values()
        ):
            raise ActiveSyncJobError
        job = SyncJobRecord(
            id=uuid4(),
            provider_id=provider_id,
            trigger_type=trigger_type,
            status=SyncJobStatus.PENDING,
            requested_by_user_id=requested_by_user_id,
            scheduled_for=scheduled_for,
            lease_expires_at=created_at + lease_duration,
            created_at=created_at,
            updated_at=created_at,
        )
        self.jobs[job.id] = job
        return job

    async def claim_job(
        self,
        *,
        job_id: UUID,
        started_at: datetime,
        lease_duration: timedelta,
    ) -> SyncJobRecord | None:
        job = self.jobs.get(job_id)
        if job is None or job.status != SyncJobStatus.PENDING:
            return None
        claimed = job.model_copy(
            update={
                "status": SyncJobStatus.RUNNING,
                "started_at": started_at,
                "lease_expires_at": started_at + lease_duration,
                "updated_at": started_at,
            }
        )
        self.jobs[job_id] = claimed
        return claimed

    async def renew_lease(
        self,
        *,
        job_id: UUID,
        checked_at: datetime,
        lease_duration: timedelta,
    ) -> bool:
        job = self.jobs.get(job_id)
        if job is None or job.status != SyncJobStatus.RUNNING:
            return False
        self.jobs[job_id] = job.model_copy(
            update={"lease_expires_at": checked_at + lease_duration}
        )
        return True

    async def finish_job(
        self,
        *,
        job_id: UUID,
        status: SyncJobStatus,
        statistics: SyncStatistics,
        checkpoint_from: datetime | None,
        checkpoint_candidate: datetime | None,
        completed_at: datetime,
        error_code: str | None,
        error_summary: str | None,
        error_category: SyncErrorCategory | None,
        failed_stage: str | None,
    ) -> SyncJobRecord | None:
        job = self.jobs.get(job_id)
        if job is None or job.status != SyncJobStatus.RUNNING:
            return None
        finished = job.model_copy(
            update={
                "status": status,
                "statistics": statistics,
                "checkpoint_from": checkpoint_from,
                "checkpoint_candidate": checkpoint_candidate,
                "completed_at": completed_at,
                "lease_expires_at": None,
                "error_code": error_code,
                "error_summary": error_summary,
                "error_category": error_category,
                "failed_stage": failed_stage,
                "updated_at": completed_at,
            }
        )
        self.jobs[job_id] = finished
        return finished

    async def get_job(self, job_id: UUID) -> SyncJobRecord | None:
        return self.jobs.get(job_id)

    async def get_checkpoint(self, provider_id: str) -> SyncCheckpoint | None:
        if self.checkpoint is not None and self.checkpoint.provider_id == provider_id:
            return self.checkpoint
        return None

    async def advance_checkpoint(
        self,
        *,
        provider_id: str,
        publication_at: datetime | None,
        completed_at: datetime,
    ) -> None:
        self.checkpoint = SyncCheckpoint(
            provider_id=provider_id,
            last_successful_publication_at=publication_at,
            last_successful_completed_at=completed_at,
            next_scheduled_at=self.next_scheduled_at,
        )

    async def reserve_scheduled_run(
        self,
        *,
        provider_id: str,
        checked_at: datetime,
        interval: timedelta,
    ) -> bool:
        del provider_id
        if self.next_scheduled_at is not None and self.next_scheduled_at > checked_at:
            return False
        self.next_scheduled_at = checked_at + interval
        return True


def make_service(
    *,
    provider: RecordingProvider | None = None,
    ingestion: InMemoryIngestion | None = None,
    repository: InMemorySyncRepository | None = None,
    max_retries: int = 2,
    sleeps: list[float] | None = None,
    timer: Callable[[], float] | None = None,
) -> tuple[
    ArticleSyncService,
    RecordingProvider,
    InMemoryIngestion,
    InMemorySyncRepository,
]:
    active_provider = provider or RecordingProvider()
    active_ingestion = ingestion or InMemoryIngestion()
    active_repository = repository or InMemorySyncRepository()
    recorded_sleeps = sleeps if sleeps is not None else []

    async def sleeper(delay: float) -> None:
        recorded_sleeps.append(delay)

    service = ArticleSyncService(
        provider=active_provider,
        source_profile_key="fixture-v1",
        ingestion=active_ingestion,  # type: ignore[arg-type]
        repository=active_repository,
        page_size=2,
        max_retries=max_retries,
        retry_base_seconds=0.25,
        lease_duration=timedelta(minutes=5),
        clock=lambda: NOW,
        sleeper=sleeper,
        timer=timer or (lambda: 0.0),
    )
    return service, active_provider, active_ingestion, active_repository


def start_and_run(service: ArticleSyncService) -> SyncJobRecord:
    requester = uuid4()
    job = run(
        service.start_job(
            trigger_type=SyncTriggerType.MANUAL,
            requested_by_user_id=requester,
        )
    )
    return run(service.run_job(job.id))


def test_sync_processes_pages_and_records_accurate_statistics() -> None:
    service, provider, _, repository = make_service()

    result = start_and_run(service)

    assert result.status == SyncJobStatus.COMPLETED
    assert result.statistics == SyncStatistics(
        retrieved=3,
        created=3,
        updated=0,
        skipped=0,
        rejected=0,
        provider_attempts=2,
    )
    assert len(provider.queries) == 2
    assert repository.checkpoint is not None
    assert repository.checkpoint.last_successful_publication_at == datetime(
        2026, 10, 14, 11, 0, tzinfo=UTC
    )


def test_success_completion_event_includes_job_correlation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service, _, _, _ = make_service()

    with caplog.at_level(logging.INFO, logger="app.services.article_sync"):
        result = start_and_run(service)

    completion = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "article_sync_completed"
    )
    assert completion.job_id == str(result.id)
    assert completion.counts["retrieved"] == 3
    assert completion.provider_duration_ms == 0


def test_repeated_sync_is_incremental_and_does_not_duplicate_articles() -> None:
    service, provider, ingestion, repository = make_service()
    first = start_and_run(service)

    second = start_and_run(service)

    assert first.statistics.created == 3
    assert second.status == SyncJobStatus.COMPLETED
    assert second.statistics.retrieved == 0
    assert len(ingestion.existing) == 3
    assert provider.queries[-1].published_after == (
        repository.checkpoint.last_successful_publication_at
    )


def test_temporary_provider_failure_uses_bounded_exponential_retry() -> None:
    sleeps: list[float] = []
    provider = RecordingProvider(
        failures=[ProviderUnavailableError(), ProviderUnavailableError()]
    )
    service, _, _, _ = make_service(provider=provider, sleeps=sleeps)

    result = start_and_run(service)

    assert result.status == SyncJobStatus.COMPLETED
    assert result.statistics.provider_attempts == 4
    assert sleeps == [0.25, 0.5]


def test_provider_timeout_is_retried_and_classified_safely() -> None:
    provider = RecordingProvider(
        failures=[ProviderTimeoutError(), ProviderTimeoutError()]
    )
    service, _, _, _ = make_service(provider=provider, max_retries=1)

    result = start_and_run(service)

    assert result.status == SyncJobStatus.FAILED
    assert result.error_code == "PROVIDER_TIMEOUT"
    assert result.error_category == SyncErrorCategory.PROVIDER_TIMEOUT
    assert result.failed_stage == "provider_request"
    assert result.statistics.provider_attempts == 2
    assert result.statistics.provider_failures == 2


def test_provider_request_duration_is_recorded() -> None:
    moments = iter([0.0, 0.012, 0.012, 0.032])
    service, _, _, _ = make_service(timer=lambda: next(moments))

    result = start_and_run(service)

    assert result.statistics.provider_duration_ms == 32


def test_permanent_provider_failure_is_not_retried_or_checkpointed() -> None:
    provider = RecordingProvider(failures=[SourceNotAuthorisedError()])
    service, _, _, repository = make_service(provider=provider)

    result = start_and_run(service)

    assert result.status == SyncJobStatus.FAILED
    assert result.error_code == "SOURCE_NOT_AUTHORISED"
    assert result.statistics.provider_attempts == 1
    assert len(provider.queries) == 1
    assert repository.checkpoint is None


def test_unexpected_provider_failure_is_stored_and_logged_safely(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "restricted-provider-payload-and-password"
    provider = RecordingProvider(failures=[RuntimeError(secret)])
    service, _, _, _ = make_service(provider=provider)

    with caplog.at_level(logging.INFO, logger="app.services.article_sync"):
        result = start_and_run(service)

    assert result.status == SyncJobStatus.FAILED
    assert result.error_code == "UNEXPECTED_SYNC_FAILURE"
    assert result.error_category == SyncErrorCategory.INTERNAL_PIPELINE
    assert result.failed_stage == "pipeline"
    assert secret not in caplog.text
    assert "article_sync_started" in caplog.text
    assert "article_sync_provider_request_failed" in caplog.text
    assert "article_sync_failed" in caplog.text


def test_rejected_article_makes_job_partial_and_keeps_old_checkpoint(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = RecordingProvider()
    rejected_id = (
        run(provider.fetch_articles(ArticleQuery(limit=1))).items[0].source_item_id
    )
    ingestion = InMemoryIngestion(reject={rejected_id})
    old_checkpoint = SyncCheckpoint(
        provider_id="fixture",
        last_successful_publication_at=datetime(2026, 10, 1, tzinfo=UTC),
        last_successful_completed_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    repository = InMemorySyncRepository(checkpoint=old_checkpoint)
    service, _, _, _ = make_service(
        provider=provider,
        ingestion=ingestion,
        repository=repository,
    )

    with caplog.at_level(logging.INFO, logger="app.services.article_sync"):
        result = start_and_run(service)

    assert result.status == SyncJobStatus.PARTIALLY_COMPLETED
    assert result.statistics.rejected == 1
    assert repository.checkpoint == old_checkpoint
    assert "article_sync_partially_completed" in caplog.text


def test_database_write_failure_emits_safe_operational_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FailingRepository(InMemorySyncRepository):
        async def finish_job(self, **kwargs):  # type: ignore[no-untyped-def]
            del kwargs
            raise ArticleSyncRepositoryError("database password=do-not-log")

    service, _, _, _ = make_service(repository=FailingRepository())

    with caplog.at_level(logging.INFO, logger="app.services.article_sync"):
        with pytest.raises(ArticleSyncRepositoryError):
            start_and_run(service)

    assert "do-not-log" not in caplog.text
    record = next(
        item
        for item in caplog.records
        if getattr(item, "event", None) == "article_sync_failure_record_unavailable"
    )
    assert record.error_category == "database_error"
    assert record.failed_stage == "database"


def test_conflicting_job_is_rejected_and_stale_job_can_be_recovered() -> None:
    service, _, _, repository = make_service()
    requester = uuid4()
    first = run(
        service.start_job(
            trigger_type=SyncTriggerType.MANUAL,
            requested_by_user_id=requester,
        )
    )

    with pytest.raises(ActiveSyncJobError):
        run(
            service.start_job(
                trigger_type=SyncTriggerType.MANUAL,
                requested_by_user_id=requester,
            )
        )

    repository.jobs[first.id] = first.model_copy(
        update={"lease_expires_at": NOW - timedelta(seconds=1)}
    )
    replacement = run(
        service.start_job(
            trigger_type=SyncTriggerType.MANUAL,
            requested_by_user_id=requester,
        )
    )

    assert repository.jobs[first.id].status == SyncJobStatus.INTERRUPTED
    assert replacement.status == SyncJobStatus.PENDING
    assert repository.stale_recoveries == 1


def test_disabled_source_fails_before_provider_access() -> None:
    repository = InMemorySyncRepository(enabled=False)
    service, provider, _, _ = make_service(repository=repository)

    with pytest.raises(ArticleSyncUnavailableError):
        run(
            service.start_job(
                trigger_type=SyncTriggerType.MANUAL,
                requested_by_user_id=uuid4(),
            )
        )

    assert provider.queries == []


def test_scheduler_uses_same_service_and_durable_due_reservation() -> None:
    service, _, _, _ = make_service()
    scheduler = ArticleSyncScheduler(
        service=service,
        interval=timedelta(hours=4),
    )

    first = run(scheduler.run_due())
    second = run(scheduler.run_due())

    assert first is not None
    assert first.trigger_type == SyncTriggerType.SCHEDULED
    assert first.status == SyncJobStatus.COMPLETED
    assert second is None
