"""Cross-user object-level authorisation tests for private saved content."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from app.repositories import (
    AccountCredentials,
    AuthenticatedSession,
    RegisteredUser,
    SavedContent,
    SavedContentConflictError,
)
from app.security import Argon2PasswordHasher
from app.services import hash_session_token

USER_A_ID = UUID("20000000-0000-4000-8000-000000000001")
USER_B_ID = UUID("20000000-0000-4000-8000-000000000002")
USER_A_ITEM_ID = UUID("20000000-0000-4000-8000-000000000003")
USER_B_ITEM_ID = UUID("20000000-0000-4000-8000-000000000004")
USER_A_POST_ID = UUID("20000000-0000-4000-8000-000000000005")
USER_B_POST_ID = UUID("20000000-0000-4000-8000-000000000006")
USER_A_NEW_POST_ID = UUID("20000000-0000-4000-8000-000000000007")
USER_A_VERSION_ID = UUID("20000000-0000-4000-8000-000000000008")
USER_B_VERSION_ID = UUID("20000000-0000-4000-8000-000000000009")
USER_A_NEW_VERSION_ID = UUID("20000000-0000-4000-8000-000000000010")
USER_A_SESSION = "user-a-session-token"
USER_B_SESSION = "user-b-session-token"
USER_A_CSRF = "user-a-csrf-token"
USER_B_CSRF = "user-b-csrf-token"


class StubDatabase:
    async def check_connection(self) -> None:
        return None


class UnusedUserRepository:
    async def create_user(self, *, email: str, password_hash: str) -> RegisteredUser:
        del password_hash
        return RegisteredUser(id=uuid4(), email=email)


class InMemoryAuthenticationRepository:
    """Resolve two fixed active sessions for authorisation tests."""

    def __init__(self) -> None:
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        self.sessions = {
            hash_session_token(USER_A_SESSION): AuthenticatedSession(
                user_id=USER_A_ID,
                email="owner-a@example.com",
                csrf_token_hash=hash_session_token(USER_A_CSRF),
                expires_at=expires_at,
            ),
            hash_session_token(USER_B_SESSION): AuthenticatedSession(
                user_id=USER_B_ID,
                email="owner-b@example.com",
                csrf_token_hash=hash_session_token(USER_B_CSRF),
                expires_at=expires_at,
            ),
        }

    async def get_account_credentials(self, *, email: str) -> AccountCredentials | None:
        del email
        return None

    async def create_session(
        self,
        *,
        user_id: UUID,
        token_hash: bytes,
        csrf_token_hash: bytes,
        expires_at: datetime,
    ) -> None:
        self.sessions[token_hash] = AuthenticatedSession(
            user_id=user_id,
            email="new-session@example.com",
            csrf_token_hash=csrf_token_hash,
            expires_at=expires_at,
        )

    async def get_active_session(
        self, *, token_hash: bytes, checked_at: datetime
    ) -> AuthenticatedSession | None:
        session = self.sessions.get(token_hash)
        if session is None or session.expires_at <= checked_at:
            return None
        return session

    async def revoke_session(self, *, token_hash: bytes, revoked_at: datetime) -> bool:
        del revoked_at
        return self.sessions.pop(token_hash, None) is not None


class InMemorySavedContentRepository:
    """Model owner-scoped persistence without requiring PostgreSQL."""

    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.items = {
            USER_A_ITEM_ID: SavedContent(
                id=USER_A_ITEM_ID,
                owner_id=USER_A_ID,
                generated_post_id=USER_A_POST_ID,
                selected_post_version_id=USER_A_VERSION_ID,
                selected_image_id=None,
                library_title="Owner A draft",
                rendered_text="Private text belonging to owner A.",
                source_attribution="Synthetic source A",
                saved_at=now,
                updated_at=now,
            ),
            USER_B_ITEM_ID: SavedContent(
                id=USER_B_ITEM_ID,
                owner_id=USER_B_ID,
                generated_post_id=USER_B_POST_ID,
                selected_post_version_id=USER_B_VERSION_ID,
                selected_image_id=None,
                library_title="Owner B draft",
                rendered_text="Private text belonging to owner B.",
                source_attribution="Synthetic source B",
                saved_at=now,
                updated_at=now,
            ),
        }
        self.references = {
            USER_A_POST_ID: (USER_A_ID, USER_A_VERSION_ID),
            USER_B_POST_ID: (USER_B_ID, USER_B_VERSION_ID),
            USER_A_NEW_POST_ID: (USER_A_ID, USER_A_NEW_VERSION_ID),
        }

    async def list_for_owner(self, *, owner_id: UUID) -> list[SavedContent]:
        return [item for item in self.items.values() if item.owner_id == owner_id]

    async def get_for_owner(
        self, *, owner_id: UUID, item_id: UUID
    ) -> SavedContent | None:
        item = self.items.get(item_id)
        return item if item is not None and item.owner_id == owner_id else None

    async def create_for_owner(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        selected_post_version_id: UUID,
        selected_image_id: UUID | None,
        library_title: str | None,
    ) -> SavedContent | None:
        reference = self.references.get(generated_post_id)
        if reference != (owner_id, selected_post_version_id):
            return None
        if any(
            item.owner_id == owner_id and item.generated_post_id == generated_post_id
            for item in self.items.values()
        ):
            raise SavedContentConflictError("Already saved.")
        now = datetime.now(UTC)
        item = SavedContent(
            id=uuid4(),
            owner_id=owner_id,
            generated_post_id=generated_post_id,
            selected_post_version_id=selected_post_version_id,
            selected_image_id=selected_image_id,
            library_title=library_title,
            rendered_text="A newly saved private draft.",
            source_attribution="Synthetic source",
            saved_at=now,
            updated_at=now,
        )
        self.items[item.id] = item
        return item

    async def update_title_for_owner(
        self,
        *,
        owner_id: UUID,
        item_id: UUID,
        library_title: str | None,
    ) -> SavedContent | None:
        item = await self.get_for_owner(owner_id=owner_id, item_id=item_id)
        if item is None:
            return None
        updated = SavedContent(
            **{
                **item.__dict__,
                "library_title": library_title,
                "updated_at": datetime.now(UTC),
            }
        )
        self.items[item_id] = updated
        return updated

    async def delete_for_owner(self, *, owner_id: UUID, item_id: UUID) -> bool:
        item = await self.get_for_owner(owner_id=owner_id, item_id=item_id)
        if item is None:
            return False
        del self.items[item_id]
        return True


def make_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        database_url=SecretStr(
            "postgresql://test-user:test-password@localhost/test-newsflow"
        ),
    )


def set_user_session(client: TestClient, user: str) -> None:
    token = USER_A_SESSION if user == "a" else USER_B_SESSION
    client.cookies.set("newsflow_session", token)


def csrf_headers(user: str) -> dict[str, str]:
    token = USER_A_CSRF if user == "a" else USER_B_CSRF
    return {"X-CSRF-Token": token}


def application(repository: InMemorySavedContentRepository) -> Any:
    return create_app(
        settings=make_settings(),
        database=StubDatabase(),
        user_repository=UnusedUserRepository(),
        authentication_repository=InMemoryAuthenticationRepository(),
        saved_content_repository=repository,
        password_hasher=Argon2PasswordHasher(),
    )


@pytest.fixture
def authorization_context() -> Iterator[
    tuple[TestClient, InMemorySavedContentRepository]
]:
    repository = InMemorySavedContentRepository()
    with TestClient(application(repository)) as client:
        yield client, repository


def test_private_collection_requires_authentication_and_returns_only_owner_items(
    authorization_context: tuple[TestClient, InMemorySavedContentRepository],
) -> None:
    client, _ = authorization_context

    unauthenticated = client.get("/api/v1/library/items")
    set_user_session(client, "a")
    owner_a = client.get("/api/v1/library/items")

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "authentication_required"
    assert owner_a.status_code == 200
    assert [item["id"] for item in owner_a.json()["items"]] == [str(USER_A_ITEM_ID)]
    assert "owner_id" not in owner_a.text
    assert "Owner B draft" not in owner_a.text
    assert owner_a.headers["cache-control"] == "no-store"


def test_cross_user_read_modify_delete_and_export_share_the_same_safe_404(
    authorization_context: tuple[TestClient, InMemorySavedContentRepository],
) -> None:
    client, repository = authorization_context
    set_user_session(client, "b")
    expected = {
        "error": {
            "code": "private_resource_not_found",
            "message": "The requested resource was not found.",
        }
    }
    requests = (
        client.get(
            f"/api/v1/library/items/{USER_A_ITEM_ID}",
        ),
        client.patch(
            f"/api/v1/library/items/{USER_A_ITEM_ID}",
            json={"library_title": "Attempted takeover"},
            headers=csrf_headers("b"),
        ),
        client.delete(
            f"/api/v1/library/items/{USER_A_ITEM_ID}",
            headers=csrf_headers("b"),
        ),
        client.get(
            f"/api/v1/library/items/{USER_A_ITEM_ID}/export",
        ),
    )

    for response in requests:
        assert response.status_code == 404
        assert response.json() == expected
        assert "Owner A" not in response.text
        assert "Private text" not in response.text
    assert repository.items[USER_A_ITEM_ID].library_title == "Owner A draft"


def test_owner_can_read_update_export_and_delete_their_item(
    authorization_context: tuple[TestClient, InMemorySavedContentRepository],
) -> None:
    client, repository = authorization_context
    set_user_session(client, "a")
    item_url = f"/api/v1/library/items/{USER_A_ITEM_ID}"

    read = client.get(item_url)
    updated = client.patch(
        item_url,
        json={"library_title": "Reviewed draft"},
        headers=csrf_headers("a"),
    )
    exported = client.get(f"{item_url}/export")
    deleted = client.delete(
        item_url,
        headers=csrf_headers("a"),
    )

    assert read.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["library_title"] == "Reviewed draft"
    assert exported.status_code == 200
    assert "Private text belonging to owner A." in exported.text
    assert exported.headers["content-disposition"].endswith(
        f'newsflow-{USER_A_ITEM_ID}.txt"'
    )
    assert deleted.status_code == 204
    assert USER_A_ITEM_ID not in repository.items


def test_owner_is_session_derived_and_cross_user_references_are_rejected(
    authorization_context: tuple[TestClient, InMemorySavedContentRepository],
) -> None:
    client, repository = authorization_context
    set_user_session(client, "a")
    endpoint = "/api/v1/library/items"

    manipulated_owner = client.post(
        endpoint,
        json={
            "user_id": str(USER_B_ID),
            "generated_post_id": str(USER_A_NEW_POST_ID),
            "selected_post_version_id": str(USER_A_NEW_VERSION_ID),
        },
        headers=csrf_headers("a"),
    )
    cross_user_reference = client.post(
        endpoint,
        json={
            "generated_post_id": str(USER_B_POST_ID),
            "selected_post_version_id": str(USER_B_VERSION_ID),
        },
        headers=csrf_headers("a"),
    )
    own_reference = client.post(
        endpoint,
        json={
            "generated_post_id": str(USER_A_NEW_POST_ID),
            "selected_post_version_id": str(USER_A_NEW_VERSION_ID),
            "library_title": "  My new draft  ",
        },
        headers=csrf_headers("a"),
    )

    assert manipulated_owner.status_code == 422
    assert cross_user_reference.status_code == 404
    assert own_reference.status_code == 201
    assert own_reference.json()["library_title"] == "My new draft"
    assert "user_id" not in own_reference.text
    created_id = UUID(own_reference.json()["id"])
    assert repository.items[created_id].owner_id == USER_A_ID


def test_state_changes_require_session_specific_csrf_proof(
    authorization_context: tuple[TestClient, InMemorySavedContentRepository],
) -> None:
    client, repository = authorization_context
    set_user_session(client, "a")

    response = client.patch(
        f"/api/v1/library/items/{USER_A_ITEM_ID}",
        json={"library_title": "Must not change"},
    )
    wrong_session_token = client.patch(
        f"/api/v1/library/items/{USER_A_ITEM_ID}",
        json={"library_title": "Must still not change"},
        headers=csrf_headers("b"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_validation_failed"
    assert wrong_session_token.status_code == 403
    assert wrong_session_token.json()["error"]["code"] == "csrf_validation_failed"
    assert repository.items[USER_A_ITEM_ID].library_title == "Owner A draft"


def test_openapi_documents_owner_scoped_endpoints_and_cookie_security(
    authorization_context: tuple[TestClient, InMemorySavedContentRepository],
) -> None:
    client, _ = authorization_context

    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/api/v1/library/items" in paths
    assert "/api/v1/library/items/{item_id}" in paths
    assert "/api/v1/library/items/{item_id}/export" in paths
    assert paths["/api/v1/library/items"]["get"]["security"] == [{"SessionCookie": []}]
    assert paths["/api/v1/library/items"]["post"]["security"] == [{"SessionCookie": []}]
    request_schema = openapi["components"]["schemas"]["SaveContentRequest"]
    assert "user_id" not in request_schema["properties"]
