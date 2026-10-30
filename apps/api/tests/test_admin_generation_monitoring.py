"""Administrator access tests for NFA-45 generation monitoring routes."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import require_authenticated_session
from app.api.routes.generation_monitoring import router
from app.core.errors import register_exception_handlers
from app.models.generation_audit import (
    GenerationAuditEvent,
    GenerationAuditEventType,
    GenerationAuditStatus,
    GenerationUsageSummary,
)
from app.repositories import AuthenticatedSession
from app.services.generation_monitoring import GenerationMonitoringService

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
ADMIN_ID = uuid4()
USER_ID = uuid4()
ARTICLE_ID = uuid4()
REQUEST_ID = uuid4()


class RouteRepository:
    def __init__(self) -> None:
        self.administrators = {ADMIN_ID}
        self.events = [
            GenerationAuditEvent(
                id=uuid4(),
                generation_request_id=REQUEST_ID,
                user_id=ADMIN_ID,
                article_id=ARTICLE_ID,
                event_type=GenerationAuditEventType.GENERATION_STARTED,
                status=GenerationAuditStatus.STARTED,
                occurred_at=NOW,
            )
        ]

    async def user_is_admin(self, user_id: UUID) -> bool:
        return user_id in self.administrators

    async def list_events(self, **values: object) -> list[GenerationAuditEvent]:
        limit = int(values["limit"])
        return self.events[:limit]

    async def list_events_since(self, **values: object) -> list[GenerationAuditEvent]:
        del values
        return self.events

    async def usage_summary(self, **values: object) -> GenerationUsageSummary:
        del values
        return GenerationUsageSummary(
            provider_attempts=0,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
        )


def _session(user_id: UUID) -> AuthenticatedSession:
    return AuthenticatedSession(
        user_id=user_id,
        email=f"{user_id}@example.invalid",
        csrf_token_hash=b"x" * 32,
        expires_at=NOW + timedelta(hours=1),
    )


def make_client(user_id: UUID) -> TestClient:
    repository = RouteRepository()
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router)
    application.state.article_sync_repository = repository
    application.state.generation_monitoring_service = GenerationMonitoringService(
        repository=repository,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )

    async def session_override() -> AuthenticatedSession:
        return _session(user_id)

    application.dependency_overrides[require_authenticated_session] = session_override
    return TestClient(application)


def test_administrator_can_read_audit_events_and_metrics() -> None:
    client = make_client(ADMIN_ID)

    audit = client.get("/api/admin/generations/audit?limit=10")
    metrics = client.get("/api/admin/generations/metrics?window_hours=24")

    assert audit.status_code == 200
    assert audit.json()["count"] == 1
    assert audit.json()["items"][0]["generation_request_id"] == str(REQUEST_ID)
    assert metrics.status_code == 200
    assert metrics.json()["total_requests"] == 1
    assert metrics.json()["active_requests"] == 1
    assert "user_id" not in metrics.json()


def test_ordinary_user_cannot_read_generation_operations() -> None:
    response = make_client(USER_ID).get("/api/admin/generations/audit")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "administrator_required"
