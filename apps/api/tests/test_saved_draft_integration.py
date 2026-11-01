"""NFA-67 PostgreSQL migration, version history, and transaction proof."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from pydantic import SecretStr

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    ArticleSnapshotTable,
    ArticleTable,
    GeneratedPostTable,
    GenerationRunTable,
    PostVersionHashtagTable,
    PostVersionTable,
    SourceProfileTable,
    UserTable,
)
from app.repositories.saved_drafts import (
    SavedDraftVersionConflict,
    SqlAlchemySavedDraftRepository,
)
from app.services.saved_drafts import SavedDraftService
from tests.support.postgres import (
    DisposablePostgres,
    postgres_resources,
    require_disposable_database,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
OWNER_ID = UUID("67100000-0000-4000-8000-000000000001")
SOURCE_ID = UUID("67100000-0000-4000-8000-000000000002")
ARTICLE_ID = UUID("67100000-0000-4000-8000-000000000003")
SNAPSHOT_ID = UUID("67100000-0000-4000-8000-000000000004")
POST_ID = UUID("67100000-0000-4000-8000-000000000005")
GENERATION_ID = UUID("67100000-0000-4000-8000-000000000006")
ORIGINAL_VERSION_ID = UUID("67100000-0000-4000-8000-000000000007")
ORIGINAL_TEXT = "Original synthetic AI draft.\n\n#Synthetic #News #AI"
FIRST_EDIT = "First human-reviewed draft.\n\n#Synthetic #News #AI"
SECOND_EDIT = "Second human-reviewed draft.\n\n#Synthetic #News #AI"
SYNTHETIC_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$syntheticfixture$not-a-password"
)


def run(coroutine):
    return asyncio.run(coroutine)


@pytest.fixture
def saved_draft_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[DisposablePostgres]:
    """Rebuild only the explicitly approved NFA-67 disposable database."""

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


def _insert_generation_context(resources: DisposablePostgres) -> None:
    """Insert synthetic, permitted source data and one original AI version."""

    with resources.engine.begin() as connection:
        connection.execute(
            sa.insert(SourceProfileTable),
            {
                "id": SOURCE_ID,
                "profile_key": "nfa67-synthetic-source",
                "source_name": "NewsFlow AI synthetic NFA-67 fixture",
                "contract_version": "1.0",
                "profile_type": "fixture",
                "status": "enabled",
                "authorisation_decision_ref": "NFA-67-SYNTHETIC",
                "access_method": "fixture",
                "approved_at": NOW,
            },
        )
        connection.execute(
            sa.insert(UserTable),
            {
                "id": OWNER_ID,
                "email": "nfa67-owner@example.invalid",
                "password_hash": SYNTHETIC_PASSWORD_HASH,
            },
        )
        connection.execute(
            sa.insert(ArticleTable),
            {
                "id": ARTICLE_ID,
                "source_profile_id": SOURCE_ID,
                "source_item_id": "nfa67-article-001",
                "canonical_url": "https://example.invalid/nfa67-article-001",
                "status": "active",
            },
        )
        connection.execute(
            sa.insert(ArticleSnapshotTable),
            {
                "id": SNAPSHOT_ID,
                "article_id": ARTICLE_ID,
                "snapshot_number": 1,
                "contract_version": "1.0",
                "source_name": "NewsFlow AI synthetic NFA-67 fixture",
                "title": "Synthetic permitted persistence demonstration",
                "publication_date": NOW,
                "category": "technology",
                "description": "A fictional database persistence scenario.",
                "canonical_url": "https://example.invalid/nfa67-article-001",
                "permitted_content_status": "available",
                "permitted_content_type": "synthetic",
                "permitted_content_text": "Synthetic permitted context.",
                "storage_allowed": True,
                "display_allowed": True,
                "ai_processing_allowed": True,
                "derivative_output_allowed": True,
                "rights_decision_ref": "NFA-67-SYNTHETIC",
                "access_method": "fixture",
                "retention_rule": "test-run-only",
                "attribution_display_name": "Synthetic NFA-67 fixture",
                "attribution_text": "Source: synthetic NFA-67 fixture",
                "retrieved_at": NOW,
            },
        )
        connection.execute(
            sa.insert(GeneratedPostTable),
            {
                "id": POST_ID,
                "user_id": OWNER_ID,
                "article_snapshot_id": SNAPSHOT_ID,
                "status": "draft",
            },
        )
        connection.execute(
            sa.insert(GenerationRunTable),
            {
                "id": GENERATION_ID,
                "generated_post_id": POST_ID,
                "generation_type": "post",
                "status": "succeeded",
                "idempotency_key": "nfa67-generation-001",
                "provider": "openai",
                "model": "synthetic-model",
                "prompt_template_version": "linkedin_post_v1",
                "prompt_text": "Synthetic prompt retained only in this test database.",
                "provider_request_id": "synthetic-provider-request",
                "attempt_count": 1,
                "created_at": NOW,
                "started_at": NOW,
                "completed_at": NOW,
            },
        )
        connection.execute(
            sa.insert(PostVersionTable),
            {
                "id": ORIGINAL_VERSION_ID,
                "generated_post_id": POST_ID,
                "generation_run_id": GENERATION_ID,
                "previous_version_id": None,
                "version_number": 1,
                "origin": "ai",
                "tone": "professional",
                "length_option": "medium",
                "audience": "general_professionals",
                "hook": "Original synthetic AI draft.",
                "summary": ORIGINAL_TEXT,
                "insight": None,
                "call_to_action": None,
                "rendered_text": ORIGINAL_TEXT,
                "source_attribution": "Source: synthetic NFA-67 fixture",
                "word_count": 6,
                "is_current": True,
                "created_by_user_id": OWNER_ID,
                "created_at": NOW,
            },
        )
        connection.execute(
            sa.insert(PostVersionHashtagTable),
            [
                {
                    "post_version_id": ORIGINAL_VERSION_ID,
                    "position": 1,
                    "hashtag": "#Synthetic",
                },
                {
                    "post_version_id": ORIGINAL_VERSION_ID,
                    "position": 2,
                    "hashtag": "#News",
                },
                {
                    "post_version_id": ORIGINAL_VERSION_ID,
                    "position": 3,
                    "hashtag": "#AI",
                },
            ],
        )


def test_postgresql_save_replay_update_and_stale_write_protection(
    saved_draft_postgres: DisposablePostgres,
) -> None:
    resources = saved_draft_postgres
    _insert_generation_context(resources)
    database = SqlAlchemyDatabase(SecretStr(resources.database_url))
    service = SavedDraftService(SqlAlchemySavedDraftRepository(database))

    created = run(
        service.create(
            owner_id=OWNER_ID,
            generation_id=GENERATION_ID,
            title="Synthetic briefing",
            edited_text=FIRST_EDIT,
            selected_image_id=None,
            idempotency_key="nfa67-save-001",
        )
    )
    replayed = run(
        service.create(
            owner_id=OWNER_ID,
            generation_id=GENERATION_ID,
            title="Synthetic briefing",
            edited_text=FIRST_EDIT,
            selected_image_id=None,
            idempotency_key="nfa67-save-001",
        )
    )
    updated = run(
        service.update(
            owner_id=OWNER_ID,
            saved_draft_id=created.id,
            expected_version=1,
            title="Reviewed synthetic briefing",
            edited_text=SECOND_EDIT,
            selected_image_id=None,
        )
    )
    with pytest.raises(SavedDraftVersionConflict):
        run(
            service.update(
                owner_id=OWNER_ID,
                saved_draft_id=created.id,
                expected_version=1,
                title="Stale overwrite",
                edited_text="This stale text must not persist.",
                selected_image_id=None,
            )
        )

    with resources.engine.connect() as connection:
        versions = (
            connection.execute(
                sa.text(
                    """
                    SELECT id, generation_run_id, previous_version_id,
                           version_number, origin, rendered_text, is_current
                    FROM post_versions
                    WHERE generated_post_id = :post_id
                    ORDER BY version_number
                    """
                ),
                {"post_id": POST_ID},
            )
            .mappings()
            .all()
        )
        saved = (
            connection.execute(
                sa.text(
                    """
                SELECT source_generation_id, selected_post_version_id,
                       library_title, version, save_key_hash, save_payload_hash
                FROM saved_content_items
                WHERE id = :saved_id
                """
                ),
                {"saved_id": created.id},
            )
            .mappings()
            .one()
        )

    assert replayed.id == created.id
    assert created.original_post_version_id == ORIGINAL_VERSION_ID
    assert created.current_post_version_id != ORIGINAL_VERSION_ID
    assert updated.version == 2
    assert updated.source_generation_id == GENERATION_ID
    assert updated.original_post_version_id == ORIGINAL_VERSION_ID
    assert updated.saved_at == created.saved_at
    assert updated.updated_at >= created.updated_at
    assert updated.article_id == ARTICLE_ID
    assert updated.source_title == "Synthetic permitted persistence demonstration"
    assert updated.source_url == "https://example.invalid/nfa67-article-001"
    assert len(versions) == 3
    assert versions[0]["rendered_text"] == ORIGINAL_TEXT
    assert versions[0]["generation_run_id"] == GENERATION_ID
    assert versions[0]["origin"] == "ai"
    assert versions[1]["rendered_text"] == FIRST_EDIT
    assert versions[1]["previous_version_id"] == ORIGINAL_VERSION_ID
    assert versions[2]["rendered_text"] == SECOND_EDIT
    assert versions[2]["is_current"] is True
    assert saved["source_generation_id"] == GENERATION_ID
    assert saved["selected_post_version_id"] == versions[2]["id"]
    assert saved["library_title"] == "Reviewed synthetic briefing"
    assert saved["version"] == 2
    assert len(saved["save_key_hash"]) == 64
    assert len(saved["save_payload_hash"]) == 64

    run(database.close())
