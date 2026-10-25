"""Login, session, current-user, logout, and CSRF endpoint tests."""

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
    AuthenticationRepositoryError,
    RegisteredUser,
)
from app.security import Argon2PasswordHasher, InMemoryRateLimiter

VALID_EMAIL = "member@example.com"
VALID_PASSWORD = "Correct-Horse-Battery-9!"


class StubDatabase:
    """Satisfy application startup without a live PostgreSQL service."""

    async def check_connection(self) -> None:
        return None


class UnusedUserRepository:
    """Provide the registration boundary without using it in login tests."""

    async def create_user(self, *, email: str, password_hash: str) -> RegisteredUser:
        del password_hash
        return RegisteredUser(id=uuid4(), email=email)


class InMemoryAuthenticationRepository:
    """Exercise authentication behaviour while retaining server-side state."""

    def __init__(self, password_hash: str, *, status: str = "active") -> None:
        self.user_id = uuid4()
        self.account = AccountCredentials(
            id=self.user_id,
            email=VALID_EMAIL,
            password_hash=password_hash,
            status=status,
        )
        self.sessions: dict[bytes, dict[str, Any]] = {}

    async def get_account_credentials(
        self,
        *,
        email: str,
    ) -> AccountCredentials | None:
        if email == self.account.email:
            return self.account
        return None

    async def create_session(
        self,
        *,
        user_id: UUID,
        token_hash: bytes,
        csrf_token_hash: bytes,
        expires_at: datetime,
    ) -> None:
        self.sessions[token_hash] = {
            "user_id": user_id,
            "csrf_token_hash": csrf_token_hash,
            "expires_at": expires_at,
            "revoked_at": None,
        }

    async def get_active_session(
        self,
        *,
        token_hash: bytes,
        checked_at: datetime,
    ) -> AuthenticatedSession | None:
        session = self.sessions.get(token_hash)
        if (
            session is None
            or session["revoked_at"] is not None
            or session["expires_at"] <= checked_at
            or self.account.status != "active"
        ):
            return None
        return AuthenticatedSession(
            user_id=session["user_id"],
            email=self.account.email,
            csrf_token_hash=session["csrf_token_hash"],
            expires_at=session["expires_at"],
        )

    async def revoke_session(
        self,
        *,
        token_hash: bytes,
        revoked_at: datetime,
    ) -> bool:
        session = self.sessions.get(token_hash)
        if session is None or session["revoked_at"] is not None:
            return False
        session["revoked_at"] = revoked_at
        return True


class FailingAuthenticationRepository(InMemoryAuthenticationRepository):
    """Simulate a safe persistence failure without exposing its detail."""

    async def get_account_credentials(
        self,
        *,
        email: str,
    ) -> AccountCredentials | None:
        del email
        raise AuthenticationRepositoryError("Private database detail.")


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "_env_file": None,
        "app_env": "test",
        "database_url": SecretStr(
            "postgresql://test-user:test-password@localhost/test-newsflow"
        ),
        "login_rate_limit_attempts": 20,
        "session_lifetime_minutes": 60,
    }
    values.update(overrides)
    return Settings(**values)


def make_application(
    repository: InMemoryAuthenticationRepository,
    *,
    settings: Settings | None = None,
    login_rate_limiter: InMemoryRateLimiter | None = None,
) -> Any:
    return create_app(
        settings=settings or make_settings(),
        database=StubDatabase(),
        user_repository=UnusedUserRepository(),
        authentication_repository=repository,
        password_hasher=Argon2PasswordHasher(),
        login_rate_limiter=login_rate_limiter,
    )


@pytest.fixture
def authentication_context() -> Iterator[
    tuple[TestClient, InMemoryAuthenticationRepository]
]:
    hasher = Argon2PasswordHasher()
    repository = InMemoryAuthenticationRepository(hasher.hash(VALID_PASSWORD))
    with TestClient(make_application(repository)) as client:
        yield client, repository


def login(client: TestClient) -> Any:
    return client.post(
        "/api/v1/auth/login",
        json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
    )


def test_successful_login_creates_hashed_session_and_securely_scoped_cookies(
    authentication_context: tuple[TestClient, InMemoryAuthenticationRepository],
) -> None:
    client, repository = authentication_context

    response = login(client)

    assert response.status_code == 200
    assert response.json()["id"] == str(repository.user_id)
    assert response.json()["email"] == VALID_EMAIL
    assert response.json()["message"] == "Login successful"
    assert response.headers["cache-control"] == "no-store"
    assert VALID_PASSWORD not in response.text
    assert "password_hash" not in response.text
    assert "session_token" not in response.text

    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(
        cookie for cookie in cookies if cookie.startswith("newsflow_session=")
    )
    csrf_cookie = next(
        cookie for cookie in cookies if cookie.startswith("newsflow_csrf=")
    )
    assert "HttpOnly" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "SameSite=lax" in session_cookie
    assert "Max-Age=3600" in session_cookie
    assert "Path=/" in session_cookie
    assert len(repository.sessions) == 1
    assert all(len(token_hash) == 32 for token_hash in repository.sessions)


def test_production_login_cookie_is_https_only() -> None:
    hasher = Argon2PasswordHasher()
    repository = InMemoryAuthenticationRepository(hasher.hash(VALID_PASSWORD))
    application = make_application(
        repository,
        settings=make_settings(app_env="production"),
    )

    with TestClient(application) as client:
        response = login(client)

    session_cookie = next(
        cookie
        for cookie in response.headers.get_list("set-cookie")
        if cookie.startswith("newsflow_session=")
    )
    assert "Secure" in session_cookie


def test_wrong_password_and_unknown_account_return_identical_generic_errors(
    authentication_context: tuple[TestClient, InMemoryAuthenticationRepository],
) -> None:
    client, _ = authentication_context

    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": VALID_EMAIL, "password": "Incorrect-Password-5!"},
    )
    unknown_account = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": VALID_PASSWORD},
    )

    expected = {
        "error": {
            "code": "invalid_credentials",
            "message": "Invalid email address or password.",
        }
    }
    assert wrong_password.status_code == 401
    assert unknown_account.status_code == 401
    assert wrong_password.json() == expected
    assert unknown_account.json() == expected
    assert VALID_PASSWORD not in unknown_account.text


def test_disabled_account_receives_generic_credentials_error() -> None:
    hasher = Argon2PasswordHasher()
    repository = InMemoryAuthenticationRepository(
        hasher.hash(VALID_PASSWORD),
        status="disabled",
    )
    with TestClient(make_application(repository)) as client:
        response = login(client)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_current_user_requires_and_accepts_active_session(
    authentication_context: tuple[TestClient, InMemoryAuthenticationRepository],
) -> None:
    client, repository = authentication_context

    unauthenticated = client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "authentication_required"

    assert login(client).status_code == 200
    authenticated = client.get("/api/v1/auth/me")
    assert authenticated.status_code == 200
    assert authenticated.json() == {
        "id": str(repository.user_id),
        "email": VALID_EMAIL,
    }
    assert "password" not in authenticated.text


def test_expired_session_cannot_access_current_user(
    authentication_context: tuple[TestClient, InMemoryAuthenticationRepository],
) -> None:
    client, repository = authentication_context
    assert login(client).status_code == 200
    stored_session = next(iter(repository.sessions.values()))
    stored_session["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_logout_requires_csrf_then_revokes_session_and_clears_cookies(
    authentication_context: tuple[TestClient, InMemoryAuthenticationRepository],
) -> None:
    client, repository = authentication_context
    assert login(client).status_code == 200

    missing_csrf = client.post("/api/v1/auth/logout")
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "csrf_validation_failed"
    assert client.get("/api/v1/auth/me").status_code == 200

    csrf_token = client.cookies.get("newsflow_csrf")
    response = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token or ""},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert all(
        session["revoked_at"] is not None for session in repository.sessions.values()
    )
    assert client.get("/api/v1/auth/me").status_code == 401
    cleared_cookies = response.headers.get_list("set-cookie")
    assert any(cookie.startswith("newsflow_session=") for cookie in cleared_cookies)
    assert any(cookie.startswith("newsflow_csrf=") for cookie in cleared_cookies)


def test_login_is_rate_limited_per_client() -> None:
    hasher = Argon2PasswordHasher()
    repository = InMemoryAuthenticationRepository(hasher.hash(VALID_PASSWORD))
    application = make_application(
        repository,
        login_rate_limiter=InMemoryRateLimiter(
            max_attempts=1,
            window_seconds=60,
        ),
    )

    with TestClient(application) as client:
        first = client.post(
            "/api/v1/auth/login",
            json={"email": VALID_EMAIL, "password": "Wrong-Password-1!"},
        )
        second = login(client)

    assert first.status_code == 401
    assert second.status_code == 429
    assert second.headers["retry-after"] == "60"
    assert second.json()["error"]["code"] == "login_rate_limited"


def test_authentication_storage_failure_returns_safe_error() -> None:
    hasher = Argon2PasswordHasher()
    repository = FailingAuthenticationRepository(hasher.hash(VALID_PASSWORD))

    with TestClient(make_application(repository)) as client:
        response = login(client)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "authentication_unavailable"
    assert "Private database detail" not in response.text
    assert VALID_PASSWORD not in response.text


def test_openapi_documents_login_logout_and_current_user(
    authentication_context: tuple[TestClient, InMemoryAuthenticationRepository],
) -> None:
    client, _ = authentication_context

    openapi = client.get("/openapi.json").json()

    assert openapi["paths"]["/api/v1/auth/login"]["post"]["summary"] == (
        "Log in and create a server-managed session"
    )
    assert "/api/v1/auth/logout" in openapi["paths"]
    assert "/api/v1/auth/me" in openapi["paths"]
    assert openapi["paths"]["/api/v1/auth/me"]["get"]["security"] == [
        {"SessionCookie": []}
    ]
    assert openapi["paths"]["/api/v1/auth/logout"]["post"]["security"] == [
        {"SessionCookie": []}
    ]
    assert openapi["components"]["securitySchemes"]["SessionCookie"]["in"] == ("cookie")
    login_response = openapi["components"]["schemas"]["LoginUserResponse"]
    assert "password" not in login_response["properties"]
    assert "password_hash" not in login_response["properties"]


def test_cors_allows_credentialed_requests_only_from_configured_frontend(
    authentication_context: tuple[TestClient, InMemoryAuthenticationRepository],
) -> None:
    client, _ = authentication_context
    preflight_headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-csrf-token",
    }

    allowed = client.options("/api/v1/auth/logout", headers=preflight_headers)
    rejected = client.options(
        "/api/v1/auth/logout",
        headers={**preflight_headers, "Origin": "https://untrusted.example"},
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
