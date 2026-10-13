"""Optional live PostgreSQL and FastAPI readiness integration test."""

import os

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


@pytest.mark.integration
def test_fastapi_connects_to_live_postgres() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run the live PostgreSQL test.")

    application = create_app(
        settings=Settings(
            database_url=SecretStr(database_url),
            database_connect_timeout_seconds=5,
        )
    )

    with TestClient(application) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }
