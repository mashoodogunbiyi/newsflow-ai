"""Protected NFA-33 manual synchronisation route tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    require_authenticated_session,
    require_csrf_authenticated_session,
)
from app.api.routes.article_sync import router
from app.core.errors import register_exception_handlers
from app.models.article_sync import (
    SyncJobRecord,
    SyncJobStatus,
    SyncStatistics,
    SyncTriggerType,
)
from app.repositories import AuthenticatedSession
from app.security import InMemoryRateLimiter

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
ADMIN_ID = uuid4()
USER_ID = uuid4()


class RouteSyncRepository:
    """Expose only the administrator lookup used by the route."""

    def __init__(self, admins: set[UUID]) -> None:
        self.admins = admins

    async def user_is_admin(self, user_id: UUID) -> bool:
        return user_id in self.admins


class RouteSyncService:
    """Record route calls without accessing a provider or database."""

    def __init__(self) -> None:
        self.jobs: dict[UUID, SyncJobRecord] = {}
        self.run_calls: list[UUID] = []

    async def start_job(
        self,
        *,
        trigger_type: SyncTriggerType,
        requested_by_user_id: UUID,
    ) -> SyncJobRecord:
        job = SyncJobRecord(
            id=uuid4(),
            provider_id="fixture",
            trigger_type=trigger_type,
            status=SyncJobStatus.PENDING,
            requested_by_user_id=requested_by_user_id,
            lease_expires_at=NOW + timedelta(minutes=5),
            created_at=NOW,
            updated_at=NOW,
        )
        self.jobs[job.id] = job
        return job

    async def run_job(self, job_id: UUID) -> SyncJobRecord:
        self.run_calls.append(job_id)
        completed = self.jobs[job_id].model_copy(
            update={
                "status": SyncJobStatus.COMPLETED,
                "started_at": NOW,
                "completed_at": NOW,
                "lease_expires_at": None,
                "statistics": SyncStatistics(),
            }
        )
        self.jobs[job_id] = completed
        return completed

    async def get_job(self, job_id: UUID) -> SyncJobRecord:
        return self.jobs[job_id]


def authenticated_session(user_id: UUID) -> AuthenticatedSession:
    return AuthenticatedSession(
        user_id=user_id,
        email=f"{user_id}@example.invalid",
        csrf_token_hash=b"x" * 32,
        expires_at=NOW + timedelta(hours=1),
    )


def make_client(
    *,
    user_id: UUID,
    admins: set[UUID],
    limiter: InMemoryRateLimiter | None = None,
) -> tuple[TestClient, RouteSyncService]:
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router)
    service = RouteSyncService()
    application.state.article_sync_service = service
    application.state.article_sync_repository = RouteSyncRepository(admins)
    application.state.manual_sync_rate_limiter = limiter or InMemoryRateLimiter(
        max_attempts=2,
        window_seconds=60,
    )

    async def session_override() -> AuthenticatedSession:
        return authenticated_session(user_id)

    application.dependency_overrides[require_csrf_authenticated_session] = (
        session_override
    )
    application.dependency_overrides[require_authenticated_session] = session_override
    return TestClient(application), service


def test_administrator_can_start_and_read_manual_job() -> None:
    client, service = make_client(user_id=ADMIN_ID, admins={ADMIN_ID})

    response = client.post("/api/v1/admin/articles/sync")

    assert response.status_code == 202
    job_id = UUID(response.json()["id"])
    assert response.json()["status"] == "pending"
    assert service.run_calls == [job_id]

    status_response = client.get(f"/api/v1/admin/articles/sync/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"


def test_ordinary_authenticated_user_cannot_start_manual_job() -> None:
    client, service = make_client(user_id=USER_ID, admins={ADMIN_ID})

    response = client.post("/api/v1/admin/articles/sync")

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "administrator_required",
            "message": "Administrator access is required.",
        }
    }
    assert service.jobs == {}


def test_manual_job_trigger_is_rate_limited() -> None:
    limiter = InMemoryRateLimiter(max_attempts=1, window_seconds=60)
    client, _ = make_client(
        user_id=ADMIN_ID,
        admins={ADMIN_ID},
        limiter=limiter,
    )

    assert client.post("/api/v1/admin/articles/sync").status_code == 202
    response = client.post("/api/v1/admin/articles/sync")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "article_sync_rate_limited"
    assert response.headers["retry-after"]
