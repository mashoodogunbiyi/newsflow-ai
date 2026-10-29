"""Protected NFA-35 ingestion observability API tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import require_authenticated_session
from app.api.routes.ingestion_observability import router
from app.core.errors import register_exception_handlers
from app.models.article_sync import (
    SyncJobRecord,
    SyncJobStatus,
    SyncStatistics,
    SyncTriggerType,
)
from app.repositories import AuthenticatedSession
from app.services.ingestion_observability import IngestionObservabilityService

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
ADMIN_ID = uuid4()
USER_ID = uuid4()


class RouteRepository:
    def __init__(self, *, administrators: set[UUID]) -> None:
        self.administrators = administrators
        self.job = SyncJobRecord(
            id=uuid4(),
            provider_id="fixture",
            trigger_type=SyncTriggerType.MANUAL,
            status=SyncJobStatus.COMPLETED,
            started_at=NOW - timedelta(seconds=3),
            completed_at=NOW,
            statistics=SyncStatistics(
                retrieved=2,
                created=2,
                provider_attempts=1,
                provider_duration_ms=20,
            ),
            created_at=NOW - timedelta(seconds=3),
            updated_at=NOW,
        )

    async def user_is_admin(self, user_id: UUID) -> bool:
        return user_id in self.administrators

    async def get_job(self, job_id: UUID) -> SyncJobRecord | None:
        return self.job if job_id == self.job.id else None

    async def list_recent_jobs(
        self,
        *,
        limit: int,
        provider_id: str | None = None,
    ) -> list[SyncJobRecord]:
        if provider_id is not None and provider_id != self.job.provider_id:
            return []
        return [self.job][:limit]

    async def list_jobs_since(
        self,
        *,
        since: datetime,
        limit: int,
    ) -> list[SyncJobRecord]:
        return [self.job] if self.job.created_at >= since and limit else []


def _session(user_id: UUID) -> AuthenticatedSession:
    return AuthenticatedSession(
        user_id=user_id,
        email=f"{user_id}@example.invalid",
        csrf_token_hash=b"x" * 32,
        expires_at=NOW + timedelta(hours=1),
    )


def make_client(user_id: UUID) -> tuple[TestClient, RouteRepository]:
    repository = RouteRepository(administrators={ADMIN_ID})
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router)
    application.state.article_sync_repository = repository
    application.state.ingestion_observability_service = IngestionObservabilityService(
        repository=repository,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )

    async def session_override() -> AuthenticatedSession:
        return _session(user_id)

    application.dependency_overrides[require_authenticated_session] = session_override
    return TestClient(application), repository


def test_administrator_can_read_recent_jobs_detail_metrics_and_health() -> None:
    client, repository = make_client(ADMIN_ID)

    recent = client.get("/api/admin/sync/jobs?limit=10")
    detail = client.get(f"/api/admin/sync/jobs/{repository.job.id}")
    metrics = client.get("/api/admin/sync/metrics?window_hours=24")
    health = client.get("/api/admin/sync/health")

    assert recent.status_code == 200
    assert recent.json()["count"] == 1
    assert recent.json()["items"][0]["duration_ms"] == 3_000
    assert detail.status_code == 200
    assert detail.json()["provider_duration_ms"] == 20
    assert metrics.status_code == 200
    assert metrics.json()["total_jobs"] == 1
    assert metrics.json()["articles_created"] == 2
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"


def test_ordinary_user_cannot_read_ingestion_operations() -> None:
    client, _ = make_client(USER_ID)

    response = client.get("/api/admin/sync/jobs")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "administrator_required"


def test_unknown_job_returns_safe_not_found_error() -> None:
    client, _ = make_client(ADMIN_ID)

    response = client.get(f"/api/admin/sync/jobs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "article_sync_job_not_found"
