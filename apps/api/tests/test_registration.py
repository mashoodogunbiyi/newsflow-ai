"""User registration endpoint and credential-safety tests."""

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from app.repositories import (
    DuplicateUserEmailError,
    RegisteredUser,
    UserRepositoryError,
)
from app.security import Argon2PasswordHasher, InMemoryRateLimiter

VALID_PASSWORD = "Correct-Horse-Battery-9!"


class StubDatabase:
    """Satisfy application startup without a live database."""

    async def check_connection(self) -> None:
        return None


class InMemoryUserRepository:
    """Capture hashes without using PostgreSQL in fast endpoint tests."""

    def __init__(self) -> None:
        self.users: dict[str, tuple[UUID, str]] = {}

    async def create_user(self, *, email: str, password_hash: str) -> RegisteredUser:
        if email in self.users:
            raise DuplicateUserEmailError("Duplicate test email.")
        user_id = uuid4()
        self.users[email] = (user_id, password_hash)
        return RegisteredUser(id=user_id, email=email)


class FailingUserRepository:
    """Simulate a safe storage failure."""

    async def create_user(self, *, email: str, password_hash: str) -> RegisteredUser:
        del email, password_hash
        raise UserRepositoryError("Private database detail.")


@pytest.fixture
def registration_context() -> Iterator[
    tuple[TestClient, InMemoryUserRepository, Argon2PasswordHasher]
]:
    repository = InMemoryUserRepository()
    password_hasher = Argon2PasswordHasher()
    application = create_app(
        settings=Settings(
            _env_file=None,
            database_url=SecretStr(
                "postgresql://test-user:test-password@localhost/test-newsflow"
            ),
            registration_rate_limit_attempts=20,
        ),
        database=StubDatabase(),
        user_repository=repository,
        password_hasher=password_hasher,
    )
    with TestClient(application) as client:
        yield client, repository, password_hasher


def test_successful_registration_hashes_password_and_returns_safe_response(
    registration_context: tuple[
        TestClient,
        InMemoryUserRepository,
        Argon2PasswordHasher,
    ],
) -> None:
    client, repository, password_hasher = registration_context

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "  New.User@Example.com  ", "password": VALID_PASSWORD},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new.user@example.com"
    assert response.json()["message"] == "Account created successfully"
    assert set(response.json()) == {"id", "email", "message"}

    _, stored_password_hash = repository.users["new.user@example.com"]
    assert stored_password_hash != VALID_PASSWORD
    assert stored_password_hash.startswith("$argon2id$")
    assert password_hasher.verify(stored_password_hash, VALID_PASSWORD)
    assert VALID_PASSWORD not in response.text
    assert "password_hash" not in response.text


def test_duplicate_email_is_rejected_without_exposing_credentials(
    registration_context: tuple[
        TestClient,
        InMemoryUserRepository,
        Argon2PasswordHasher,
    ],
) -> None:
    client, _, _ = registration_context
    request = {"email": "duplicate@example.com", "password": VALID_PASSWORD}

    first_response = client.post("/api/v1/auth/register", json=request)
    duplicate_response = client.post("/api/v1/auth/register", json=request)

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "error": {
            "code": "email_already_registered",
            "message": "An account with this email already exists.",
        }
    }
    assert VALID_PASSWORD not in duplicate_response.text
    assert "password_hash" not in duplicate_response.text


def test_invalid_email_returns_clear_safe_validation_error(
    registration_context: tuple[
        TestClient,
        InMemoryUserRepository,
        Argon2PasswordHasher,
    ],
) -> None:
    client, repository, _ = registration_context

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": VALID_PASSWORD},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert repository.users == {}
    assert VALID_PASSWORD not in response.text


@pytest.mark.parametrize(
    "weak_password",
    [
        "Short1!",
        "all-lowercase-123!",
        "ALL-UPPERCASE-123!",
        "MissingNumbers!",
        "MissingSymbol123",
    ],
)
def test_weak_password_is_rejected(
    registration_context: tuple[
        TestClient,
        InMemoryUserRepository,
        Argon2PasswordHasher,
    ],
    weak_password: str,
) -> None:
    client, repository, _ = registration_context

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": weak_password},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert repository.users == {}
    assert weak_password not in response.text


def test_registration_storage_failure_returns_safe_error() -> None:
    application = create_app(
        settings=Settings(
            _env_file=None,
            database_url=SecretStr(
                "postgresql://test-user:test-password@localhost/test-newsflow"
            ),
        ),
        database=StubDatabase(),
        user_repository=FailingUserRepository(),
    )

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "failure@example.com", "password": VALID_PASSWORD},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "registration_unavailable"
    assert "Private database detail" not in response.text
    assert VALID_PASSWORD not in response.text


def test_registration_is_rate_limited_per_client() -> None:
    application = create_app(
        settings=Settings(
            _env_file=None,
            database_url=SecretStr(
                "postgresql://test-user:test-password@localhost/test-newsflow"
            ),
        ),
        database=StubDatabase(),
        user_repository=InMemoryUserRepository(),
        registration_rate_limiter=InMemoryRateLimiter(
            max_attempts=1,
            window_seconds=60,
        ),
    )

    with TestClient(application) as client:
        first_response = client.post(
            "/api/v1/auth/register",
            json={"email": "invalid-email", "password": VALID_PASSWORD},
        )
        second_response = client.post(
            "/api/v1/auth/register",
            json={"email": "second@example.com", "password": VALID_PASSWORD},
        )

    assert first_response.status_code == 422
    assert second_response.status_code == 429
    assert second_response.headers["retry-after"] == "60"
    assert second_response.json()["error"]["code"] == "registration_rate_limited"


def test_openapi_schema_documents_registration_endpoint(
    registration_context: tuple[
        TestClient,
        InMemoryUserRepository,
        Argon2PasswordHasher,
    ],
) -> None:
    client, _, _ = registration_context

    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"]["/api/v1/auth/register"]["post"]

    assert operation["summary"] == "Register a user account"
    assert operation["tags"] == ["Authentication"]
    assert operation["responses"]["201"]["description"] == "Successful Response"
    assert "409" in operation["responses"]
    assert "422" in operation["responses"]
    response_schema = openapi["components"]["schemas"]["RegisterUserResponse"]
    assert "password" not in response_schema["properties"]
    assert "password_hash" not in response_schema["properties"]
