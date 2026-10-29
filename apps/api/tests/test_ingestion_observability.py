"""NFA-35 structured logging, metrics, and health-indicator tests."""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from io import StringIO
from uuid import UUID, uuid4

from app.core.logging_config import StructuredJsonFormatter, log_event
from app.models.article_sync import (
    SyncErrorCategory,
    SyncJobRecord,
    SyncJobStatus,
    SyncStatistics,
    SyncTriggerType,
)
from app.models.ingestion_observability import IngestionHealthStatus
from app.services.ingestion_observability import IngestionObservabilityService

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


def run(coroutine):
    return asyncio.run(coroutine)


def job(
    *,
    status: SyncJobStatus,
    completed_minutes_ago: int = 5,
    error_category: SyncErrorCategory | None = None,
    retrieved: int = 3,
    rejected: int = 0,
) -> SyncJobRecord:
    started = NOW - timedelta(minutes=completed_minutes_ago, seconds=2)
    completed = (
        None
        if status in {SyncJobStatus.PENDING, SyncJobStatus.RUNNING}
        else NOW - timedelta(minutes=completed_minutes_ago)
    )
    return SyncJobRecord(
        id=uuid4(),
        provider_id="fixture",
        trigger_type=SyncTriggerType.SCHEDULED,
        status=status,
        started_at=started,
        completed_at=completed,
        lease_expires_at=(NOW + timedelta(minutes=5) if completed is None else None),
        statistics=SyncStatistics(
            retrieved=retrieved,
            created=max(0, retrieved - rejected),
            rejected=rejected,
            provider_attempts=2,
            provider_failures=(
                1
                if error_category
                in {
                    SyncErrorCategory.PROVIDER_CONNECTION,
                    SyncErrorCategory.PROVIDER_TIMEOUT,
                    SyncErrorCategory.PROVIDER_AUTHENTICATION,
                    SyncErrorCategory.PROVIDER_RATE_LIMIT,
                }
                else 0
            ),
            provider_duration_ms=40,
        ),
        error_code=("SYNTHETIC_FAILURE" if error_category else None),
        error_summary=("A safe synthetic failure." if error_category else None),
        error_category=error_category,
        failed_stage=("database" if error_category else None),
        created_at=started,
        updated_at=completed or started,
    )


class ObservabilityRepository:
    def __init__(self, jobs: list[SyncJobRecord]) -> None:
        self.jobs = jobs

    async def get_job(self, job_id: UUID) -> SyncJobRecord | None:
        return next((item for item in self.jobs if item.id == job_id), None)

    async def list_recent_jobs(
        self,
        *,
        limit: int,
        provider_id: str | None = None,
    ) -> list[SyncJobRecord]:
        matches = [
            item
            for item in self.jobs
            if provider_id is None or item.provider_id == provider_id
        ]
        return matches[:limit]

    async def list_jobs_since(
        self,
        *,
        since: datetime,
        limit: int,
    ) -> list[SyncJobRecord]:
        return [item for item in self.jobs if item.created_at >= since][:limit]


def test_metrics_aggregate_counts_durations_and_failure_categories() -> None:
    jobs = [
        job(status=SyncJobStatus.COMPLETED),
        job(
            status=SyncJobStatus.FAILED,
            error_category=SyncErrorCategory.PROVIDER_TIMEOUT,
        ),
        job(
            status=SyncJobStatus.PARTIALLY_COMPLETED,
            error_category=SyncErrorCategory.DATABASE,
            rejected=1,
        ),
    ]
    service = IngestionObservabilityService(
        repository=ObservabilityRepository(jobs),  # type: ignore[arg-type]
        clock=lambda: NOW,
    )

    metrics = run(service.metrics())

    assert metrics.total_jobs == 3
    assert metrics.completed_jobs == 1
    assert metrics.failed_jobs == 1
    assert metrics.partially_completed_jobs == 1
    assert metrics.articles_retrieved == 9
    assert metrics.articles_rejected == 1
    assert metrics.provider_request_failures == 1
    assert metrics.database_failures == 1
    assert metrics.average_duration_ms == 2_000
    assert metrics.average_provider_duration_ms == 40


def test_health_reports_repeated_failures_and_stale_success() -> None:
    jobs = [
        job(
            status=SyncJobStatus.FAILED,
            completed_minutes_ago=1,
            error_category=SyncErrorCategory.PROVIDER_CONNECTION,
        ),
        job(
            status=SyncJobStatus.FAILED,
            completed_minutes_ago=2,
            error_category=SyncErrorCategory.DATABASE,
        ),
        job(
            status=SyncJobStatus.FAILED,
            completed_minutes_ago=3,
            error_category=SyncErrorCategory.PROVIDER_TIMEOUT,
        ),
        job(status=SyncJobStatus.COMPLETED, completed_minutes_ago=400),
    ]
    service = IngestionObservabilityService(
        repository=ObservabilityRepository(jobs),  # type: ignore[arg-type]
        failure_threshold=3,
        success_stale_seconds=3600,
        clock=lambda: NOW,
    )

    health = run(service.health())

    assert health.status == IngestionHealthStatus.CRITICAL
    assert health.consecutive_failures == 3
    assert {indicator.code for indicator in health.indicators} >= {
        "repeated_failures",
        "successful_sync_stale",
    }


def test_json_logging_keeps_safe_fields_and_redacts_credentials() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredJsonFormatter())
    test_logger = logging.getLogger("test.ingestion.logging")
    test_logger.handlers = [handler]
    test_logger.propagate = False
    test_logger.setLevel(logging.INFO)

    log_event(
        test_logger,
        logging.INFO,
        "article_sync_completed",
        job_id="job-123",
        provider_id="fixture",
        status="completed",
        counts={"retrieved": 3, "created": 3},
        password="must-not-appear",
    )
    test_logger.info(
        "connection postgresql://admin:real-password@database/newsflow "
        "api_key=sk-supersecret123"
    )

    lines = stream.getvalue().splitlines()
    event = json.loads(lines[0])
    assert event["event"] == "article_sync_completed"
    assert event["job_id"] == "job-123"
    assert event["counts"] == {"retrieved": 3, "created": 3}
    assert "password" not in event
    assert "real-password" not in lines[1]
    assert "sk-supersecret123" not in lines[1]
    assert "[REDACTED]" in lines[1]
