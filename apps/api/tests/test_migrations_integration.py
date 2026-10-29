"""Opt-in destructive integration test for migrations and seed data."""

import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.seed import seed_database
from app.main import create_app

pytestmark = pytest.mark.integration

API_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "alembic_version",
    "article_snapshots",
    "article_provenance_events",
    "article_rights_versions",
    "article_sync_checkpoints",
    "article_sync_jobs",
    "articles",
    "generated_images",
    "generated_posts",
    "generation_facts",
    "generation_runs",
    "post_claim_sources",
    "post_claims",
    "post_version_hashtags",
    "post_versions",
    "saved_content_items",
    "sessions",
    "source_profiles",
    "users",
}
EXPECTED_SEED_COUNTS = {
    "users": 1,
    "source_profiles": 1,
    "articles": 1,
    "article_snapshots": 1,
    "article_provenance_events": 1,
    "article_rights_versions": 1,
    "generated_posts": 1,
    "generation_runs": 1,
    "generation_facts": 2,
    "post_versions": 1,
    "post_claims": 2,
    "saved_content_items": 1,
    "post_version_hashtags": 3,
    "post_claim_sources": 2,
}


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    reset_allowed = os.getenv("ALLOW_DATABASE_RESET_FOR_TESTS", "").lower()
    if not database_url or reset_allowed != "true":
        pytest.skip(
            "Set TEST_DATABASE_URL and ALLOW_DATABASE_RESET_FOR_TESTS=true "
            "for a disposable PostgreSQL database."
        )
    if "newsflow_migration_test" not in database_url:
        pytest.fail(
            "TEST_DATABASE_URL must name a disposable database containing "
            "'newsflow_migration_test'."
        )
    return database_url


def _sqlalchemy_url(database_url: str) -> str:
    return database_url.replace("postgresql://", "postgresql+psycopg://", 1)


def test_upgrade_seed_repeat_rollback_and_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _test_database_url()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SEED_DATA_ENABLED", "true")

    alembic_config = Config(str(API_ROOT / "alembic.ini"))
    engine = sa.create_engine(_sqlalchemy_url(database_url))
    settings = Settings(_env_file=None)

    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    assert EXPECTED_TABLES <= set(sa.inspect(engine).get_table_names())
    session_columns = {
        column["name"] for column in sa.inspect(engine).get_columns("sessions")
    }
    assert "csrf_token_hash" in session_columns
    session_indexes = {
        index["name"] for index in sa.inspect(engine).get_indexes("sessions")
    }
    assert {"ix_sessions_user_id", "ix_sessions_expires_at"} <= session_indexes
    user_columns = {
        column["name"] for column in sa.inspect(engine).get_columns("users")
    }
    assert "role" in user_columns
    sync_indexes = {
        index["name"] for index in sa.inspect(engine).get_indexes("article_sync_jobs")
    }
    assert "uq_article_sync_jobs_active_provider" in sync_indexes
    assert {
        "ix_article_sync_jobs_created_at",
        "ix_article_sync_jobs_status_created",
    } <= sync_indexes
    sync_columns = {
        column["name"] for column in sa.inspect(engine).get_columns("article_sync_jobs")
    }
    assert {
        "provider_duration_ms",
        "provider_failures",
        "error_category",
        "failed_stage",
    } <= sync_columns
    generation_columns = {
        column["name"] for column in sa.inspect(engine).get_columns("generation_runs")
    }
    assert "article_rights_version_id" in generation_columns
    generation_indexes = {
        index["name"] for index in sa.inspect(engine).get_indexes("generation_runs")
    }
    assert "ix_generation_runs_article_rights_version" in generation_indexes
    snapshot_indexes = {
        index["name"] for index in sa.inspect(engine).get_indexes("article_snapshots")
    }
    assert "ix_article_snapshots_publication_article" in snapshot_indexes
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT 1")).scalar_one() == 1

    with TestClient(create_app(settings=settings)) as client:
        readiness_response = client.get("/ready")
    assert readiness_response.status_code == 200
    assert readiness_response.json() == {
        "status": "ready",
        "database": "connected",
    }

    first_counts = seed_database(settings)
    second_counts = seed_database(settings)
    assert first_counts == EXPECTED_SEED_COUNTS
    assert second_counts == EXPECTED_SEED_COUNTS

    command.downgrade(alembic_config, "base")
    assert not (EXPECTED_TABLES - {"alembic_version"}) & set(
        sa.inspect(engine).get_table_names()
    )

    command.upgrade(alembic_config, "head")
    assert seed_database(settings) == EXPECTED_SEED_COUNTS
    engine.dispose()
