"""NFA-67 and NFA-68 saved-draft persistence and REST API tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    require_authenticated_session,
    require_csrf_authenticated_session,
)
from app.api.routes.saved_drafts import router
from app.core.errors import ApplicationError, register_exception_handlers
from app.repositories import AuthenticatedSession
from app.repositories.saved_drafts import (
    SavedDraft,
    SavedDraftDuplicateError,
    SavedDraftIdempotencyConflict,
    SavedDraftImage,
    SavedDraftPage,
    SavedDraftRepositoryError,
    SavedDraftVersionConflict,
)
from app.services.saved_drafts import SavedDraftService

OWNER_A = UUID("67000000-0000-4000-8000-000000000001")
OWNER_B = UUID("67000000-0000-4000-8000-000000000002")
GENERATION_ID = UUID("67000000-0000-4000-8000-000000000003")
POST_ID = UUID("67000000-0000-4000-8000-000000000004")
ORIGINAL_VERSION_ID = UUID("67000000-0000-4000-8000-000000000005")
IMAGE_ID = UUID("67000000-0000-4000-8000-000000000006")
OTHER_IMAGE_ID = UUID("67000000-0000-4000-8000-000000000007")
ARTICLE_ID = UUID("67000000-0000-4000-8000-000000000008")
NOW = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)


class InMemorySavedDraftRepository:
    """Faithfully model the repository contract without PostgreSQL."""

    def __init__(self) -> None:
        self.items: dict[UUID, SavedDraft] = {}
        self.save_keys: dict[tuple[UUID, str], tuple[str, UUID]] = {}
        self.fail_next = False

    async def get_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
    ) -> SavedDraft | None:
        self._maybe_fail()
        item = self.items.get(saved_draft_id)
        return item if item is not None and item.owner_id == owner_id else None

    async def list_for_owner(
        self,
        *,
        owner_id: UUID,
        page: int,
        page_size: int,
    ) -> SavedDraftPage:
        self._maybe_fail()
        owned = sorted(
            (item for item in self.items.values() if item.owner_id == owner_id),
            key=lambda item: (item.updated_at, item.id),
            reverse=True,
        )
        offset = (page - 1) * page_size
        return SavedDraftPage(
            items=owned[offset : offset + page_size],
            page=page,
            page_size=page_size,
            total_items=len(owned),
        )

    async def create_for_owner(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        title: str | None,
        edited_text: str,
        selected_image_id: UUID | None,
        save_key_hash: str,
        payload_hash: str,
    ) -> SavedDraft | None:
        self._maybe_fail()
        key = (owner_id, save_key_hash)
        existing_key = self.save_keys.get(key)
        if existing_key is not None:
            existing_payload, item_id = existing_key
            if existing_payload != payload_hash:
                raise SavedDraftIdempotencyConflict("Key reused.")
            return self.items[item_id]
        if owner_id != OWNER_A or generation_id != GENERATION_ID:
            return None
        if selected_image_id not in {None, IMAGE_ID}:
            return None
        if any(
            item.owner_id == owner_id and item.generated_post_id == POST_ID
            for item in self.items.values()
        ):
            raise SavedDraftDuplicateError("Already saved.")

        saved_at = NOW
        selected_image = (
            SavedDraftImage(
                id=IMAGE_ID,
                alt_text="Synthetic AI-generated chart illustration",
                mime_type="image/png",
                width_px=1536,
                height_px=1024,
                ai_generated=True,
                ai_disclosure_required=True,
            )
            if selected_image_id == IMAGE_ID
            else None
        )
        item = SavedDraft(
            id=uuid4(),
            owner_id=owner_id,
            generated_post_id=POST_ID,
            source_generation_id=GENERATION_ID,
            original_post_version_id=ORIGINAL_VERSION_ID,
            current_post_version_id=uuid4(),
            selected_image_id=selected_image_id,
            selected_image=selected_image,
            title=title,
            edited_text=edited_text,
            tone="professional",
            length_option="medium",
            status="saved",
            version=1,
            article_id=ARTICLE_ID,
            source_title="Synthetic authorised article",
            source_url="https://example.invalid/newsflow/nfa-67",
            source_attribution="Source: synthetic authorised fixture",
            model_identifier="synthetic-model",
            prompt_version="linkedin_post_v1",
            generation_created_at=NOW - timedelta(minutes=5),
            saved_at=saved_at,
            updated_at=saved_at,
        )
        self.items[item.id] = item
        self.save_keys[key] = (payload_hash, item.id)
        return item

    async def update_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        expected_version: int,
        title: str | None,
        edited_text: str,
        selected_image_id: UUID | None,
    ) -> SavedDraft | None:
        self._maybe_fail()
        item = self.items.get(saved_draft_id)
        if item is None or item.owner_id != owner_id:
            return None
        if selected_image_id not in {None, IMAGE_ID}:
            return None
        if item.version != expected_version:
            raise SavedDraftVersionConflict("Stale version.")
        if (
            item.title == title
            and item.edited_text == edited_text
            and item.selected_image_id == selected_image_id
        ):
            return item
        updated = replace(
            item,
            current_post_version_id=(
                uuid4()
                if item.edited_text != edited_text
                else item.current_post_version_id
            ),
            selected_image_id=selected_image_id,
            selected_image=(
                SavedDraftImage(
                    id=IMAGE_ID,
                    alt_text="Synthetic AI-generated chart illustration",
                    mime_type="image/png",
                    width_px=1536,
                    height_px=1024,
                    ai_generated=True,
                    ai_disclosure_required=True,
                )
                if selected_image_id == IMAGE_ID
                else None
            ),
            title=title,
            edited_text=edited_text,
            version=item.version + 1,
            updated_at=item.updated_at + timedelta(minutes=1),
        )
        self.items[item.id] = updated
        return updated

    def _maybe_fail(self) -> None:
        if self.fail_next:
            self.fail_next = False
            raise SavedDraftRepositoryError("Synthetic database failure.")


def _session(owner_id: UUID) -> AuthenticatedSession:
    return AuthenticatedSession(
        user_id=owner_id,
        email="saved-drafts@example.invalid",
        csrf_token_hash=b"x" * 32,
        expires_at=NOW + timedelta(hours=1),
    )


def _client(
    repository: InMemorySavedDraftRepository,
    *,
    owner_id: UUID = OWNER_A,
    authenticated: bool = True,
) -> TestClient:
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router)
    application.state.saved_draft_service = SavedDraftService(repository)

    async def session_override() -> AuthenticatedSession:
        if not authenticated:
            raise ApplicationError(
                status_code=401,
                code="authentication_required",
                message="Authentication is required.",
            )
        return _session(owner_id)

    application.dependency_overrides[require_authenticated_session] = session_override
    application.dependency_overrides[require_csrf_authenticated_session] = (
        session_override
    )
    return TestClient(application)


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "generation_id": str(GENERATION_ID),
        "title": "Quarterly briefing",
        "edited_text": "A reviewed LinkedIn draft.\n\n#Synthetic #News #AI",
        "selected_image_id": str(IMAGE_ID),
    }
    payload.update(overrides)
    return payload


def _create(
    client: TestClient,
    *,
    key: str = "nfa67-save-001",
    payload: dict[str, object] | None = None,
):
    return client.post(
        "/api/v1/drafts",
        headers={"Idempotency-Key": key},
        json=payload or _payload(),
    )


def test_create_requires_authentication_and_valid_bounded_text() -> None:
    repository = InMemorySavedDraftRepository()
    denied = _create(_client(repository, authenticated=False))
    invalid = _create(
        _client(repository),
        key="nfa67-save-invalid",
        payload=_payload(edited_text="   "),
    )
    oversized = _create(
        _client(repository),
        key="nfa67-save-oversized",
        payload=_payload(edited_text="x" * 12_001),
    )

    assert denied.status_code == 401
    assert invalid.status_code == 422
    assert oversized.status_code == 422
    assert repository.items == {}


def test_create_preserves_source_generation_image_and_private_response() -> None:
    repository = InMemorySavedDraftRepository()
    response = _create(_client(repository))

    assert response.status_code == 201
    assert response.headers["cache-control"] == "private, no-store"
    body = response.json()
    assert body["edited_text"] == _payload()["edited_text"]
    assert body["selected_image_id"] == str(IMAGE_ID)
    assert body["selected_image"] == {
        "id": str(IMAGE_ID),
        "alt_text": "Synthetic AI-generated chart illustration",
        "mime_type": "image/png",
        "width_px": 1536,
        "height_px": 1024,
        "ai_generated": True,
        "ai_disclosure_required": True,
    }
    assert body["source"]["article_id"] == str(ARTICLE_ID)
    assert body["generation"]["generation_id"] == str(GENERATION_ID)
    assert body["generation"]["original_post_version_id"] == str(ORIGINAL_VERSION_ID)
    assert body["version"] == 1
    assert body["created_at"] == body["updated_at"]
    assert "owner_id" not in body
    assert "save_key_hash" not in body
    assert "save_payload_hash" not in body
    assert "storage_key" not in response.text


def test_create_is_idempotent_but_rejects_key_reuse_and_duplicate_save() -> None:
    repository = InMemorySavedDraftRepository()
    client = _client(repository)

    first = _create(client)
    replay = _create(client)
    reused = _create(client, payload=_payload(title="Different title"))
    duplicate = _create(client, key="nfa67-save-002")

    assert replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]
    assert len(repository.items) == 1
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "idempotency_key_conflict"
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "draft_already_saved"


def test_update_appends_text_version_and_rejects_stale_or_cross_owner_access() -> None:
    repository = InMemorySavedDraftRepository()
    owner_client = _client(repository)
    created = _create(owner_client).json()
    item_id = created["id"]
    original_version = created["generation"]["original_post_version_id"]

    updated = owner_client.put(
        f"/api/v1/drafts/{item_id}",
        json={
            "expected_version": 1,
            "title": "Reviewed title",
            "edited_text": "A second human-reviewed draft.\n\n#Synthetic #News #AI",
            "selected_image_id": None,
        },
    )
    no_change = owner_client.put(
        f"/api/v1/drafts/{item_id}",
        json={
            "expected_version": 2,
            "title": "Reviewed title",
            "edited_text": "A second human-reviewed draft.\n\n#Synthetic #News #AI",
            "selected_image_id": None,
        },
    )
    stale = owner_client.put(
        f"/api/v1/drafts/{item_id}",
        json={
            "expected_version": 1,
            "title": "Stale edit",
            "edited_text": "This edit must not overwrite newer work.",
            "selected_image_id": None,
        },
    )
    other_owner_client = _client(repository, owner_id=OWNER_B)
    other_owner = other_owner_client.get(f"/api/v1/drafts/{item_id}")
    other_owner_update = other_owner_client.put(
        f"/api/v1/drafts/{item_id}",
        json={
            "expected_version": 2,
            "title": "Cross-user overwrite",
            "edited_text": "This update must never reach another user's draft.",
            "selected_image_id": None,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert (
        updated.json()["current_post_version_id"] != created["current_post_version_id"]
    )
    assert updated.json()["generation"]["original_post_version_id"] == (
        original_version
    )
    assert no_change.status_code == 200
    assert no_change.json()["version"] == 2
    assert (
        no_change.json()["current_post_version_id"]
        == updated.json()["current_post_version_id"]
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "draft_version_conflict"
    assert repository.items[UUID(item_id)].title == "Reviewed title"
    assert other_owner.status_code == 404
    assert other_owner.json()["error"]["code"] == "private_resource_not_found"
    assert other_owner_update.status_code == 404
    assert repository.items[UUID(item_id)].title == "Reviewed title"


def test_invalid_image_and_database_failure_leave_existing_content_unchanged() -> None:
    repository = InMemorySavedDraftRepository()
    client = _client(repository)

    invalid_image = _create(
        client,
        key="nfa67-save-image",
        payload=_payload(selected_image_id=str(OTHER_IMAGE_ID)),
    )
    created = _create(client, key="nfa67-save-valid")
    repository.fail_next = True
    unavailable = client.put(
        f"/api/v1/drafts/{created.json()['id']}",
        json={
            "expected_version": 1,
            "title": "Must not persist",
            "edited_text": "A failed update must not replace the saved draft.",
            "selected_image_id": None,
        },
    )

    assert invalid_image.status_code == 404
    assert created.status_code == 201
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == ("draft_persistence_unavailable")
    stored = repository.items[UUID(created.json()["id"])]
    assert stored.title == "Quarterly briefing"
    assert stored.version == 1


def test_list_returns_only_owner_page_in_stable_newest_first_order() -> None:
    repository = InMemorySavedDraftRepository()
    owner_client = _client(repository)
    created_response = _create(owner_client)
    created = repository.items[UUID(created_response.json()["id"])]

    owner_items = [
        replace(
            created,
            id=uuid4(),
            generated_post_id=uuid4(),
            title=f"Owner draft {minute}",
            selected_image_id=None,
            selected_image=None,
            updated_at=NOW + timedelta(minutes=minute),
        )
        for minute in (1, 2, 3)
    ]
    foreign = replace(
        created,
        id=uuid4(),
        owner_id=OWNER_B,
        generated_post_id=uuid4(),
        title="Another user's private draft",
        updated_at=NOW + timedelta(minutes=4),
    )
    for item in [*owner_items, foreign]:
        repository.items[item.id] = item

    first_page = owner_client.get("/api/v1/drafts?page=1&page_size=2")
    second_page = owner_client.get("/api/v1/drafts?page=2&page_size=2")

    assert first_page.status_code == 200
    assert first_page.headers["cache-control"] == "private, no-store"
    assert [item["title"] for item in first_page.json()["items"]] == [
        "Owner draft 3",
        "Owner draft 2",
    ]
    assert first_page.json() | {"items": []} == {
        "items": [],
        "page": 1,
        "page_size": 2,
        "total_items": 4,
        "total_pages": 2,
        "sort": "updated_at_desc",
    }
    assert [item["title"] for item in second_page.json()["items"]] == [
        "Owner draft 1",
        "Quarterly briefing",
    ]
    assert "Another user's private draft" not in first_page.text + second_page.text
    assert "storage_key" not in first_page.text + second_page.text


def test_list_requires_authentication_and_valid_bounded_pagination() -> None:
    repository = InMemorySavedDraftRepository()
    denied = _client(repository, authenticated=False).get("/api/v1/drafts")
    client = _client(repository)
    bad_page = client.get("/api/v1/drafts?page=0")
    bad_size = client.get("/api/v1/drafts?page_size=101")
    bad_identifier = client.get("/api/v1/drafts/not-a-uuid")
    repository.fail_next = True
    unavailable = client.get("/api/v1/drafts")

    assert denied.status_code == 401
    assert bad_page.status_code == 422
    assert bad_size.status_code == 422
    assert bad_identifier.status_code == 422
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "draft_persistence_unavailable"


def test_patch_updates_only_supplied_fields_and_enforces_conflicts_and_ownership() -> (
    None
):
    repository = InMemorySavedDraftRepository()
    owner_client = _client(repository)
    created = _create(owner_client).json()
    item_id = created["id"]

    patched = owner_client.patch(
        f"/api/v1/drafts/{item_id}",
        json={"expected_version": 1, "title": "Library title only"},
    )
    stale = owner_client.patch(
        f"/api/v1/drafts/{item_id}",
        json={"expected_version": 1, "title": "Stale overwrite"},
    )
    no_change_fields = owner_client.patch(
        f"/api/v1/drafts/{item_id}",
        json={"expected_version": 2},
    )
    null_text = owner_client.patch(
        f"/api/v1/drafts/{item_id}",
        json={"expected_version": 2, "edited_text": None},
    )
    foreign = _client(repository, owner_id=OWNER_B).patch(
        f"/api/v1/drafts/{item_id}",
        json={"expected_version": 2, "title": "Cross-user overwrite"},
    )

    assert patched.status_code == 200
    assert patched.headers["cache-control"] == "private, no-store"
    assert patched.json()["title"] == "Library title only"
    assert patched.json()["edited_text"] == created["edited_text"]
    assert patched.json()["selected_image_id"] == created["selected_image_id"]
    assert (
        patched.json()["current_post_version_id"] == created["current_post_version_id"]
    )
    assert patched.json()["version"] == 2
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "draft_version_conflict"
    assert no_change_fields.status_code == 422
    assert null_text.status_code == 422
    assert foreign.status_code == 404
    assert repository.items[UUID(item_id)].title == "Library title only"


def test_openapi_documents_collection_create_retrieve_and_update_contracts() -> None:
    schema = _client(InMemorySavedDraftRepository()).get("/openapi.json")

    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert {"get", "post"} <= set(paths["/api/v1/drafts"])
    assert {"get", "put", "patch"} <= set(paths["/api/v1/drafts/{saved_draft_id}"])
    assert "storage_key" not in schema.text
