"""NFA-73 joined HTTP and PostgreSQL saved-content lifecycle proof."""

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from app.security import Argon2PasswordHasher
from tests.support.postgres import (
    DisposablePostgres,
    postgres_resources,
    require_disposable_database,
)
from tests.test_saved_draft_integration import (
    FIRST_EDIT,
    GENERATION_ID,
    IMAGE_ID,
    OWNER_ID,
    SECOND_EDIT,
    _insert_generation_context,
)

pytestmark = pytest.mark.integration

OWNER_EMAIL = "nfa73-owner@example.com"
SECOND_EMAIL = "nfa73-second-user@example.com"
TEST_PASSWORD = "Synthetic-Lifecycle-Password-42!"
IMAGE_BYTES = b"\x89PNG\r\n\x1a\nNewsFlow-AI-NFA-73-synthetic-image"


@pytest.fixture
def lifecycle_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[DisposablePostgres]:
    """Rebuild only the explicitly approved E7 disposable database."""

    database_url = require_disposable_database(
        required_name="newsflow_saved_draft_test"
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "test")
    resources = postgres_resources(database_url)
    command.downgrade(resources.alembic_config, "base")
    command.upgrade(resources.alembic_config, "head")
    try:
        yield resources
    finally:
        command.downgrade(resources.alembic_config, "base")
        resources.engine.dispose()


@dataclass(frozen=True)
class BrowserSession:
    """Purpose-limited cookie values captured for one synthetic user."""

    session_token: str
    csrf_token: str


def _capture_session(client: TestClient) -> BrowserSession:
    session_token = client.cookies.get("newsflow_session")
    csrf_token = client.cookies.get("newsflow_csrf")
    assert session_token is not None
    assert csrf_token is not None
    return BrowserSession(session_token=session_token, csrf_token=csrf_token)


def _use_session(client: TestClient, session: BrowserSession | None) -> None:
    client.cookies.clear()
    if session is not None:
        client.cookies.set("newsflow_session", session.session_token)
        client.cookies.set("newsflow_csrf", session.csrf_token)


def _csrf(session: BrowserSession) -> dict[str, str]:
    return {"X-CSRF-Token": session.csrf_token}


def _prepare_fixture(
    resources: DisposablePostgres,
    *,
    storage_root: Path,
) -> None:
    """Create synthetic user, generation, image, and private object fixtures."""

    _insert_generation_context(resources)
    image_path = storage_root / "generated-images" / "nfa68-private-image.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(IMAGE_BYTES)
    password_hash = Argon2PasswordHasher().hash(TEST_PASSWORD)
    with resources.engine.begin() as connection:
        connection.execute(
            sa.text(
                """
                UPDATE users
                SET email = :email, password_hash = :password_hash
                WHERE id = :owner_id
                """
            ),
            {
                "email": OWNER_EMAIL,
                "password_hash": password_hash,
                "owner_id": OWNER_ID,
            },
        )
        connection.execute(
            sa.text(
                """
                UPDATE generated_images
                SET byte_size = :byte_size, content_sha256 = :digest
                WHERE id = :image_id
                """
            ),
            {
                "byte_size": len(IMAGE_BYTES),
                "digest": hashlib.sha256(IMAGE_BYTES).hexdigest(),
                "image_id": IMAGE_ID,
            },
        )


def test_complete_saved_content_lifecycle_is_owner_scoped_and_retained_safely(
    lifecycle_postgres: DisposablePostgres,
    tmp_path: Path,
) -> None:
    """Exercise create through retention using real routes and PostgreSQL."""

    resources = lifecycle_postgres
    _prepare_fixture(resources, storage_root=tmp_path)
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=SecretStr(resources.database_url),
        image_storage_local_root=tmp_path,
        registration_rate_limit_attempts=100,
        login_rate_limit_attempts=100,
    )

    with TestClient(create_app(settings=settings)) as client:
        # Authentication is required at every private entry point.
        assert client.get("/api/v1/drafts").status_code == 401
        assert client.get(f"/api/images/{IMAGE_ID}/download").status_code == 401

        second_registration = client.post(
            "/api/v1/auth/register",
            json={"email": SECOND_EMAIL, "password": TEST_PASSWORD},
        )
        assert second_registration.status_code == 201
        client.cookies.clear()

        owner_login = client.post(
            "/api/v1/auth/login",
            json={"email": OWNER_EMAIL, "password": TEST_PASSWORD},
        )
        assert owner_login.status_code == 200
        owner_session = _capture_session(client)
        client.cookies.clear()

        second_login = client.post(
            "/api/v1/auth/login",
            json={"email": SECOND_EMAIL, "password": TEST_PASSWORD},
        )
        assert second_login.status_code == 200
        second_session = _capture_session(client)

        _use_session(client, owner_session)
        create_payload = {
            "generation_id": str(GENERATION_ID),
            "title": "Synthetic lifecycle briefing",
            "edited_text": FIRST_EDIT,
            "selected_image_id": str(IMAGE_ID),
        }
        created = client.post(
            "/api/v1/drafts",
            json=create_payload,
            headers={**_csrf(owner_session), "Idempotency-Key": "nfa73-save-001"},
        )
        assert created.status_code == 201
        draft = created.json()
        draft_id = draft["id"]
        assert draft["version"] == 1
        assert draft["edited_text"] == FIRST_EDIT
        assert draft["selected_image_id"] == str(IMAGE_ID)
        assert "storage_key" not in created.text
        assert "password" not in created.text

        replay = client.post(
            "/api/v1/drafts",
            json=create_payload,
            headers={**_csrf(owner_session), "Idempotency-Key": "nfa73-save-001"},
        )
        duplicate = client.post(
            "/api/v1/drafts",
            json=create_payload,
            headers={**_csrf(owner_session), "Idempotency-Key": "nfa73-save-002"},
        )
        assert replay.status_code == 201
        assert replay.json()["id"] == draft_id
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "draft_already_saved"

        first_page = client.get("/api/v1/drafts?page=1&page_size=1")
        empty_page = client.get("/api/v1/drafts?page=2&page_size=1")
        retrieved = client.get(f"/api/v1/drafts/{draft_id}")
        assert first_page.status_code == 200
        assert first_page.json()["total_items"] == 1
        assert first_page.json()["items"][0]["id"] == draft_id
        assert empty_page.json()["items"] == []
        assert retrieved.json()["source"]["attribution"].startswith("Source:")

        updated = client.put(
            f"/api/v1/drafts/{draft_id}",
            json={
                "expected_version": 1,
                "title": "Reviewed synthetic lifecycle briefing",
                "edited_text": SECOND_EDIT,
                "selected_image_id": str(IMAGE_ID),
            },
            headers=_csrf(owner_session),
        )
        stale = client.patch(
            f"/api/v1/drafts/{draft_id}",
            json={"expected_version": 1, "title": "Stale overwrite"},
            headers=_csrf(owner_session),
        )
        assert updated.status_code == 200
        assert updated.json()["version"] == 2
        assert updated.json()["edited_text"] == SECOND_EDIT
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "draft_version_conflict"
        assert (
            client.get(f"/api/v1/drafts/{draft_id}").json()["edited_text"]
            == SECOND_EDIT
        )

        history = client.get(f"/api/v1/drafts/{draft_id}/versions?page_size=1")
        assert history.status_code == 200
        assert history.json()["total_items"] == 2
        assert history.json()["total_pages"] == 2
        current_history = history.json()["items"][0]
        assert current_history["version_number"] == 2
        assert current_history["change_type"] == "manual_edit"
        historical = client.get(
            f"/api/v1/drafts/{draft_id}/versions/{current_history['id']}"
        )
        assert historical.status_code == 200
        assert historical.json()["edited_text"] == SECOND_EDIT

        download = client.get(f"/api/images/{IMAGE_ID}/download")
        assert download.status_code == 200
        assert download.content == IMAGE_BYTES
        assert download.headers["content-disposition"].startswith("attachment;")
        assert download.headers["cache-control"] == "private, no-store, max-age=0"

        # A second authenticated user receives the same private 404 for every object.
        _use_session(client, second_session)
        assert client.get(f"/api/v1/drafts/{draft_id}").status_code == 404
        assert client.get(f"/api/v1/drafts/{draft_id}/versions").status_code == 404
        assert historical.json()["id"]
        assert (
            client.get(
                f"/api/v1/drafts/{draft_id}/versions/{current_history['id']}"
            ).status_code
            == 404
        )
        assert client.get(f"/api/images/{IMAGE_ID}/download").status_code == 404
        assert (
            client.patch(
                f"/api/v1/drafts/{draft_id}",
                json={"expected_version": 2, "title": "Cross-user overwrite"},
                headers=_csrf(second_session),
            ).status_code
            == 404
        )
        assert (
            client.delete(
                f"/api/v1/drafts/{draft_id}",
                headers=_csrf(second_session),
            ).status_code
            == 404
        )

        _use_session(client, owner_session)
        deleted = client.delete(
            f"/api/v1/drafts/{draft_id}",
            headers=_csrf(owner_session),
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/drafts/{draft_id}").status_code == 404
        assert client.get(f"/api/v1/drafts/{draft_id}/versions").status_code == 404
        assert client.get(f"/api/images/{IMAGE_ID}/download").status_code == 404
        after_delete = client.get("/api/v1/drafts")
        assert after_delete.json()["items"] == []
        assert after_delete.json()["total_items"] == 0

        with resources.engine.begin() as connection:
            lifecycle = (
                connection.execute(
                    sa.text(
                        """
                        SELECT item.user_id, item.version, item.deleted_at,
                               image.status AS image_status,
                               job.status AS cleanup_status
                        FROM saved_content_items AS item
                        JOIN generated_images AS image
                          ON image.id = item.selected_image_id
                        JOIN image_cleanup_jobs AS job
                          ON job.generated_image_id = image.id
                        WHERE item.id = :draft_id
                        """
                    ),
                    {"draft_id": draft_id},
                )
                .mappings()
                .one()
            )
            assert lifecycle["user_id"] == OWNER_ID
            assert lifecycle["version"] == 2
            assert lifecycle["deleted_at"] is not None
            assert lifecycle["image_status"] == "deleted"
            assert lifecycle["cleanup_status"] == "completed"
            connection.execute(
                sa.text(
                    """
                    UPDATE saved_content_items
                    SET deletion_due_at = now() - interval '1 minute'
                    WHERE id = :draft_id
                    """
                ),
                {"draft_id": draft_id},
            )

        assert client.portal is not None
        retention = client.portal.call(
            client.app.state.content_deletion_service.run_retention
        )
        assert retention.drafts_redacted == 1

    with resources.engine.connect() as connection:
        retained = (
            connection.execute(
                sa.text(
                    """
                SELECT
                  (SELECT count(*) FROM saved_content_items WHERE id = :draft_id)
                    AS saved_count,
                  (SELECT count(*) FROM saved_draft_versions
                   WHERE saved_draft_id = :draft_id) AS history_count
                """
                ),
                {"draft_id": draft_id},
            )
            .mappings()
            .one()
        )
    assert retained["saved_count"] == 0
    assert retained["history_count"] == 0
