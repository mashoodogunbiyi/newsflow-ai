"""Full account, session, and private-resource security regression journey."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from tests.support.account_security import TEST_PASSWORD, AccountSecurityContext


def test_registration_login_and_authenticated_session_are_secure(
    account_security_context: AccountSecurityContext,
) -> None:
    context = account_security_context

    registration = context.register(email="  Owner.One@Example.com  ")
    login = context.login(email="owner.one@example.com")
    current_user = context.client.get("/api/v1/auth/me")

    assert registration.status_code == 201
    assert registration.json()["email"] == "owner.one@example.com"
    assert set(registration.json()) == {"id", "email", "message"}
    stored_account = context.repository.accounts_by_email["owner.one@example.com"]
    assert stored_account.password_hash != TEST_PASSWORD
    assert stored_account.password_hash.startswith("$argon2id$")
    assert context.password_hasher.verify(stored_account.password_hash, TEST_PASSWORD)

    assert login.status_code == 200
    assert current_user.status_code == 200
    assert current_user.json()["id"] == registration.json()["id"]
    assert len(context.repository.sessions) == 1
    assert all(len(token_hash) == 32 for token_hash in context.repository.sessions)
    combined_responses = registration.text + login.text + current_user.text
    assert TEST_PASSWORD not in combined_responses
    assert "password_hash" not in combined_responses
    assert "session_token" not in combined_responses


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("not-an-email", TEST_PASSWORD),
        ("weak@example.com", "weak-password"),
    ],
)
def test_invalid_registration_creates_no_account(
    account_security_context: AccountSecurityContext,
    email: str,
    password: str,
) -> None:
    response = account_security_context.register(email=email, password=password)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert account_security_context.repository.accounts_by_email == {}
    assert password not in response.text


def test_duplicate_and_failed_login_attempts_create_no_extra_session(
    account_security_context: AccountSecurityContext,
) -> None:
    context = account_security_context
    request_email = "security.user@example.com"
    assert context.register(email=request_email).status_code == 201

    duplicate = context.register(email=request_email)
    wrong_password = context.login(
        email=request_email,
        password="Incorrect-Synthetic-Password-7!",
    )
    unknown_account = context.login(email="unknown@example.com")

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_already_registered"
    expected_login_error = {
        "error": {
            "code": "invalid_credentials",
            "message": "Invalid email address or password.",
        }
    }
    assert wrong_password.status_code == 401
    assert unknown_account.status_code == 401
    assert wrong_password.json() == expected_login_error
    assert unknown_account.json() == expected_login_error
    assert context.repository.sessions == {}
    assert TEST_PASSWORD not in duplicate.text + unknown_account.text
    assert "password_hash" not in duplicate.text + unknown_account.text


def test_expired_and_logged_out_sessions_cannot_be_reused(
    account_security_context: AccountSecurityContext,
) -> None:
    context = account_security_context
    email = "session.user@example.com"
    assert context.register(email=email).status_code == 201
    assert context.login(email=email).status_code == 200
    expired_browser_session = context.capture_browser_session()
    stored_session = next(iter(context.repository.sessions.values()))
    stored_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)

    assert context.client.get("/api/v1/auth/me").status_code == 401

    context.clear_browser_session()
    assert context.login(email=email).status_code == 200
    active_browser_session = context.capture_browser_session()
    logout = context.client.post(
        "/api/v1/auth/logout",
        headers=context.csrf_headers(active_browser_session),
    )

    assert logout.status_code == 204
    assert context.client.get("/api/v1/auth/me").status_code == 401
    context.use_browser_session(active_browser_session)
    assert context.client.get("/api/v1/auth/me").status_code == 401
    context.use_browser_session(expired_browser_session)
    assert context.client.get("/api/v1/auth/me").status_code == 401


def test_private_content_is_owner_scoped_for_every_operation(
    account_security_context: AccountSecurityContext,
) -> None:
    context = account_security_context
    owner_a_email = "owner.a@example.com"
    owner_b_email = "owner.b@example.com"
    owner_a_registration = context.register(email=owner_a_email)
    owner_b_registration = context.register(email=owner_b_email)
    owner_a_id = UUID(owner_a_registration.json()["id"])
    owner_b_id = UUID(owner_b_registration.json()["id"])
    owner_a_post, owner_a_version = context.repository.add_owned_post(
        owner_id=owner_a_id
    )
    owner_b_post, owner_b_version = context.repository.add_owned_post(
        owner_id=owner_b_id
    )

    assert context.login(email=owner_a_email).status_code == 200
    owner_a_session = context.capture_browser_session()
    saved_a = context.client.post(
        "/api/v1/library/items",
        json={
            "generated_post_id": str(owner_a_post),
            "selected_post_version_id": str(owner_a_version),
            "library_title": "Owner A private draft",
        },
        headers=context.csrf_headers(owner_a_session),
    )
    item_a_id = saved_a.json()["id"]
    assert saved_a.status_code == 201

    owner_a_read = context.client.get(f"/api/v1/library/items/{item_a_id}")
    owner_a_update = context.client.patch(
        f"/api/v1/library/items/{item_a_id}",
        json={"library_title": "Owner A reviewed draft"},
        headers=context.csrf_headers(owner_a_session),
    )
    owner_a_export = context.client.get(f"/api/v1/library/items/{item_a_id}/export")
    owner_a_collection = context.client.get("/api/v1/library/items")
    assert owner_a_read.status_code == 200
    assert owner_a_update.status_code == 200
    assert owner_a_export.status_code == 200
    assert [item["id"] for item in owner_a_collection.json()["items"]] == [item_a_id]

    context.clear_browser_session()
    assert context.login(email=owner_b_email).status_code == 200
    owner_b_session = context.capture_browser_session()
    saved_b = context.client.post(
        "/api/v1/library/items",
        json={
            "generated_post_id": str(owner_b_post),
            "selected_post_version_id": str(owner_b_version),
            "library_title": "Owner B private draft",
        },
        headers=context.csrf_headers(owner_b_session),
    )
    assert saved_b.status_code == 201
    assert [
        item["id"]
        for item in context.client.get("/api/v1/library/items").json()["items"]
    ] == [saved_b.json()["id"]]

    expected_private_404 = {
        "error": {
            "code": "private_resource_not_found",
            "message": "The requested resource was not found.",
        }
    }
    cross_user_responses = (
        context.client.get(f"/api/v1/library/items/{item_a_id}"),
        context.client.patch(
            f"/api/v1/library/items/{item_a_id}",
            json={"library_title": "Attempted takeover"},
            headers=context.csrf_headers(owner_b_session),
        ),
        context.client.delete(
            f"/api/v1/library/items/{item_a_id}",
            headers=context.csrf_headers(owner_b_session),
        ),
        context.client.get(f"/api/v1/library/items/{item_a_id}/export"),
    )
    for response in cross_user_responses:
        assert response.status_code == 404
        assert response.json() == expected_private_404
        assert "Owner A" not in response.text

    context.use_browser_session(owner_a_session)
    ownership_override = context.client.post(
        "/api/v1/library/items",
        json={
            "user_id": str(owner_b_id),
            "generated_post_id": str(owner_b_post),
            "selected_post_version_id": str(owner_b_version),
        },
        headers=context.csrf_headers(owner_a_session),
    )
    cross_user_reference = context.client.post(
        "/api/v1/library/items",
        json={
            "generated_post_id": str(owner_b_post),
            "selected_post_version_id": str(owner_b_version),
        },
        headers=context.csrf_headers(owner_a_session),
    )
    assert ownership_override.status_code == 422
    assert cross_user_reference.status_code == 404
    assert context.repository.saved_items[UUID(item_a_id)].library_title == (
        "Owner A reviewed draft"
    )


def test_unauthenticated_requests_cannot_access_private_endpoints(
    account_security_context: AccountSecurityContext,
) -> None:
    context = account_security_context
    unknown_id = "30000000-0000-4000-8000-000000000001"
    context.clear_browser_session()

    list_response = context.client.get("/api/v1/library/items")
    read_response = context.client.get(f"/api/v1/library/items/{unknown_id}")

    assert list_response.status_code == 401
    assert read_response.status_code == 401
    assert list_response.json()["error"]["code"] == "authentication_required"
    assert read_response.json()["error"]["code"] == "authentication_required"
