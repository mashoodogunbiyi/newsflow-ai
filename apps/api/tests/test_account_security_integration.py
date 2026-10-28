"""Opt-in PostgreSQL proof of session-derived object ownership."""

from uuid import UUID

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.database.seed import SEED_IDS, seed_database
from app.main import create_app
from app.security import Argon2PasswordHasher
from tests.support.account_security import TEST_PASSWORD
from tests.support.postgres import DisposablePostgres

pytestmark = pytest.mark.integration
OWNER_EMAIL = "seed.owner@example.com"


def test_postgresql_enforces_cross_user_saved_content_isolation(
    account_security_postgres: DisposablePostgres,
) -> None:
    resources = account_security_postgres
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=SecretStr(resources.database_url),
        seed_data_enabled=True,
        registration_rate_limit_attempts=20,
        login_rate_limit_attempts=20,
    )
    seed_database(settings)
    password_hash = Argon2PasswordHasher().hash(TEST_PASSWORD)
    with resources.engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE users SET email = :email, password_hash = :password_hash, "
                "status = 'active' "
                "WHERE id = :user_id"
            ),
            {
                "password_hash": password_hash,
                "email": OWNER_EMAIL,
                "user_id": SEED_IDS["user"],
            },
        )

    with TestClient(create_app(settings=settings)) as client:
        owner_login = client.post(
            "/api/v1/auth/login",
            json={"email": OWNER_EMAIL, "password": TEST_PASSWORD},
        )
        owner_read = client.get(f"/api/v1/library/items/{SEED_IDS['saved_content']}")
        owner_collection = client.get("/api/v1/library/items")
        client.cookies.clear()

        other_registration = client.post(
            "/api/v1/auth/register",
            json={"email": "other.owner@example.com", "password": TEST_PASSWORD},
        )
        other_login = client.post(
            "/api/v1/auth/login",
            json={"email": "other.owner@example.com", "password": TEST_PASSWORD},
        )
        csrf_token = client.cookies.get("newsflow_csrf") or ""
        cross_user_read = client.get(
            f"/api/v1/library/items/{SEED_IDS['saved_content']}"
        )
        cross_user_update = client.patch(
            f"/api/v1/library/items/{SEED_IDS['saved_content']}",
            json={"library_title": "Attempted PostgreSQL takeover"},
            headers={"X-CSRF-Token": csrf_token},
        )
        cross_user_delete = client.delete(
            f"/api/v1/library/items/{SEED_IDS['saved_content']}",
            headers={"X-CSRF-Token": csrf_token},
        )
        cross_user_export = client.get(
            f"/api/v1/library/items/{SEED_IDS['saved_content']}/export"
        )
        cross_user_save = client.post(
            "/api/v1/library/items",
            json={
                "generated_post_id": SEED_IDS["generated_post"],
                "selected_post_version_id": SEED_IDS["post_version"],
            },
            headers={"X-CSRF-Token": csrf_token},
        )
        other_collection = client.get("/api/v1/library/items")

    assert owner_login.status_code == 200
    assert owner_read.status_code == 200
    assert [item["id"] for item in owner_collection.json()["items"]] == [
        SEED_IDS["saved_content"]
    ]
    assert other_registration.status_code == 201
    assert other_login.status_code == 200
    expected = {
        "error": {
            "code": "private_resource_not_found",
            "message": "The requested resource was not found.",
        }
    }
    for response in (
        cross_user_read,
        cross_user_update,
        cross_user_delete,
        cross_user_export,
        cross_user_save,
    ):
        assert response.status_code == 404
        assert response.json() == expected
        assert "Synthetic energy dashboard" not in response.text
    assert other_collection.status_code == 200
    assert other_collection.json() == {"items": []}

    with resources.engine.connect() as connection:
        protected_item = connection.execute(
            sa.text(
                "SELECT user_id, library_title, deleted_at "
                "FROM saved_content_items WHERE id = :item_id"
            ),
            {"item_id": SEED_IDS["saved_content"]},
        ).one()
    assert protected_item.user_id == UUID(SEED_IDS["user"])
    assert protected_item.library_title == "Synthetic energy dashboard example"
    assert protected_item.deleted_at is None
