"""Reusable scheduled and manual article synchronisation workflow."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.article_sync import (
    SyncJobRecord,
    SyncJobStatus,
    SyncStatistics,
    SyncTriggerType,
)
from app.providers.base import NewsProvider
from app.providers.exceptions import ProviderError
from app.providers.models import ArticleQuery, ProviderPage
from app.repositories.article_sync import (
    ActiveSyncJobError,
    ArticleSyncRepository,
    ArticleSyncRepositoryError,
)
from app.repositories.articles import (
    ArticleIdentityConflictError,
    ArticleIngestionAction,
    ArticleRepositoryError,
)
from app.services.article_deduplication import (
    ArticleDeduplicationService,
    ArticleStorageNotPermittedError,
)

logger = logging.getLogger(__name__)


class ArticleSyncUnavailableError(RuntimeError):
    """Raised before access when the configured source cannot be used."""


class ArticleSyncJobNotFoundError(RuntimeError):
    """Raised when no job exists for a supplied identifier."""


class ArticleSyncLeaseLostError(RuntimeError):
    """Raised when another worker owns or recovered the durable lease."""


class ArticleSyncPipelineError(RuntimeError):
    """Safe internal pipeline failure with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.safe_message = message
        super().__init__(message)


class ArticleSyncService:
    """Coordinate providers, validation, deduplication, rights, and job state."""

    def __init__(
        self,
        *,
        provider: NewsProvider,
        source_profile_key: str,
        ingestion: ArticleDeduplicationService,
        repository: ArticleSyncRepository,
        page_size: int = 50,
        max_retries: int = 2,
        retry_base_seconds: float = 1.0,
        lease_duration: timedelta = timedelta(minutes=5),
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100.")
        if not 0 <= max_retries <= 5:
            raise ValueError("max_retries must be between 0 and 5.")
        if retry_base_seconds < 0:
            raise ValueError("retry_base_seconds cannot be negative.")
        if lease_duration.total_seconds() < 30:
            raise ValueError("lease_duration must be at least 30 seconds.")
        self._provider = provider
        self._source_profile_key = source_profile_key
        self._ingestion = ingestion
        self._repository = repository
        self._page_size = page_size
        self._max_retries = max_retries
        self._retry_base_seconds = retry_base_seconds
        self._lease_duration = lease_duration
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleeper = sleeper

    @property
    def provider_id(self) -> str:
        """Return the non-secret provider identifier used for job locking."""

        return self._provider.provider_id

    async def start_job(
        self,
        *,
        trigger_type: SyncTriggerType,
        requested_by_user_id: UUID | None = None,
        scheduled_for: datetime | None = None,
    ) -> SyncJobRecord:
        """Create a pending job after checking source permission and stale leases."""

        now = self._now()
        if trigger_type == SyncTriggerType.MANUAL and requested_by_user_id is None:
            raise ValueError("Manual synchronisation requires a requesting user.")
        if not await self._repository.source_profile_enabled(self._source_profile_key):
            raise ArticleSyncUnavailableError(
                "The configured source profile is not enabled and approved."
            )
        await self._repository.recover_stale_jobs(checked_at=now)
        return await self._repository.create_job(
            provider_id=self.provider_id,
            trigger_type=trigger_type,
            requested_by_user_id=requested_by_user_id,
            scheduled_for=scheduled_for,
            created_at=now,
            lease_duration=self._lease_duration,
        )

    async def run_job(self, job_id: UUID) -> SyncJobRecord:
        """Claim and run one job, returning its final durable record."""

        started_at = self._now()
        job = await self._repository.claim_job(
            job_id=job_id,
            started_at=started_at,
            lease_duration=self._lease_duration,
        )
        if job is None:
            existing = await self._repository.get_job(job_id)
            if existing is None:
                raise ArticleSyncJobNotFoundError
            if existing.status in {
                SyncJobStatus.PENDING,
                SyncJobStatus.RUNNING,
            }:
                raise ArticleSyncLeaseLostError
            return existing

        checkpoint_from: datetime | None = None
        counters = {
            "retrieved": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "rejected": 0,
            "provider_attempts": 0,
        }
        checkpoint_candidate = checkpoint_from

        try:
            checkpoint = await self._repository.get_checkpoint(self.provider_id)
            checkpoint_from = (
                checkpoint.last_successful_publication_at
                if checkpoint is not None
                and self._provider.capabilities.incremental_retrieval
                else None
            )
            checkpoint_candidate = checkpoint_from
            cursor: str | None = None
            observed_cursors: set[str] = set()
            while True:
                await self._renew_lease(job_id)
                page = await self._fetch_page(
                    ArticleQuery(
                        limit=self._page_size,
                        cursor=cursor,
                        published_after=checkpoint_from,
                    ),
                    counters=counters,
                )
                if page.provider_id != self.provider_id:
                    raise ArticleSyncPipelineError(
                        "PROVIDER_ID_MISMATCH",
                        "The provider returned an unexpected identity.",
                    )

                for article in page.items:
                    counters["retrieved"] += 1
                    checkpoint_candidate = max(
                        filter(
                            None,
                            (checkpoint_candidate, article.publication_date),
                        )
                    )
                    try:
                        result = await self._ingestion.ingest(article)
                    except (
                        ArticleIdentityConflictError,
                        ArticleStorageNotPermittedError,
                    ):
                        counters["rejected"] += 1
                        logger.warning(
                            "article_sync_item_rejected job_id=%s provider_id=%s "
                            "source_item_id=%s",
                            job_id,
                            self.provider_id,
                            article.source_item_id,
                        )
                        continue

                    counter_name = {
                        ArticleIngestionAction.CREATED: "created",
                        ArticleIngestionAction.UPDATED: "updated",
                        ArticleIngestionAction.SKIPPED: "skipped",
                    }[result.action]
                    counters[counter_name] += 1

                if page.next_cursor is None:
                    break
                if page.next_cursor in observed_cursors:
                    raise ArticleSyncPipelineError(
                        "REPEATED_PROVIDER_CURSOR",
                        "The provider repeated a pagination cursor.",
                    )
                observed_cursors.add(page.next_cursor)
                cursor = page.next_cursor

            statistics = SyncStatistics(**counters)
            completed_at = self._now()
            status = (
                SyncJobStatus.PARTIALLY_COMPLETED
                if statistics.rejected
                else SyncJobStatus.COMPLETED
            )
            completed = await self._repository.finish_job(
                job_id=job_id,
                status=status,
                statistics=statistics,
                checkpoint_from=checkpoint_from,
                checkpoint_candidate=checkpoint_candidate,
                completed_at=completed_at,
                error_code=("ARTICLE_REJECTIONS" if statistics.rejected else None),
                error_summary=(
                    "One or more article records were safely rejected."
                    if statistics.rejected
                    else None
                ),
            )
            if completed is None:
                raise ArticleSyncLeaseLostError
            if status == SyncJobStatus.COMPLETED:
                try:
                    await self._repository.advance_checkpoint(
                        provider_id=self.provider_id,
                        publication_at=checkpoint_candidate,
                        completed_at=completed_at,
                    )
                except ArticleSyncRepositoryError:
                    logger.error(
                        "article_sync_checkpoint_deferred job_id=%s provider_id=%s",
                        job_id,
                        self.provider_id,
                    )
            self._log_completion(completed)
            return completed
        except (
            ProviderError,
            ArticleRepositoryError,
            ArticleSyncRepositoryError,
            ArticleSyncPipelineError,
        ) as exc:
            return await self._record_failure(
                job_id=job_id,
                counters=counters,
                checkpoint_from=checkpoint_from,
                checkpoint_candidate=checkpoint_candidate,
                error=exc,
            )

    async def get_job(self, job_id: UUID) -> SyncJobRecord:
        """Return a job or a stable not-found error."""

        job = await self._repository.get_job(job_id)
        if job is None:
            raise ArticleSyncJobNotFoundError
        return job

    async def reserve_scheduled_run(
        self,
        *,
        interval: timedelta,
    ) -> bool:
        """Atomically reserve a provider schedule slot across all workers."""

        if interval.total_seconds() < 60:
            raise ValueError("The scheduled interval must be at least 60 seconds.")
        return await self._repository.reserve_scheduled_run(
            provider_id=self.provider_id,
            checked_at=self._now(),
            interval=interval,
        )

    async def _fetch_page(
        self,
        query: ArticleQuery,
        *,
        counters: dict[str, int],
    ) -> ProviderPage:
        attempts = 0
        while True:
            attempts += 1
            counters["provider_attempts"] += 1
            try:
                return await self._provider.fetch_articles(query)
            except ProviderError as exc:
                if not exc.retryable or attempts > self._max_retries:
                    raise
                delay = self._retry_base_seconds * (2 ** (attempts - 1))
                logger.warning(
                    "article_sync_provider_retry provider_id=%s code=%s "
                    "attempt=%s delay_seconds=%s",
                    self.provider_id,
                    exc.code.value,
                    attempts,
                    delay,
                )
                await self._sleeper(delay)

    async def _renew_lease(self, job_id: UUID) -> None:
        renewed = await self._repository.renew_lease(
            job_id=job_id,
            checked_at=self._now(),
            lease_duration=self._lease_duration,
        )
        if not renewed:
            raise ArticleSyncLeaseLostError

    async def _record_failure(
        self,
        *,
        job_id: UUID,
        counters: dict[str, int],
        checkpoint_from: datetime | None,
        checkpoint_candidate: datetime | None,
        error: Exception,
    ) -> SyncJobRecord:
        status = (
            SyncJobStatus.PARTIALLY_COMPLETED
            if counters["created"] + counters["updated"] + counters["skipped"] > 0
            else SyncJobStatus.FAILED
        )
        if isinstance(error, ProviderError):
            code = error.code.value
            summary = error.safe_message
        elif isinstance(error, ArticleSyncPipelineError):
            code = error.code
            summary = error.safe_message
        elif isinstance(error, ArticleRepositoryError):
            code = "ARTICLE_STORAGE_FAILED"
            summary = "Article storage failed safely."
        else:
            code = "SYNC_PERSISTENCE_FAILED"
            summary = "Synchronisation persistence failed safely."
        statistics = SyncStatistics(**counters)
        completed = await self._repository.finish_job(
            job_id=job_id,
            status=status,
            statistics=statistics,
            checkpoint_from=checkpoint_from,
            checkpoint_candidate=checkpoint_candidate,
            completed_at=self._now(),
            error_code=code,
            error_summary=summary,
        )
        if completed is None:
            raise ArticleSyncLeaseLostError from error
        logger.warning(
            "article_sync_failed job_id=%s provider_id=%s status=%s code=%s",
            job_id,
            self.provider_id,
            status.value,
            code,
        )
        return completed

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("The synchronisation clock must include a timezone.")
        return value.astimezone(UTC)

    @staticmethod
    def _log_completion(job: SyncJobRecord) -> None:
        logger.info(
            "article_sync_completed job_id=%s provider_id=%s status=%s "
            "retrieved=%s created=%s updated=%s skipped=%s rejected=%s",
            job.id,
            job.provider_id,
            job.status.value,
            job.statistics.retrieved,
            job.statistics.created,
            job.statistics.updated,
            job.statistics.skipped,
            job.statistics.rejected,
        )


class ArticleSyncScheduler:
    """One-shot durable scheduler boundary for cron or a managed scheduler."""

    def __init__(
        self,
        *,
        service: ArticleSyncService,
        interval: timedelta,
    ) -> None:
        self._service = service
        self._interval = interval

    async def run_due(self) -> SyncJobRecord | None:
        """Run once when this process wins the durable schedule reservation."""

        reserved = await self._service.reserve_scheduled_run(interval=self._interval)
        if not reserved:
            return None
        try:
            job = await self._service.start_job(
                trigger_type=SyncTriggerType.SCHEDULED,
                scheduled_for=datetime.now(UTC),
            )
        except ActiveSyncJobError:
            return None
        return await self._service.run_job(job.id)
