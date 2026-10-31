"""Owner-scoped retrieval and integrity checks for private generated images."""

import hashlib
import hmac
import logging
from uuid import UUID

from app.core.logging_config import log_event
from app.models.image_delivery import ImageMetadataResponse, PrivateImageDelivery
from app.repositories.generated_images import GeneratedImageRepository
from app.services import require_owned_resource
from app.services.image_storage import (
    PrivateImageObjectNotFoundError,
    PrivateImageStorage,
    PrivateImageStorageError,
)

logger = logging.getLogger(__name__)

_FILE_EXTENSION = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


class ImageContentUnavailableError(RuntimeError):
    """Raised when an authorised image cannot be delivered safely."""


class ImageDeliveryService:
    """Retrieve only owner-scoped records and backend-private image objects."""

    def __init__(
        self,
        *,
        images: GeneratedImageRepository,
        storage: PrivateImageStorage,
    ) -> None:
        self._images = images
        self._storage = storage

    async def get_metadata(
        self,
        *,
        owner_id: UUID,
        image_id: UUID,
    ) -> ImageMetadataResponse:
        """Return safe metadata for an image owned by the active user."""

        record = require_owned_resource(
            await self._images.get_for_owner(
                image_id=image_id,
                owner_id=owner_id,
            )
        )
        return ImageMetadataResponse.from_record(record)

    async def get_content(
        self,
        *,
        owner_id: UUID,
        image_id: UUID,
    ) -> PrivateImageDelivery:
        """Read and integrity-check one already-authorised private object."""

        record = require_owned_resource(
            await self._images.get_for_owner(
                image_id=image_id,
                owner_id=owner_id,
            )
        )
        try:
            content = await self._storage.read(record.storage_key.get_secret_value())
        except PrivateImageObjectNotFoundError as exc:
            self._record_failure(
                event="generated_image_delivery_missing_object",
                request_id=record.request_id,
                error_code="image_content_unavailable",
            )
            raise ImageContentUnavailableError(
                "The private image object is unavailable."
            ) from exc
        except PrivateImageStorageError as exc:
            self._record_failure(
                event="generated_image_delivery_storage_failed",
                request_id=record.request_id,
                error_code="image_content_unavailable",
            )
            raise ImageContentUnavailableError(
                "The private image object could not be read safely."
            ) from exc

        digest = hashlib.sha256(content).hexdigest()
        if len(content) != record.file_size_bytes or not hmac.compare_digest(
            digest,
            record.content_sha256,
        ):
            self._record_failure(
                event="generated_image_delivery_integrity_failed",
                request_id=record.request_id,
                error_code="image_content_integrity_failed",
            )
            raise ImageContentUnavailableError(
                "The private image object failed its integrity check."
            )

        metadata = ImageMetadataResponse.from_record(record)
        return PrivateImageDelivery(
            metadata=metadata,
            content=content,
            download_filename=(
                f"newsflow-ai-image-{record.id}.{_FILE_EXTENSION[record.mime_type]}"
            ),
        )

    @staticmethod
    def _record_failure(*, event: str, request_id: UUID, error_code: str) -> None:
        log_event(
            logger,
            logging.ERROR,
            event,
            request_id=str(request_id),
            error_code=error_code,
            status="unavailable",
        )
