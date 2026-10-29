"""Reusable scheduled and manual article synchronisation workflow."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.logging_config import log_event
from app.models.article_sync import (
    SyncErrorCategory,
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
        timer: Callable[[], float] = time.perf_counter,
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
        self._timer = timer

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

        log_event(
            logger,
            logging.INFO,
            "article_sync_started",
            job_id=str(job.id),
            provider_id=job.provider_id,
            trigger_type=job.trigger_type.value,
            status=job.status.value,
        )

        checkpoint_from: datetime | None = None
        counters = {
            "retrieved": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "rejected": 0,
            "provider_attempts": 0,
            "provider_failures": 0,
            "provider_duration_ms": 0,
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
                    job_id=job_id,
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
                        log_event(
                            logger,
                            logging.WARNING,
                            "article_sync_item_rejected",
                            job_id=str(job_id),
                            provider_id=self.provider_id,
                            error_category=(SyncErrorCategory.ARTICLE_VALIDATION.value),
                            failed_stage="validation",
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
                error_category=(
                    SyncErrorCategory.ARTICLE_VALIDATION
                    if statistics.rejected
                    else None
                ),
                failed_stage=("validation" if statistics.rejected else None),
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
                    log_event(
                        logger,
                        logging.ERROR,
                        "article_sync_checkpoint_deferred",
                        job_id=str(job_id),
                        provider_id=self.provider_id,
                        error_category=SyncErrorCategory.DATABASE.value,
                        failed_stage="checkpoint",
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
        except ArticleSyncLeaseLostError:
            raise
        except Exception as exc:
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
        job_id: UUID,
    ) -> ProviderPage:
        attempts = 0
        while True:
            attempts += 1
            counters["provider_attempts"] += 1
            request_started = self._timer()
            try:
                page = await self._provider.fetch_articles(query)
                elapsed_ms = max(0, int((self._timer() - request_started) * 1000))
                counters["provider_duration_ms"] += elapsed_ms
                log_event(
                    logger,
                    logging.INFO,
                    "article_sync_provider_request_completed",
                    job_id=str(job_id),
                    provider_id=self.provider_id,
                    attempt=attempts,
                    duration_ms=elapsed_ms,
                )
                return page
            except ProviderError as exc:
                counters["provider_failures"] += 1
                elapsed_ms = max(0, int((self._timer() - request_started) * 1000))
                counters["provider_duration_ms"] += elapsed_ms
                category, stage = _classify_sync_error(exc)
                log_event(
                    logger,
                    logging.WARNING,
                    "article_sync_provider_request_failed",
                    job_id=str(job_id),
                    provider_id=self.provider_id,
                    attempt=attempts,
                    duration_ms=elapsed_ms,
                    error_code=exc.code.value,
                    error_category=category.value,
                    failed_stage=stage,
                )
                if not exc.retryable or attempts > self._max_retries:
                    raise
                delay = self._retry_base_seconds * (2 ** (attempts - 1))
                log_event(
                    logger,
                    logging.WARNING,
                    "article_sync_provider_retry",
                    job_id=str(job_id),
                    provider_id=self.provider_id,
                    error_code=exc.code.value,
                    error_category=category.value,
                    failed_stage=stage,
                    attempt=attempts,
                    delay_seconds=delay,
                )
                await self._sleeper(delay)
            except Exception:
                counters["provider_failures"] += 1
                elapsed_ms = max(0, int((self._timer() - request_started) * 1000))
                counters["provider_duration_ms"] += elapsed_ms
                log_event(
                    logger,
                    logging.ERROR,
                    "article_sync_provider_request_failed",
                    job_id=str(job_id),
                    provider_id=self.provider_id,
                    attempt=attempts,
                    duration_ms=elapsed_ms,
                    error_code="UNEXPECTED_PROVIDER_FAILURE",
                    error_category=SyncErrorCategory.INTERNAL_PIPELINE.value,
                    failed_stage="provider_request",
                )
                raise

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
        elif isinstance(error, ArticleSyncRepositoryError):
            code = "SYNC_PERSISTENCE_FAILED"
            summary = "Synchronisation persistence failed safely."
        else:
            code = "UNEXPECTED_SYNC_FAILURE"
            summary = "Synchronisation failed safely."
        error_category, failed_stage = _classify_sync_error(error)
        statistics = SyncStatistics(**counters)
        try:
            completed = await self._repository.finish_job(
                job_id=job_id,
                status=status,
                statistics=statistics,
                checkpoint_from=checkpoint_from,
                checkpoint_candidate=checkpoint_candidate,
                completed_at=self._now(),
                error_code=code,
                error_summary=summary,
                error_category=error_category,
                failed_stage=failed_stage,
            )
        except ArticleSyncRepositoryError:
            log_event(
                logger,
                logging.ERROR,
                "article_sync_failure_record_unavailable",
                job_id=str(job_id),
                provider_id=self.provider_id,
                status=status.value,
                error_code="SYNC_PERSISTENCE_FAILED",
                error_category=SyncErrorCategory.DATABASE.value,
                failed_stage="database",
                provider_duration_ms=statistics.provider_duration_ms,
                counts=_statistics_counts(statistics),
            )
            raise
        if completed is None:
            raise ArticleSyncLeaseLostError from error
        log_event(
            logger,
            logging.WARNING,
            (
                "article_sync_partially_completed"
                if status == SyncJobStatus.PARTIALLY_COMPLETED
                else "article_sync_failed"
            ),
            job_id=str(job_id),
            provider_id=self.provider_id,
            status=status.value,
            error_code=code,
            error_category=error_category.value,
            failed_stage=failed_stage,
            provider_duration_ms=statistics.provider_duration_ms,
            duration_ms=_job_duration_ms(completed),
            counts=_statistics_counts(statistics),
        )
        return completed

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("The synchronisation clock must include a timezone.")
        return value.astimezone(UTC)

    @staticmethod
    def _log_completion(job: SyncJobRecord) -> None:
        log_event(
            logger,
            (
                logging.WARNING
                if job.status == SyncJobStatus.PARTIALLY_COMPLETED
                else logging.INFO
            ),
            (
                "article_sync_partially_completed"
                if job.status == SyncJobStatus.PARTIALLY_COMPLETED
                else "article_sync_completed"
            ),
            job_id=str(job.id),
            provider_id=job.provider_id,
            trigger_type=job.trigger_type.value,
            status=job.status.value,
            duration_ms=_job_duration_ms(job),
            provider_duration_ms=job.statistics.provider_duration_ms,
            error_code=job.error_code,
            error_category=(
                job.error_category.value if job.error_category is not None else None
            ),
            failed_stage=job.failed_stage,
            counts=_statistics_counts(job.statistics),
        )


def _statistics_counts(statistics: SyncStatistics) -> dict[str, int]:
    return {
        "retrieved": statistics.retrieved,
        "created": statistics.created,
        "updated": statistics.updated,
        "skipped": statistics.skipped,
        "rejected": statistics.rejected,
        "provider_attempts": statistics.provider_attempts,
        "provider_failures": statistics.provider_failures,
    }


def _job_duration_ms(job: SyncJobRecord) -> int | None:
    if job.started_at is None or job.completed_at is None:
        return None
    return max(0, int((job.completed_at - job.started_at).total_seconds() * 1000))


def _classify_sync_error(error: Exception) -> tuple[SyncErrorCategory, str]:
    if isinstance(error, ProviderError):
        code = error.code.value.upper()
        if "TIMEOUT" in code:
            return SyncErrorCategory.PROVIDER_TIMEOUT, "provider_request"
        if "AUTH" in code and code != "SOURCE_NOT_AUTHORISED":
            return SyncErrorCategory.PROVIDER_AUTHENTICATION, "provider_request"
        if "RATE" in code:
            return SyncErrorCategory.PROVIDER_RATE_LIMIT, "provider_request"
        if code == "SOURCE_NOT_AUTHORISED":
            return SyncErrorCategory.SOURCE_AUTHORISATION, "authorisation"
        if code in {"PROVIDER_DATA_INVALID", "INVALID_PROVIDER_CURSOR"}:
            return SyncErrorCategory.ARTICLE_VALIDATION, "provider_validation"
        return SyncErrorCategory.PROVIDER_CONNECTION, "provider_request"
    if isinstance(error, ArticleRepositoryError | ArticleSyncRepositoryError):
        return SyncErrorCategory.DATABASE, "database"
    if isinstance(error, ArticleSyncPipelineError):
        if error.code in {"REPEATED_PROVIDER_CURSOR", "PROVIDER_ID_MISMATCH"}:
            return SyncErrorCategory.SYNCHRONISATION_CONFLICT, "synchronisation"
        return SyncErrorCategory.INTERNAL_PIPELINE, "pipeline"
    return SyncErrorCategory.INTERNAL_PIPELINE, "pipeline"


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
