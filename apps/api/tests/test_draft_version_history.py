"""NFA-70 immutable saved-draft version-history API tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    require_authenticated_session,
    require_csrf_authenticated_session,
)
from app.api.routes.saved_drafts import router
from app.core.errors import register_exception_handlers
from app.repositories import AuthenticatedSession
from app.repositories.saved_drafts import (
    SavedDraft,
    SavedDraftVersion,
    SavedDraftVersionConflict,
    SavedDraftVersionPage,
)
from app.services.saved_drafts import SavedDraftService

OWNER_A = UUID("70000000-0000-4000-8000-000000000001")
OWNER_B = UUID("70000000-0000-4000-8000-000000000002")
DRAFT_ID = UUID("70000000-0000-4000-8000-000000000003")
POST_ID = UUID("70000000-0000-4000-8000-000000000004")
ARTICLE_ID = UUID("70000000-0000-4000-8000-000000000005")
GENERATION_ID = UUID("70000000-0000-4000-8000-000000000006")
VERSION_ONE_ID = UUID("70000000-0000-4000-8000-000000000007")
VERSION_TWO_ID = UUID("70000000-0000-4000-8000-000000000008")
POST_VERSION_ONE_ID = UUID("70000000-0000-4000-8000-000000000009")
POST_VERSION_TWO_ID = UUID("70000000-0000-4000-8000-000000000010")
NOW = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)


def _draft() -> SavedDraft:
    return SavedDraft(
        id=DRAFT_ID,
        owner_id=OWNER_A,
        generated_post_id=POST_ID,
        source_generation_id=GENERATION_ID,
        original_post_version_id=POST_VERSION_ONE_ID,
        current_post_version_id=POST_VERSION_TWO_ID,
        selected_image_id=None,
        selected_image=None,
        title="Synthetic history example",
        edited_text="A clearer current draft.\n\n#News #AI #Synthetic",
        tone="professional",
        length_option="medium",
        status="saved",
        version=2,
        article_id=ARTICLE_ID,
        source_title="Synthetic authorised source",
        source_url="https://example.invalid/nfa-70",
        source_attribution="Source: synthetic authorised fixture",
        model_identifier="synthetic-model",
        prompt_version="linkedin_post_v1",
        generation_created_at=NOW - timedelta(minutes=10),
        saved_at=NOW - timedelta(minutes=9),
        updated_at=NOW,
    )


def _history(
    *,
    version_id: UUID,
    post_version_id: UUID,
    version_number: int,
    change_type: str,
    edited_text: str,
    created_at: datetime,
    restored_from_version_id: UUID | None = None,
) -> SavedDraftVersion:
    return SavedDraftVersion(
        id=version_id,
        saved_draft_id=DRAFT_ID,
        owner_id=OWNER_A,
        generated_post_id=POST_ID,
        post_version_id=post_version_id,
        selected_image_id=None,
        selected_image=None,
        generation_run_id=GENERATION_ID if version_number == 1 else None,
        restored_from_version_id=restored_from_version_id,
        version_number=version_number,
        change_type=change_type,
        title="Synthetic history example",
        edited_text=edited_text,
        tone="professional",
        length_option="medium",
        article_id=ARTICLE_ID,
        source_title="Synthetic authorised source",
        source_url="https://example.invalid/nfa-70",
        source_attribution="Source: synthetic authorised fixture",
        created_at=created_at,
    )


class HistoryRepository:
    def __init__(self) -> None:
        self.draft = _draft()
        self.versions = [
            _history(
                version_id=VERSION_TWO_ID,
                post_version_id=POST_VERSION_TWO_ID,
                version_number=2,
                change_type="manual_edit",
                edited_text=self.draft.edited_text,
                created_at=NOW,
            ),
            _history(
                version_id=VERSION_ONE_ID,
                post_version_id=POST_VERSION_ONE_ID,
                version_number=1,
                change_type="initial_save",
                edited_text="The original AI draft.\n\n#News #AI #Synthetic",
                created_at=NOW - timedelta(minutes=9),
            ),
        ]

    async def list_versions_for_owner(
        self, *, owner_id: UUID, saved_draft_id: UUID, page: int, page_size: int
    ) -> SavedDraftVersionPage | None:
        if owner_id != OWNER_A or saved_draft_id != DRAFT_ID:
            return None
        offset = (page - 1) * page_size
        return SavedDraftVersionPage(
            items=self.versions[offset : offset + page_size],
            page=page,
            page_size=page_size,
            total_items=len(self.versions),
        )

    async def get_version_for_owner(
        self, *, owner_id: UUID, saved_draft_id: UUID, version_id: UUID
    ) -> SavedDraftVersion | None:
        if owner_id != OWNER_A or saved_draft_id != DRAFT_ID:
            return None
        return next((item for item in self.versions if item.id == version_id), None)

    async def restore_version_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        version_id: UUID,
        expected_version: int,
    ) -> SavedDraft | None:
        historical = await self.get_version_for_owner(
            owner_id=owner_id,
            saved_draft_id=saved_draft_id,
            version_id=version_id,
        )
        if historical is None:
            return None
        if expected_version != self.draft.version:
            raise SavedDraftVersionConflict("Stale version.")
        new_history_id = UUID("70000000-0000-4000-8000-000000000011")
        new_post_version_id = UUID("70000000-0000-4000-8000-000000000012")
        self.draft = replace(
            self.draft,
            current_post_version_id=new_post_version_id,
            edited_text=historical.edited_text,
            version=self.draft.version + 1,
            updated_at=NOW + timedelta(minutes=1),
        )
        self.versions.insert(
            0,
            _history(
                version_id=new_history_id,
                post_version_id=new_post_version_id,
                version_number=self.draft.version,
                change_type="version_restoration",
                edited_text=historical.edited_text,
                created_at=self.draft.updated_at,
                restored_from_version_id=historical.id,
            ),
        )
        return self.draft


def _client(repository: HistoryRepository, owner_id: UUID = OWNER_A) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.state.saved_draft_service = SavedDraftService(repository)  # type: ignore[arg-type]

    async def session_override() -> AuthenticatedSession:
        return AuthenticatedSession(
            user_id=owner_id,
            email="history@example.invalid",
            csrf_token_hash=b"x" * 32,
            expires_at=NOW + timedelta(hours=1),
        )

    app.dependency_overrides[require_authenticated_session] = session_override
    app.dependency_overrides[require_csrf_authenticated_session] = session_override
    return TestClient(app)


def test_history_is_newest_first_and_selected_version_is_retrievable() -> None:
    client = _client(HistoryRepository())

    collection = client.get(f"/api/v1/drafts/{DRAFT_ID}/versions")
    selected = client.get(f"/api/v1/drafts/{DRAFT_ID}/versions/{VERSION_ONE_ID}")

    assert collection.status_code == 200
    assert [item["version_number"] for item in collection.json()["items"]] == [2, 1]
    assert collection.json()["items"][0]["change_type"] == "manual_edit"
    assert selected.status_code == 200
    assert selected.json()["edited_text"].startswith("The original AI draft")
    assert selected.headers["cache-control"] == "private, no-store"


def test_other_owner_receives_the_same_private_not_found_response() -> None:
    client = _client(HistoryRepository(), owner_id=OWNER_B)

    response = client.get(f"/api/v1/drafts/{DRAFT_ID}/versions/{VERSION_ONE_ID}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "private_resource_not_found"


def test_history_has_no_direct_update_route() -> None:
    response = _client(HistoryRepository()).put(
        f"/api/v1/drafts/{DRAFT_ID}/versions/{VERSION_ONE_ID}",
        json={"edited_text": "Attempted rewrite"},
    )

    assert response.status_code == 405


def test_restore_appends_a_new_version_without_rewriting_history() -> None:
    repository = HistoryRepository()
    client = _client(repository)
    original_history = tuple(repository.versions)

    response = client.post(
        f"/api/v1/drafts/{DRAFT_ID}/versions/{VERSION_ONE_ID}/restore",
        json={"expected_version": 2},
    )

    assert response.status_code == 200
    assert response.json()["version"] == 3
    assert response.json()["edited_text"].startswith("The original AI draft")
    assert repository.versions[1:] == list(original_history)
    assert repository.versions[0].change_type == "version_restoration"
    assert repository.versions[0].restored_from_version_id == VERSION_ONE_ID


def test_restore_rejects_a_stale_current_version() -> None:
    response = _client(HistoryRepository()).post(
        f"/api/v1/drafts/{DRAFT_ID}/versions/{VERSION_ONE_ID}/restore",
        json={"expected_version": 1},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "draft_version_conflict"
