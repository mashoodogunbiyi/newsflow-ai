"""NFA-54 PostgreSQL and private-storage image workflow proof."""

import asyncio
import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from pydantic import SecretBytes, SecretStr

from app.core.image_storage_config import ImageStorageConfiguration
from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    ArticleSnapshotTable,
    ArticleTable,
    GeneratedPostTable,
    GenerationRunTable,
    SourceProfileTable,
    UserTable,
)
from app.models.generated_image import (
    GeneratedImageStorageRequest,
    ImageSafetyReviewStatus,
)
from app.models.image_generation import (
    GeneratedImageDataReference,
    ImageDataReferenceKind,
    ImageGenerationQuality,
    ImageGenerationSize,
    ImageGenerationUsage,
    ImageOutputFormat,
    OpenAIImageGenerationResult,
)
from app.repositories.generated_images import SqlAlchemyGeneratedImageRepository
from app.services.generated_image_storage import GeneratedImageStorageService
from app.services.image_delivery import ImageDeliveryService
from app.services.image_storage import LocalPrivateImageStorage
from app.services.image_validation import GeneratedImageValidationService
from tests.support.image_workflow import SyntheticImageFiles
from tests.support.postgres import (
    DisposablePostgres,
    postgres_resources,
    require_disposable_database,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
OWNER_ID = UUID("54100000-0000-4000-8000-000000000001")
OTHER_OWNER_ID = UUID("54100000-0000-4000-8000-000000000002")
SOURCE_ID = UUID("54100000-0000-4000-8000-000000000003")
ARTICLE_ID = UUID("54100000-0000-4000-8000-000000000004")
SNAPSHOT_ID = UUID("54100000-0000-4000-8000-000000000005")
POST_ID = UUID("54100000-0000-4000-8000-000000000006")
PARENT_RUN_ID = UUID("54100000-0000-4000-8000-000000000007")
CHILD_RUN_ID = UUID("54100000-0000-4000-8000-000000000008")
PARENT_REQUEST_ID = UUID("54100000-0000-4000-8000-000000000009")
CHILD_REQUEST_ID = UUID("54100000-0000-4000-8000-000000000010")
RIGHTS_ID = UUID("54100000-0000-4000-8000-000000000011")
SAFETY_ID = UUID("54100000-0000-4000-8000-000000000012")
SYNTHETIC_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$syntheticfixture$not-a-real-password-hash"
)


def run(coroutine):
    return asyncio.run(coroutine)


@pytest.fixture
def image_pipeline_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[DisposablePostgres]:
    """Rebuild only the explicitly approved E5 disposable database."""

    database_url = require_disposable_database(
        required_name="newsflow_image_pipeline_test"
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


def insert_owned_image_context(resources: DisposablePostgres) -> None:
    """Insert only synthetic records required by the real image repository."""

    with resources.engine.begin() as connection:
        connection.execute(
            sa.insert(SourceProfileTable),
            {
                "id": SOURCE_ID,
                "profile_key": "nfa54-synthetic-source",
                "source_name": "NewsFlow AI synthetic E5 fixture",
                "contract_version": "1.0",
                "profile_type": "fixture",
                "status": "enabled",
                "authorisation_decision_ref": "NFA-54-SYNTHETIC",
                "access_method": "fixture",
                "approved_at": NOW,
            },
        )
        connection.execute(
            sa.insert(UserTable),
            [
                {
                    "id": OWNER_ID,
                    "email": "nfa54-owner@example.invalid",
                    "password_hash": SYNTHETIC_PASSWORD_HASH,
                },
                {
                    "id": OTHER_OWNER_ID,
                    "email": "nfa54-other@example.invalid",
                    "password_hash": SYNTHETIC_PASSWORD_HASH,
                },
            ],
        )
        connection.execute(
            sa.insert(ArticleTable),
            {
                "id": ARTICLE_ID,
                "source_profile_id": SOURCE_ID,
                "source_item_id": "nfa54-article-001",
                "canonical_url": "https://example.invalid/nfa54-article-001",
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
                "source_name": "NewsFlow AI synthetic E5 fixture",
                "title": "Synthetic accessibility technology demonstration",
                "publication_date": NOW,
                "category": "technology",
                "description": "A fictional accessibility technology scenario.",
                "canonical_url": "https://example.invalid/nfa54-article-001",
                "permitted_content_status": "available",
                "permitted_content_type": "synthetic",
                "permitted_content_text": "Synthetic permitted context.",
                "storage_allowed": True,
                "display_allowed": True,
                "ai_processing_allowed": True,
                "derivative_output_allowed": True,
                "rights_decision_ref": "NFA-54-SYNTHETIC",
                "access_method": "fixture",
                "retention_rule": "test-run-only",
                "attribution_display_name": "Synthetic E5 fixture",
                "attribution_text": "Source: NewsFlow AI synthetic E5 fixture",
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
            [
                generation_run_values(PARENT_RUN_ID, "nfa54-parent-run"),
                generation_run_values(CHILD_RUN_ID, "nfa54-child-run"),
            ],
        )


def generation_run_values(run_id: UUID, idempotency_key: str) -> dict[str, object]:
    return {
        "id": run_id,
        "generated_post_id": POST_ID,
        "generation_type": "image",
        "status": "succeeded",
        "idempotency_key": idempotency_key,
        "provider": "openai",
        "model": "gpt-image-2.5-flare",
        "prompt_template_version": "image_prompt_v1",
        "prompt_text": "Prompt content intentionally not retained in this test.",
        "provider_request_id": f"provider-{run_id}",
        "attempt_count": 1,
        "created_at": NOW,
        "started_at": NOW,
        "completed_at": NOW,
    }


def generated_result(
    *,
    request_id: UUID,
    image_bytes: bytes,
) -> OpenAIImageGenerationResult:
    return OpenAIImageGenerationResult(
        request_id=request_id,
        model_identifier="gpt-image-2.5-flare",
        image_data_reference=GeneratedImageDataReference(
            kind=ImageDataReferenceKind.INLINE_BYTES,
            media_type="image/png",
            data=SecretBytes(image_bytes),
            byte_length=len(image_bytes),
            sha256=hashlib.sha256(image_bytes).hexdigest(),
        ),
        usage_metadata=ImageGenerationUsage(
            input_tokens=12,
            output_tokens=24,
            total_tokens=36,
        ),
        provider_request_id=f"provider-{request_id}",
        prompt_version="image_prompt_v1",
        safety_policy_version="image_safety_v1",
        safety_evaluation_id=SAFETY_ID,
        rights_version_id=RIGHTS_ID,
        size=ImageGenerationSize.LANDSCAPE,
        quality=ImageGenerationQuality.MEDIUM,
        output_format=ImageOutputFormat.PNG,
        created_at=NOW,
    )


def test_postgresql_private_storage_versions_and_owner_isolation(
    image_pipeline_postgres: DisposablePostgres,
    image_workflow_files: SyntheticImageFiles,
    tmp_path: Path,
) -> None:
    resources = image_pipeline_postgres
    insert_owned_image_context(resources)
    database = SqlAlchemyDatabase(SecretStr(resources.database_url))
    repository = SqlAlchemyGeneratedImageRepository(database)
    private_root = tmp_path / "private-image-storage"
    storage_adapter = LocalPrivateImageStorage(private_root)
    storage = GeneratedImageStorageService(
        validator=GeneratedImageValidationService(
            ImageStorageConfiguration(
                local_root=private_root,
                max_file_bytes=1_048_576,
            )
        ),
        storage=storage_adapter,
        repository=repository,
        clock=lambda: NOW,
    )
    delivery = ImageDeliveryService(images=repository, storage=storage_adapter)

    parent = run(
        storage.store(
            GeneratedImageStorageRequest(
                owner_id=OWNER_ID,
                article_id=ARTICLE_ID,
                generated_post_id=POST_ID,
                generation_run_id=PARENT_RUN_ID,
                result=generated_result(
                    request_id=PARENT_REQUEST_ID,
                    image_bytes=image_workflow_files.valid_png.read_bytes(),
                ),
                output_safety_status=ImageSafetyReviewStatus.APPROVED,
            )
        )
    )
    child = run(
        storage.store(
            GeneratedImageStorageRequest(
                owner_id=OWNER_ID,
                article_id=ARTICLE_ID,
                generated_post_id=POST_ID,
                generation_run_id=CHILD_RUN_ID,
                parent_image_id=parent.id,
                result=generated_result(
                    request_id=CHILD_REQUEST_ID,
                    image_bytes=image_workflow_files.alternate_png.read_bytes(),
                ),
                output_safety_status=ImageSafetyReviewStatus.PENDING,
            )
        )
    )

    parent_delivery = run(delivery.get_content(owner_id=OWNER_ID, image_id=parent.id))
    child_delivery = run(delivery.get_content(owner_id=OWNER_ID, image_id=child.id))
    foreign = run(repository.get_for_owner(image_id=parent.id, owner_id=OTHER_OWNER_ID))
    with resources.engine.connect() as connection:
        rows = (
            connection.execute(
                sa.text(
                    """
                SELECT id, parent_image_id, regeneration_sequence, ai_generated,
                       ai_disclosure_required, storage_key
                FROM generated_images
                ORDER BY regeneration_sequence
                """
                )
            )
            .mappings()
            .all()
        )

    assert parent_delivery.metadata.image_id == parent.id
    assert child_delivery.metadata.parent_image_id == parent.id
    assert parent_delivery.content != child_delivery.content
    assert parent.regeneration_sequence == 0
    assert child.regeneration_sequence == 1
    assert foreign is None
    assert len(rows) == 2
    assert rows[0]["parent_image_id"] is None
    assert rows[1]["parent_image_id"] == parent.id
    assert all(row["ai_generated"] for row in rows)
    assert all(row["ai_disclosure_required"] for row in rows)
    assert all(not Path(row["storage_key"]).is_absolute() for row in rows)
    assert len(list((private_root / "generated-images").iterdir())) == 2

    run(database.close())
