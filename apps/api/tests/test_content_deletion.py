"""NFA-72 secure deletion, cleanup retry, retention, and API tests."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import require_csrf_authenticated_session
from app.api.routes.saved_drafts import router
from app.core.errors import ApplicationError, register_exception_handlers
from app.repositories import AuthenticatedSession
from app.repositories.content_deletion import (
    DeletionRequest,
    ImageCleanupTask,
)
from app.services.content_deletion import ContentDeletionService
from app.services.image_storage import PrivateImageStorageError

OWNER = UUID("72000000-0000-4000-8000-000000000001")
OTHER_OWNER = UUID("72000000-0000-4000-8000-000000000002")
DRAFT_ID = UUID("72000000-0000-4000-8000-000000000003")
IMAGE_ID = UUID("72000000-0000-4000-8000-000000000004")
JOB_ID = UUID("72000000-0000-4000-8000-000000000005")
NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


class FakeDeletionRepository:
    def __init__(self) -> None:
        self.owner_id = OWNER
        self.cleanup = [
            ImageCleanupTask(
                job_id=JOB_ID,
                image_id=IMAGE_ID,
                storage_key="generated-images/synthetic.png",
            )
        ]
        self.completed: list[UUID] = []
        self.retried: list[UUID] = []
        self.requested_at: datetime | None = None
        self.purge_after: datetime | None = None
        self.claimed: list[ImageCleanupTask] = []
        self.purged = 0

    async def request_for_owner(self, **values: object) -> DeletionRequest | None:
        owner_id = values["owner_id"]
        draft_id = values["draft_id"]
        if owner_id != self.owner_id or draft_id != DRAFT_ID:
            return None
        self.requested_at = values["requested_at"]  # type: ignore[assignment]
        self.purge_after = values["purge_after"]  # type: ignore[assignment]
        return DeletionRequest(draft_id=DRAFT_ID, cleanup_tasks=self.cleanup)

    async def complete_image_cleanup(self, **values: object) -> None:
        self.completed.append(values["job_id"])  # type: ignore[arg-type]

    async def retry_image_cleanup(self, **values: object) -> None:
        self.retried.append(values["job_id"])  # type: ignore[arg-type]

    async def claim_due_image_cleanup(self, **_: object) -> list[ImageCleanupTask]:
        return self.claimed

    async def purge_due_content(self, **_: object) -> int:
        return self.purged


class FakeStorage:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.deleted: list[str] = []

    async def delete(self, storage_key: str) -> None:
        if self.fail:
            raise PrivateImageStorageError("Synthetic object failure.")
        self.deleted.append(storage_key)


def service(
    repository: FakeDeletionRepository,
    storage: FakeStorage,
) -> ContentDeletionService:
    return ContentDeletionService(
        repository=repository,
        storage=storage,
        draft_retention=timedelta(days=30),
        audit_retention=timedelta(days=365),
        retry_delay=timedelta(minutes=5),
    )


def session(owner_id: UUID) -> AuthenticatedSession:
    return AuthenticatedSession(
        user_id=owner_id,
        email="deletion@example.invalid",
        csrf_token_hash=b"x" * 32,
        expires_at=NOW + timedelta(hours=1),
    )


def client(
    deletion_service: ContentDeletionService,
    *,
    owner_id: UUID = OWNER,
    authenticated: bool = True,
) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.state.content_deletion_service = deletion_service

    async def session_override() -> AuthenticatedSession:
        if not authenticated:
            raise ApplicationError(
                status_code=401,
                code="authentication_required",
                message="Authentication is required.",
            )
        return session(owner_id)

    app.dependency_overrides[require_csrf_authenticated_session] = session_override
    return TestClient(app)


def test_delete_immediately_queues_and_removes_unreferenced_image() -> None:
    repository = FakeDeletionRepository()
    storage = FakeStorage()
    response = client(service(repository, storage)).delete(f"/api/v1/drafts/{DRAFT_ID}")

    assert response.status_code == 204
    assert response.content == b""
    assert storage.deleted == ["generated-images/synthetic.png"]
    assert repository.completed == [JOB_ID]
    assert repository.retried == []
    assert repository.purge_after is not None
    assert repository.requested_at is not None
    assert repository.purge_after - repository.requested_at == timedelta(days=30)


def test_cross_owner_delete_is_indistinguishable_from_missing() -> None:
    repository = FakeDeletionRepository()
    response = client(service(repository, FakeStorage()), owner_id=OTHER_OWNER).delete(
        f"/api/v1/drafts/{DRAFT_ID}"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "private_resource_not_found"


def test_unauthenticated_delete_is_rejected() -> None:
    repository = FakeDeletionRepository()
    response = client(service(repository, FakeStorage()), authenticated=False).delete(
        f"/api/v1/drafts/{DRAFT_ID}"
    )

    assert response.status_code == 401
    assert repository.requested_at is None


def test_storage_failure_is_recorded_for_retry_without_restoring_access() -> None:
    repository = FakeDeletionRepository()
    response = client(service(repository, FakeStorage(fail=True))).delete(
        f"/api/v1/drafts/{DRAFT_ID}"
    )

    assert response.status_code == 204
    assert repository.retried == [JOB_ID]
    assert repository.requested_at is not None


def test_retention_worker_retries_objects_before_redacting_due_content() -> None:
    repository = FakeDeletionRepository()
    repository.claimed = repository.cleanup
    repository.purged = 1
    storage = FakeStorage()

    result = asyncio.run(service(repository, storage).run_retention())

    assert result.images_completed == 1
    assert result.images_retried == 0
    assert result.drafts_redacted == 1
    assert repository.completed == [JOB_ID]
