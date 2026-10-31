"""NFA-51 private storage, persistence, retry, and cleanup tests."""

import asyncio
import hashlib
import io
import stat
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from PIL import Image
from pydantic import SecretBytes

from app.core.image_storage_config import ImageStorageConfiguration
from app.models.generated_image import (
    GeneratedImagePersistenceResult,
    GeneratedImageStorageRequest,
    ImageSafetyReviewStatus,
    StoredGeneratedImageRecord,
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
from app.services.generated_image_storage import (
    GeneratedImageStorageService,
    GeneratedImageStorageWorkflowError,
)
from app.services.image_storage import (
    LocalPrivateImageStorage,
    PrivateImageStorageError,
)
from app.services.image_validation import GeneratedImageValidationService

OWNER_ID = UUID("51000000-0000-4000-8000-000000000001")
ARTICLE_ID = UUID("51000000-0000-4000-8000-000000000002")
ARTICLE_SNAPSHOT_ID = UUID("51000000-0000-4000-8000-000000000003")
POST_ID = UUID("51000000-0000-4000-8000-000000000004")
RUN_ID = UUID("51000000-0000-4000-8000-000000000005")
REQUEST_ID = UUID("51000000-0000-4000-8000-000000000006")
SAFETY_ID = UUID("51000000-0000-4000-8000-000000000007")
RIGHTS_ID = UUID("51000000-0000-4000-8000-000000000008")
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def run(coroutine):
    return asyncio.run(coroutine)


def square_png() -> bytes:
    image = Image.new("RGB", (1024, 1024), color=(13, 82, 116))
    output = io.BytesIO()
    image.save(output, format="PNG")
    image.close()
    return output.getvalue()


def generation_result(image_bytes: bytes) -> OpenAIImageGenerationResult:
    return OpenAIImageGenerationResult(
        request_id=REQUEST_ID,
        model_identifier="gpt-image-2.5-flare",
        image_data_reference=GeneratedImageDataReference(
            kind=ImageDataReferenceKind.INLINE_BYTES,
            media_type="image/png",
            data=SecretBytes(image_bytes),
            byte_length=len(image_bytes),
            sha256=hashlib.sha256(image_bytes).hexdigest(),
        ),
        usage_metadata=ImageGenerationUsage(total_tokens=10),
        provider_request_id="provider-image-request",
        prompt_version="image_prompt_v1",
        safety_policy_version="image_safety_v1",
        safety_evaluation_id=SAFETY_ID,
        rights_version_id=RIGHTS_ID,
        size=ImageGenerationSize.SQUARE,
        quality=ImageGenerationQuality.MEDIUM,
        output_format=ImageOutputFormat.PNG,
        created_at=NOW,
    )


def storage_request(
    image_bytes: bytes,
    *,
    safety_status: ImageSafetyReviewStatus = ImageSafetyReviewStatus.PENDING,
) -> GeneratedImageStorageRequest:
    return GeneratedImageStorageRequest(
        owner_id=OWNER_ID,
        article_id=ARTICLE_ID,
        generated_post_id=POST_ID,
        generation_run_id=RUN_ID,
        result=generation_result(image_bytes),
        output_safety_status=safety_status,
    )


class MemoryRepository:
    def __init__(self) -> None:
        self.record: StoredGeneratedImageRecord | None = None
        self.save_calls = 0

    async def get_by_request_id(
        self,
        *,
        request_id: UUID,
    ) -> StoredGeneratedImageRecord | None:
        if self.record is not None and self.record.request_id == request_id:
            return self.record
        return None

    async def save(self, image) -> GeneratedImagePersistenceResult:
        self.save_calls += 1
        if self.record is not None:
            return GeneratedImagePersistenceResult(record=self.record, created=False)
        self.record = StoredGeneratedImageRecord(
            **image.model_dump(exclude={"regeneration_sequence"}),
            article_snapshot_id=ARTICLE_SNAPSHOT_ID,
            regeneration_sequence=0,
        )
        return GeneratedImagePersistenceResult(record=self.record, created=True)


class FailingRepository(MemoryRepository):
    async def save(self, image) -> GeneratedImagePersistenceResult:
        raise RuntimeError("synthetic database failure")


class FailingStorage:
    async def put(self, data: bytes, *, file_extension: str):
        raise PrivateImageStorageError("synthetic storage failure")

    async def delete(self, storage_key: str) -> None:
        raise AssertionError("Nothing should be deleted after a failed upload.")

    async def read(self, storage_key: str) -> bytes:
        raise AssertionError("Not used.")


def service(root: Path, repository) -> GeneratedImageStorageService:
    configuration = ImageStorageConfiguration(local_root=root)
    return GeneratedImageStorageService(
        validator=GeneratedImageValidationService(configuration),
        storage=LocalPrivateImageStorage(root),
        repository=repository,
        clock=lambda: NOW,
    )


def test_local_private_storage_uses_unpredictable_keys_and_restrictive_permissions(
    tmp_path: Path,
) -> None:
    storage = LocalPrivateImageStorage(tmp_path / "private")

    first = run(storage.put(b"first", file_extension="png"))
    second = run(storage.put(b"second", file_extension="png"))

    first_key = first.storage_key.get_secret_value()
    second_key = second.storage_key.get_secret_value()
    assert first_key.startswith("generated-images/")
    assert first_key != second_key
    assert "first" not in first_key
    assert run(storage.read(first_key)) == b"first"
    stored_path = tmp_path / "private" / first_key
    assert stat.S_IMODE(stored_path.stat().st_mode) == 0o600
    assert not hasattr(first, "public_url")


def test_successful_workflow_persists_ownership_provenance_and_ai_metadata(
    tmp_path: Path,
) -> None:
    repository = MemoryRepository()
    image = run(service(tmp_path, repository).store(storage_request(square_png())))

    assert image.owner_id == OWNER_ID
    assert image.article_id == ARTICLE_ID
    assert image.generated_post_id == POST_ID
    assert image.generation_run_id == RUN_ID
    assert image.safety_status == ImageSafetyReviewStatus.PENDING
    assert image.ai_generated is True
    assert image.ai_disclosure_required is True
    assert image.model_identifier == "gpt-image-2.5-flare"
    assert image.prompt_version == "image_prompt_v1"
    assert repository.record is not None
    assert repository.record.article_snapshot_id == ARTICLE_SNAPSHOT_ID
    assert "storage_key" not in image.model_dump()


def test_retry_returns_existing_record_without_duplicate_file(
    tmp_path: Path,
) -> None:
    repository = MemoryRepository()
    selected_service = service(tmp_path, repository)
    request = storage_request(square_png())

    first = run(selected_service.store(request))
    second = run(selected_service.store(request))

    assert second.id == first.id
    assert repository.save_calls == 1
    assert len(list(tmp_path.glob("generated-images/*"))) == 1


def test_database_failure_removes_uploaded_file(tmp_path: Path) -> None:
    selected_service = service(tmp_path, FailingRepository())

    with pytest.raises(RuntimeError, match="synthetic database failure"):
        run(selected_service.store(storage_request(square_png())))

    assert list(tmp_path.glob("generated-images/*")) == []


def test_storage_failure_does_not_create_false_database_success(tmp_path: Path) -> None:
    repository = MemoryRepository()
    configuration = ImageStorageConfiguration(local_root=tmp_path)
    selected_service = GeneratedImageStorageService(
        validator=GeneratedImageValidationService(configuration),
        storage=FailingStorage(),
        repository=repository,
    )

    with pytest.raises(GeneratedImageStorageWorkflowError) as error:
        run(selected_service.store(storage_request(square_png())))

    assert error.value.code == "image_private_storage_failed"
    assert repository.save_calls == 0


def test_blocked_output_is_rejected_before_validation_or_storage(
    tmp_path: Path,
) -> None:
    repository = MemoryRepository()

    with pytest.raises(GeneratedImageStorageWorkflowError) as error:
        run(
            service(tmp_path, repository).store(
                storage_request(
                    square_png(),
                    safety_status=ImageSafetyReviewStatus.BLOCKED,
                )
            )
        )

    assert error.value.code == "image_output_safety_blocked"
    assert repository.save_calls == 0
    assert list(tmp_path.glob("generated-images/*")) == []


def test_provider_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    image_bytes = square_png()
    request = storage_request(image_bytes)
    invalid_result = request.result.model_copy(
        update={
            "image_data_reference": request.result.image_data_reference.model_copy(
                update={"sha256": "0" * 64}
            )
        }
    )

    with pytest.raises(GeneratedImageStorageWorkflowError) as error:
        run(
            service(tmp_path, MemoryRepository()).store(
                request.model_copy(update={"result": invalid_result})
            )
        )

    assert error.value.code == "image_provider_digest_mismatch"
