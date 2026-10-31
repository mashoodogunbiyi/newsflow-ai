"""Validate, privately store, and persist generated-image metadata."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from app.core.logging_config import log_event
from app.models.generated_image import (
    GeneratedImageStorageRequest,
    GeneratedImageWrite,
    ImageSafetyReviewStatus,
    StoredGeneratedImage,
)
from app.models.image_generation import ImageDataReferenceKind
from app.repositories.generated_images import GeneratedImageRepository
from app.services.image_storage import PrivateImageStorage, PrivateImageStorageError
from app.services.image_validation import GeneratedImageValidationService

logger = logging.getLogger(__name__)


class GeneratedImageStorageWorkflowError(RuntimeError):
    """Safe storage-workflow failure with a stable code."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.safe_message = message
        super().__init__(message)


class GeneratedImageStorageService:
    """Coordinate validation, storage, persistence, idempotency, and cleanup."""

    def __init__(
        self,
        *,
        validator: GeneratedImageValidationService,
        storage: PrivateImageStorage,
        repository: GeneratedImageRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._validator = validator
        self._storage = storage
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))

    async def store(
        self,
        request: GeneratedImageStorageRequest,
    ) -> StoredGeneratedImage:
        """Store one safe private image and return no private location details."""

        if request.output_safety_status == ImageSafetyReviewStatus.BLOCKED:
            raise GeneratedImageStorageWorkflowError(
                code="image_output_safety_blocked",
                message="Generated image was blocked by output safety review.",
            )

        image_bytes = self._image_bytes(request)
        reference = request.result.image_data_reference
        if (
            reference.byte_length is not None
            and len(image_bytes) != reference.byte_length
        ):
            raise GeneratedImageStorageWorkflowError(
                code="image_provider_length_mismatch",
                message="Generated image data does not match provider metadata.",
            )

        expected_width, expected_height = (
            int(part) for part in request.result.size.value.split("x", maxsplit=1)
        )
        validated = self._validator.validate(
            image_bytes,
            expected_media_type=reference.media_type,
            expected_dimensions=(expected_width, expected_height),
        )
        if reference.sha256 is not None:
            import hashlib

            if hashlib.sha256(image_bytes).hexdigest() != reference.sha256:
                raise GeneratedImageStorageWorkflowError(
                    code="image_provider_digest_mismatch",
                    message="Generated image data does not match provider metadata.",
                )

        existing = await self._repository.get_by_request_id(
            request_id=request.result.request_id
        )
        if existing is not None:
            self._require_matching_retry(request, validated.sha256, existing)
            return StoredGeneratedImage.from_record(existing)

        try:
            stored_object = await self._storage.put(
                validated.data.get_secret_value(),
                file_extension=validated.file_extension,
            )
        except PrivateImageStorageError as exc:
            raise GeneratedImageStorageWorkflowError(
                code="image_private_storage_failed",
                message="Generated image could not be stored safely.",
            ) from exc

        proposed = GeneratedImageWrite(
            id=uuid4(),
            request_id=request.result.request_id,
            owner_id=request.owner_id,
            article_id=request.article_id,
            generated_post_id=request.generated_post_id,
            source_post_version_id=request.source_post_version_id,
            generation_run_id=request.generation_run_id,
            parent_image_id=request.parent_image_id,
            storage_provider=stored_object.provider,
            storage_key=stored_object.storage_key,
            mime_type=validated.mime_type,
            file_size_bytes=validated.file_size_bytes,
            width=validated.width,
            height=validated.height,
            content_sha256=validated.sha256,
            model_identifier=request.result.model_identifier,
            prompt_version=request.result.prompt_version,
            safety_policy_version=request.result.safety_policy_version,
            safety_status=request.output_safety_status,
            created_at=self._clock(),
        )
        try:
            persistence = await self._repository.save(proposed)
        except BaseException:
            await self._compensate(stored_object.storage_key.get_secret_value())
            raise

        if not persistence.created:
            await self._compensate(stored_object.storage_key.get_secret_value())

        log_event(
            logger,
            logging.INFO,
            "generated_image_stored",
            image_id=str(persistence.record.id),
            request_id=str(persistence.record.request_id),
            owner_id=str(persistence.record.owner_id),
            article_id=str(persistence.record.article_id),
            generation_run_id=str(persistence.record.generation_run_id),
            status=persistence.record.generation_status,
            validation_status=persistence.record.validation_status.value,
            safety_status=persistence.record.safety_status.value,
        )
        return StoredGeneratedImage.from_record(persistence.record)

    @staticmethod
    def _image_bytes(request: GeneratedImageStorageRequest) -> bytes:
        if request.retrieved_image_bytes is not None:
            return request.retrieved_image_bytes.get_secret_value()
        reference = request.result.image_data_reference
        if (
            reference.kind == ImageDataReferenceKind.INLINE_BYTES
            and reference.data is not None
        ):
            return reference.data.get_secret_value()
        raise GeneratedImageStorageWorkflowError(
            code="image_bytes_unavailable",
            message=(
                "Generated image bytes must be retrieved through an approved "
                "bounded downloader before storage."
            ),
        )

    @staticmethod
    def _require_matching_retry(request, content_sha256: str, existing) -> None:
        if not (
            existing.owner_id == request.owner_id
            and existing.article_id == request.article_id
            and existing.generated_post_id == request.generated_post_id
            and existing.generation_run_id == request.generation_run_id
            and existing.source_post_version_id == request.source_post_version_id
            and existing.parent_image_id == request.parent_image_id
            and existing.content_sha256 == content_sha256
        ):
            raise GeneratedImageStorageWorkflowError(
                code="image_storage_idempotency_conflict",
                message="The image request identifier has already been used.",
            )

    async def _compensate(self, storage_key: str) -> None:
        try:
            await self._storage.delete(storage_key)
        except PrivateImageStorageError:
            log_event(
                logger,
                logging.ERROR,
                "generated_image_cleanup_failed",
                status="orphan_reconciliation_required",
            )
