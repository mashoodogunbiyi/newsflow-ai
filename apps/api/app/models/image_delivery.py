"""Public metadata and private content models for generated-image delivery."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.generated_image import (
    ImageSafetyReviewStatus,
    ImageValidationStatus,
    StoredGeneratedImageRecord,
)


class ImageMetadataResponse(BaseModel):
    """Safe image metadata that excludes private storage implementation details."""

    image_id: UUID
    generation_id: UUID
    generated_post_id: UUID
    article_id: UUID
    parent_image_id: UUID | None
    regeneration_sequence: int = Field(ge=0)
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    file_size_bytes: int = Field(gt=0)
    model_identifier: str
    prompt_version: str
    safety_policy_version: str
    safety_status: ImageSafetyReviewStatus
    validation_status: ImageValidationStatus
    generation_status: Literal["completed"]
    is_ai_generated: Literal[True]
    ai_disclosure_required: Literal[True]
    created_at: datetime

    @classmethod
    def from_record(
        cls,
        record: StoredGeneratedImageRecord,
    ) -> "ImageMetadataResponse":
        """Map an internal record without exposing its provider, key, or digest."""

        return cls(
            image_id=record.id,
            generation_id=record.generation_run_id,
            generated_post_id=record.generated_post_id,
            article_id=record.article_id,
            parent_image_id=record.parent_image_id,
            regeneration_sequence=record.regeneration_sequence,
            mime_type=record.mime_type,
            width=record.width,
            height=record.height,
            file_size_bytes=record.file_size_bytes,
            model_identifier=record.model_identifier,
            prompt_version=record.prompt_version,
            safety_policy_version=record.safety_policy_version,
            safety_status=record.safety_status,
            validation_status=record.validation_status,
            generation_status=record.generation_status,
            is_ai_generated=record.ai_generated,
            ai_disclosure_required=record.ai_disclosure_required,
            created_at=record.created_at,
        )

    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(frozen=True, slots=True)
class PrivateImageDelivery:
    """Authorised image bytes and safe response metadata for backend delivery."""

    metadata: ImageMetadataResponse
    content: bytes = field(repr=False)
    download_filename: str
