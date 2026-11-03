"""NFA-76 API-boundary security regression tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


class StubDatabase:
    async def check_connection(self) -> None:
        return None


def make_settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        database_url=SecretStr(
            "postgresql://test-user:test-password@localhost:5432/test-newsflow"
        ),
        **overrides,
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    application = create_app(
        settings=make_settings(),
        database=StubDatabase(),
    )
    with TestClient(application) as test_client:
        yield test_client


def test_api_responses_include_security_headers(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    )
    assert response.headers["cross-origin-resource-policy"] == "same-site"
    assert response.headers["permissions-policy"] == (
        "camera=(), geolocation=(), microphone=()"
    )
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-permitted-cross-domain-policies"] == "none"
    assert "strict-transport-security" not in response.headers


def test_hsts_is_enabled_for_production_responses() -> None:
    application = create_app(
        settings=make_settings(app_env="production"),
        database=StubDatabase(),
    )
    client = TestClient(application)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == (
        "max-age=31536000; includeSubDomains"
    )


def test_documentation_remains_usable_without_api_only_csp(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "content-security-policy" not in response.headers
    assert response.headers["x-frame-options"] == "DENY"


def test_oversized_json_body_is_rejected_before_validation() -> None:
    application = create_app(
        settings=make_settings(api_max_request_body_bytes=1_024),
        database=StubDatabase(),
    )
    client = TestClient(application)
    sensitive_marker = "not-a-secret-" + ("x" * 2_000)

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "person@example.com", "password": sensitive_marker},
    )

    assert response.status_code == 413
    assert response.json() == {
        "error": {
            "code": "request_body_too_large",
            "message": "The request body exceeds the configured size limit.",
        }
    }
    assert sensitive_marker not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"


def test_chunked_body_cannot_bypass_request_size_limit() -> None:
    application = create_app(
        settings=make_settings(api_max_request_body_bytes=1_024),
        database=StubDatabase(),
    )
    client = TestClient(application)

    def chunks() -> Iterator[bytes]:
        yield b'{"email":"person@example.com","password":"'
        yield b"x" * 2_000
        yield b'"}'

    response = client.post(
        "/api/v1/auth/register",
        content=chunks(),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_body_too_large"


def test_non_json_state_changing_body_is_rejected() -> None:
    application = create_app(
        settings=make_settings(),
        database=StubDatabase(),
    )
    client = TestClient(application)

    response = client.post(
        "/api/v1/auth/login",
        content="email=person@example.com&password=unsafe",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 415
    assert response.json() == {
        "error": {
            "code": "unsupported_media_type",
            "message": "Request bodies must use application/json.",
        }
    }


def test_exact_cors_origin_is_enforced_with_credentials(client: TestClient) -> None:
    preflight = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-csrf-token",
    }

    allowed = client.options("/api/v1/auth/logout", headers=preflight)
    rejected = client.options(
        "/api/v1/auth/logout",
        headers={**preflight, "Origin": "https://attacker.example"},
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


def test_every_openapi_endpoint_is_present_in_security_inventory() -> None:
    application = create_app(
        settings=make_settings(),
        database=StubDatabase(),
    )
    openapi_paths = application.openapi()["paths"]
    repository_root = Path(__file__).resolve().parents[3]
    inventory = repository_root.joinpath("docs/api-security.md").read_text(
        encoding="utf-8"
    )

    for path, operations in openapi_paths.items():
        for method in operations:
            assert f"`{method.upper()} {path}`" in inventory
