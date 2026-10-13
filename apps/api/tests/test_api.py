"""API foundation and PostgreSQL readiness tests."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import DatabaseConfigurationError, Settings
from app.database import DatabaseConnectionError
from app.main import create_app


class StubDatabase:
    """Controllable database boundary for API tests."""

    def __init__(self, *, fail_after_checks: int | None = None) -> None:
        self.check_count = 0
        self.fail_after_checks = fail_after_checks

    async def check_connection(self) -> None:
        self.check_count += 1
        if (
            self.fail_after_checks is not None
            and self.check_count > self.fail_after_checks
        ):
            raise DatabaseConnectionError("Test database failure.")


def make_test_settings() -> Settings:
    return Settings(
        database_url=SecretStr(
            "postgresql://test-user:test-password@localhost:5432/test-newsflow"
        )
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    application = create_app(
        settings=make_test_settings(),
        database=StubDatabase(),
    )
    with TestClient(application) as test_client:
        yield test_client


def test_health_check_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_check_confirms_database_connection(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }


def test_readiness_check_returns_safe_error_when_database_fails() -> None:
    application = create_app(
        settings=make_test_settings(),
        database=StubDatabase(fail_after_checks=1),
    )

    with TestClient(application) as test_client:
        response = test_client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "The database is temporarily unavailable.",
        }
    }
    assert "test-password" not in response.text


def test_startup_fails_when_database_is_unavailable() -> None:
    application = create_app(
        settings=make_test_settings(),
        database=StubDatabase(fail_after_checks=0),
    )

    with pytest.raises(DatabaseConnectionError, match="Test database failure"):
        with TestClient(application):
            pass


def test_startup_fails_safely_when_database_url_is_missing() -> None:
    application = create_app(settings=Settings(database_url=None))

    with pytest.raises(
        DatabaseConfigurationError,
        match="DATABASE_URL must be set",
    ):
        with TestClient(application):
            pass


def test_openapi_schema_describes_health_checks(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
    assert "/ready" in response.json()["paths"]


def test_swagger_documentation_is_available(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_unknown_route_uses_standard_error_shape(client: TestClient) -> None:
    response = client.get("/route-that-does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "http_404",
            "message": "Not Found",
        }
    }
