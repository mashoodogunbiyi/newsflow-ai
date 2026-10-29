"""Operational metrics and threshold-based health for article ingestion."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.article_sync import (
    SyncErrorCategory,
    SyncJobRecord,
    SyncJobResponse,
    SyncJobStatus,
)
from app.models.ingestion_observability import (
    IngestionHealthIndicator,
    IngestionHealthResponse,
    IngestionHealthStatus,
    IngestionMetricsResponse,
    SyncJobCollectionResponse,
)
from app.repositories.article_sync import ArticleSyncRepository
from app.services.article_sync import ArticleSyncJobNotFoundError


class IngestionObservabilityService:
    """Read existing sync records and derive safe operational signals."""

    def __init__(
        self,
        *,
        repository: ArticleSyncRepository,
        metrics_enabled: bool = True,
        metrics_window_hours: int = 24,
        failure_threshold: int = 3,
        success_stale_seconds: int = 21_600,
        long_running_seconds: int = 900,
        rejection_rate_percent: int = 25,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._metrics_enabled = metrics_enabled
        self._metrics_window_hours = metrics_window_hours
        self._failure_threshold = failure_threshold
        self._success_stale_seconds = success_stale_seconds
        self._long_running_seconds = long_running_seconds
        self._rejection_rate_percent = rejection_rate_percent
        self._clock = clock or (lambda: datetime.now(UTC))

    async def list_recent_jobs(
        self,
        *,
        limit: int,
        provider_id: str | None = None,
    ) -> SyncJobCollectionResponse:
        jobs = await self._repository.list_recent_jobs(
            limit=limit,
            provider_id=provider_id,
        )
        return SyncJobCollectionResponse(
            items=[SyncJobResponse.from_record(job) for job in jobs],
            count=len(jobs),
        )

    async def get_job(self, job_id: UUID) -> SyncJobResponse:
        job = await self._repository.get_job(job_id)
        if job is None:
            raise ArticleSyncJobNotFoundError
        return SyncJobResponse.from_record(job)

    async def metrics(
        self, *, window_hours: int | None = None
    ) -> IngestionMetricsResponse:
        now = self._now()
        hours = window_hours or self._metrics_window_hours
        window_start = now - timedelta(hours=hours)
        jobs = (
            await self._repository.list_jobs_since(since=window_start, limit=10_000)
            if self._metrics_enabled
            else []
        )
        durations = [
            duration for job in jobs if (duration := _duration_ms(job)) is not None
        ]
        provider_durations = [
            job.statistics.provider_duration_ms
            for job in jobs
            if job.statistics.provider_attempts > 0
        ]
        return IngestionMetricsResponse(
            enabled=self._metrics_enabled,
            window_start=window_start,
            window_end=now,
            total_jobs=len(jobs),
            completed_jobs=_status_count(jobs, SyncJobStatus.COMPLETED),
            failed_jobs=_status_count(jobs, SyncJobStatus.FAILED),
            partially_completed_jobs=_status_count(
                jobs, SyncJobStatus.PARTIALLY_COMPLETED
            ),
            interrupted_jobs=_status_count(jobs, SyncJobStatus.INTERRUPTED),
            active_jobs=sum(
                job.status in {SyncJobStatus.PENDING, SyncJobStatus.RUNNING}
                for job in jobs
            ),
            articles_retrieved=sum(job.statistics.retrieved for job in jobs),
            articles_created=sum(job.statistics.created for job in jobs),
            articles_updated=sum(job.statistics.updated for job in jobs),
            articles_skipped=sum(job.statistics.skipped for job in jobs),
            articles_rejected=sum(job.statistics.rejected for job in jobs),
            provider_attempts=sum(job.statistics.provider_attempts for job in jobs),
            provider_request_failures=sum(
                job.statistics.provider_failures for job in jobs
            ),
            database_failures=sum(
                job.error_category == SyncErrorCategory.DATABASE for job in jobs
            ),
            average_duration_ms=(
                round(sum(durations) / len(durations)) if durations else None
            ),
            average_provider_duration_ms=(
                round(sum(provider_durations) / len(provider_durations))
                if provider_durations
                else None
            ),
        )

    async def health(self) -> IngestionHealthResponse:
        now = self._now()
        jobs = await self._repository.list_recent_jobs(limit=500)
        terminal_jobs = [
            job
            for job in jobs
            if job.status
            in {
                SyncJobStatus.COMPLETED,
                SyncJobStatus.FAILED,
                SyncJobStatus.PARTIALLY_COMPLETED,
                SyncJobStatus.INTERRUPTED,
            }
        ]
        consecutive_failures = 0
        for job in terminal_jobs:
            if job.status == SyncJobStatus.COMPLETED:
                break
            consecutive_failures += 1
        successful_jobs = [
            job
            for job in jobs
            if job.status == SyncJobStatus.COMPLETED and job.completed_at is not None
        ]
        last_success = (
            max(job.completed_at for job in successful_jobs if job.completed_at)
            if successful_jobs
            else None
        )
        active_jobs = [
            job
            for job in jobs
            if job.status in {SyncJobStatus.PENDING, SyncJobStatus.RUNNING}
        ]
        indicators: list[IngestionHealthIndicator] = []

        if consecutive_failures >= self._failure_threshold:
            indicators.append(
                IngestionHealthIndicator(
                    code="repeated_failures",
                    status=IngestionHealthStatus.CRITICAL,
                    summary=(
                        "The ingestion failure threshold has been reached. "
                        "Review recent job error categories and stages."
                    ),
                )
            )
        if (
            last_success is None
            or (now - last_success).total_seconds() > self._success_stale_seconds
        ):
            indicators.append(
                IngestionHealthIndicator(
                    code="successful_sync_stale",
                    status=IngestionHealthStatus.WARNING,
                    summary="No successful ingestion has completed within the configured threshold.",
                )
            )
        if any(
            job.started_at is not None
            and (now - job.started_at).total_seconds() > self._long_running_seconds
            for job in active_jobs
        ):
            indicators.append(
                IngestionHealthIndicator(
                    code="long_running_job",
                    status=IngestionHealthStatus.WARNING,
                    summary="At least one ingestion job has exceeded the runtime threshold.",
                )
            )
        retrieved = sum(job.statistics.retrieved for job in terminal_jobs)
        rejected = sum(job.statistics.rejected for job in terminal_jobs)
        if retrieved and (rejected * 100 / retrieved) >= self._rejection_rate_percent:
            indicators.append(
                IngestionHealthIndicator(
                    code="high_rejection_rate",
                    status=IngestionHealthStatus.WARNING,
                    summary="The recent article rejection rate has reached the configured threshold.",
                )
            )
        if not indicators:
            indicators.append(
                IngestionHealthIndicator(
                    code="ingestion_operational",
                    status=IngestionHealthStatus.HEALTHY,
                    summary="Recent ingestion activity is within configured thresholds.",
                )
            )

        overall = (
            IngestionHealthStatus.CRITICAL
            if any(
                indicator.status == IngestionHealthStatus.CRITICAL
                for indicator in indicators
            )
            else (
                IngestionHealthStatus.WARNING
                if any(
                    indicator.status == IngestionHealthStatus.WARNING
                    for indicator in indicators
                )
                else IngestionHealthStatus.HEALTHY
            )
        )
        return IngestionHealthResponse(
            status=overall,
            checked_at=now,
            last_successful_sync_at=last_success,
            consecutive_failures=consecutive_failures,
            active_jobs=len(active_jobs),
            indicators=indicators,
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("The observability clock must include a timezone.")
        return value.astimezone(UTC)


def _duration_ms(job: SyncJobRecord) -> int | None:
    if job.started_at is None or job.completed_at is None:
        return None
    return max(0, int((job.completed_at - job.started_at).total_seconds() * 1000))


def _status_count(jobs: list[SyncJobRecord], status: SyncJobStatus) -> int:
    return sum(job.status == status for job in jobs)
