"""NFA-53 secure generated-image metadata, preview, and download tests."""

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.dependencies import require_authenticated_session
from app.api.routes.image_delivery import router
from app.core.errors import ApplicationError, register_exception_handlers
from app.models.generated_image import (
    ImageSafetyReviewStatus,
    StoredGeneratedImageRecord,
)
from app.repositories import AuthenticatedSession
from app.services import PrivateResourceNotFoundError
from app.services.image_delivery import (
    ImageContentUnavailableError,
    ImageDeliveryService,
)
from app.services.image_storage import (
    LocalPrivateImageStorage,
    PrivateImageObjectNotFoundError,
)

OWNER_ID = UUID("53000000-0000-4000-8000-000000000001")
OTHER_OWNER_ID = UUID("53000000-0000-4000-8000-000000000002")
IMAGE_ID = UUID("53000000-0000-4000-8000-000000000003")
MISSING_IMAGE_ID = UUID("53000000-0000-4000-8000-000000000004")
REQUEST_ID = UUID("53000000-0000-4000-8000-000000000005")
ARTICLE_ID = UUID("53000000-0000-4000-8000-000000000006")
SNAPSHOT_ID = UUID("53000000-0000-4000-8000-000000000007")
POST_ID = UUID("53000000-0000-4000-8000-000000000008")
RUN_ID = UUID("53000000-0000-4000-8000-000000000009")
PARENT_IMAGE_ID = UUID("53000000-0000-4000-8000-000000000010")
NOW = datetime(2026, 10, 31, 20, 0, tzinfo=UTC)
IMAGE_BYTES = b"synthetic-private-png-bytes"


def run(coroutine):
    return asyncio.run(coroutine)


def image_record(
    *,
    owner_id: UUID = OWNER_ID,
    storage_key: str = "generated-images/safe.png",
    content: bytes = IMAGE_BYTES,
) -> StoredGeneratedImageRecord:
    return StoredGeneratedImageRecord(
        id=IMAGE_ID,
        request_id=REQUEST_ID,
        owner_id=owner_id,
        article_id=ARTICLE_ID,
        article_snapshot_id=SNAPSHOT_ID,
        generated_post_id=POST_ID,
        source_post_version_id=None,
        generation_run_id=RUN_ID,
        parent_image_id=PARENT_IMAGE_ID,
        regeneration_sequence=2,
        storage_provider="local_private",
        storage_key=SecretStr(storage_key),
        mime_type="image/png",
        file_size_bytes=len(content),
        width=1536,
        height=1024,
        content_sha256=hashlib.sha256(content).hexdigest(),
        model_identifier="synthetic-image-model",
        prompt_version="image_prompt_v1",
        safety_policy_version="image_safety_v1",
        safety_status=ImageSafetyReviewStatus.APPROVED,
        created_at=NOW,
    )


class MemoryImages:
    def __init__(self, record: StoredGeneratedImageRecord | None = None) -> None:
        self.record = record if record is not None else image_record()
        self.requests: list[tuple[UUID, UUID]] = []

    async def get_for_owner(self, *, image_id: UUID, owner_id: UUID):
        self.requests.append((image_id, owner_id))
        if (
            self.record is not None
            and self.record.id == image_id
            and self.record.owner_id == owner_id
        ):
            return self.record
        return None


class MemoryStorage:
    def __init__(
        self,
        *,
        content: bytes = IMAGE_BYTES,
        failure: Exception | None = None,
    ) -> None:
        self.content = content
        self.failure = failure
        self.read_keys: list[str] = []

    async def read(self, storage_key: str) -> bytes:
        self.read_keys.append(storage_key)
        if self.failure is not None:
            raise self.failure
        return self.content

    async def put(self, data: bytes, *, file_extension: str):
        raise AssertionError("Image delivery cannot write objects.")

    async def delete(self, storage_key: str) -> None:
        raise AssertionError("Image delivery cannot delete objects.")


def selected_service(
    *,
    record: StoredGeneratedImageRecord | None = None,
    storage: MemoryStorage | LocalPrivateImageStorage | None = None,
) -> ImageDeliveryService:
    return ImageDeliveryService(
        images=MemoryImages(record),
        storage=storage or MemoryStorage(),
    )


def test_metadata_preserves_ai_designation_without_storage_internals() -> None:
    metadata = run(
        selected_service().get_metadata(owner_id=OWNER_ID, image_id=IMAGE_ID)
    )

    assert metadata.image_id == IMAGE_ID
    assert metadata.generation_id == RUN_ID
    assert metadata.parent_image_id == PARENT_IMAGE_ID
    assert metadata.regeneration_sequence == 2
    assert metadata.is_ai_generated is True
    assert metadata.ai_disclosure_required is True
    assert metadata.safety_status == ImageSafetyReviewStatus.APPROVED
    assert "storage_key" not in metadata.model_dump()
    assert "storage_provider" not in metadata.model_dump()
    assert "content_sha256" not in metadata.model_dump()


def test_service_delivers_only_owner_scoped_integrity_checked_content() -> None:
    storage = MemoryStorage()
    service = selected_service(storage=storage)

    delivered = run(service.get_content(owner_id=OWNER_ID, image_id=IMAGE_ID))

    assert delivered.content == IMAGE_BYTES
    assert delivered.metadata.mime_type == "image/png"
    assert delivered.download_filename == f"newsflow-ai-image-{IMAGE_ID}.png"
    assert storage.read_keys == ["generated-images/safe.png"]


def test_missing_and_differently_owned_records_share_private_not_found() -> None:
    service = selected_service()

    with pytest.raises(PrivateResourceNotFoundError):
        run(service.get_content(owner_id=OTHER_OWNER_ID, image_id=IMAGE_ID))
    with pytest.raises(PrivateResourceNotFoundError):
        run(service.get_content(owner_id=OWNER_ID, image_id=MISSING_IMAGE_ID))


def test_missing_storage_object_returns_controlled_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = selected_service(
        storage=MemoryStorage(
            failure=PrivateImageObjectNotFoundError("synthetic missing object")
        )
    )

    with pytest.raises(ImageContentUnavailableError):
        run(service.get_content(owner_id=OWNER_ID, image_id=IMAGE_ID))

    assert "generated_image_delivery_missing_object" in caplog.text
    assert "generated-images/safe.png" not in caplog.text


def test_modified_storage_object_fails_integrity_check() -> None:
    service = selected_service(storage=MemoryStorage(content=b"modified"))

    with pytest.raises(ImageContentUnavailableError):
        run(service.get_content(owner_id=OWNER_ID, image_id=IMAGE_ID))


def test_unsafe_database_storage_key_cannot_escape_private_root(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside.png"
    outside.write_bytes(IMAGE_BYTES)
    record = image_record(storage_key="../outside.png")
    service = selected_service(
        record=record,
        storage=LocalPrivateImageStorage(tmp_path / "private"),
    )

    with pytest.raises(ImageContentUnavailableError):
        run(service.get_content(owner_id=OWNER_ID, image_id=IMAGE_ID))

    assert outside.read_bytes() == IMAGE_BYTES


def api_client(
    *,
    authenticated: bool = True,
    owner_id: UUID = OWNER_ID,
    service: ImageDeliveryService | None = None,
) -> TestClient:
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router)
    application.state.image_delivery_service = service or selected_service()

    async def session_override():
        if not authenticated:
            raise ApplicationError(
                status_code=401,
                code="authentication_required",
                message="Authentication is required.",
            )
        return AuthenticatedSession(
            user_id=owner_id,
            email="nfa53@example.invalid",
            csrf_token_hash=b"x" * 32,
            expires_at=NOW + timedelta(hours=1),
        )

    application.dependency_overrides[require_authenticated_session] = session_override
    return TestClient(application)


def test_metadata_endpoint_requires_authentication_and_returns_safe_contract() -> None:
    denied = api_client(authenticated=False).get(f"/api/images/{IMAGE_ID}")
    response = api_client().get(f"/api/images/{IMAGE_ID}")

    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "authentication_required"
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store, max-age=0"
    assert response.headers["vary"] == "Cookie"
    assert response.json() == {
        "image_id": str(IMAGE_ID),
        "generation_id": str(RUN_ID),
        "generated_post_id": str(POST_ID),
        "article_id": str(ARTICLE_ID),
        "parent_image_id": str(PARENT_IMAGE_ID),
        "regeneration_sequence": 2,
        "mime_type": "image/png",
        "width": 1536,
        "height": 1024,
        "file_size_bytes": len(IMAGE_BYTES),
        "model_identifier": "synthetic-image-model",
        "prompt_version": "image_prompt_v1",
        "safety_policy_version": "image_safety_v1",
        "safety_status": "approved",
        "validation_status": "passed",
        "generation_status": "completed",
        "is_ai_generated": True,
        "ai_disclosure_required": True,
        "created_at": "2026-10-31T20:00:00Z",
    }
    assert "storage_key" not in response.text


def test_preview_endpoint_returns_private_content_headers() -> None:
    response = api_client().get(f"/api/images/{IMAGE_ID}/content")

    assert response.status_code == 200
    assert response.content == IMAGE_BYTES
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-length"] == str(len(IMAGE_BYTES))
    assert response.headers["cache-control"] == "private, no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"] == (
        f'inline; filename="newsflow-ai-image-{IMAGE_ID}.png"'
    )


def test_download_endpoint_uses_server_generated_safe_filename() -> None:
    response = api_client().get(f"/api/images/{IMAGE_ID}/download")

    assert response.status_code == 200
    assert response.content == IMAGE_BYTES
    assert response.headers["content-disposition"] == (
        f'attachment; filename="newsflow-ai-image-{IMAGE_ID}.png"'
    )
    assert "generated-images" not in response.headers["content-disposition"]


def test_foreign_and_missing_image_api_responses_are_indistinguishable() -> None:
    foreign = api_client(owner_id=OTHER_OWNER_ID).get(f"/api/images/{IMAGE_ID}/content")
    missing = api_client().get(f"/api/images/{MISSING_IMAGE_ID}/content")

    assert foreign.status_code == missing.status_code == 404
    assert (
        foreign.json()
        == missing.json()
        == {
            "error": {
                "code": "private_resource_not_found",
                "message": "The requested image was not found.",
            }
        }
    )


def test_missing_private_object_has_safe_api_error_without_internal_path() -> None:
    service = selected_service(
        storage=MemoryStorage(
            failure=PrivateImageObjectNotFoundError(
                "/private/secret/generated-images/missing.png"
            )
        )
    )
    response = api_client(service=service).get(f"/api/images/{IMAGE_ID}/download")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "image_delivery_unavailable",
            "message": "The image is temporarily unavailable.",
        }
    }
    assert "/private/secret" not in response.text


def test_openapi_documents_all_three_authenticated_delivery_endpoints() -> None:
    schema = api_client().get("/openapi.json").json()

    assert schema["paths"]["/api/images/{image_id}"]["get"]["security"]
    assert schema["paths"]["/api/images/{image_id}/content"]["get"]["security"]
    assert schema["paths"]["/api/images/{image_id}/download"]["get"]["security"]
    content = schema["paths"]["/api/images/{image_id}/content"]["get"]["responses"][
        "200"
    ]["content"]
    assert set(content) == {"image/png", "image/jpeg", "image/webp"}
