"""Validated inputs and private metadata for generated-image persistence."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretBytes, SecretStr

from app.models.image_generation import OpenAIImageGenerationResult


class ImageSafetyReviewStatus(str, Enum):
    """Trusted output-safety result applied before an image is retained."""

    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"


class ImageValidationStatus(str, Enum):
    """Persisted validation outcomes for retained image records."""

    PASSED = "passed"


class GeneratedImageStatus(str, Enum):
    """Lifecycle state for a privately stored image."""

    AVAILABLE = "available"
    DELETED = "deleted"


class GeneratedImageStorageRequest(BaseModel):
    """Authenticated context and provider result required for secure storage."""

    owner_id: UUID
    article_id: UUID
    generated_post_id: UUID
    generation_run_id: UUID
    source_post_version_id: UUID | None = None
    parent_image_id: UUID | None = None
    result: OpenAIImageGenerationResult
    retrieved_image_bytes: SecretBytes | None = Field(default=None, repr=False)
    output_safety_status: ImageSafetyReviewStatus = ImageSafetyReviewStatus.PENDING

    model_config = ConfigDict(extra="forbid", frozen=True)


class ValidatedGeneratedImage(BaseModel):
    """Canonical image bytes and content-derived metadata after validation."""

    data: SecretBytes = Field(repr=False)
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    file_extension: Literal["png", "jpg", "webp"]
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    file_size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    metadata_removed: Literal[True] = True

    model_config = ConfigDict(extra="forbid", frozen=True)


class PrivateImageObject(BaseModel):
    """Internal reference to an object that is never exposed as a public URL."""

    provider: str = Field(min_length=1, max_length=50)
    storage_key: SecretStr = Field(repr=False)
    file_size_bytes: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid", frozen=True)


class GeneratedImageWrite(BaseModel):
    """Complete internal record proposed for PostgreSQL persistence."""

    id: UUID
    request_id: UUID
    owner_id: UUID
    article_id: UUID
    generated_post_id: UUID
    source_post_version_id: UUID | None = None
    generation_run_id: UUID
    parent_image_id: UUID | None = None
    regeneration_sequence: int | None = Field(default=None, ge=0)
    storage_provider: str
    storage_key: SecretStr = Field(repr=False)
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    file_size_bytes: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    model_identifier: str = Field(min_length=1, max_length=200)
    prompt_version: str = Field(pattern=r"^image_prompt_v[1-9][0-9]*$")
    safety_policy_version: str = Field(pattern=r"^image_safety_v[1-9][0-9]*$")
    safety_status: ImageSafetyReviewStatus
    validation_status: ImageValidationStatus = ImageValidationStatus.PASSED
    generation_status: Literal["completed"] = "completed"
    ai_generated: Literal[True] = True
    ai_disclosure_required: Literal[True] = True
    created_at: datetime

    model_config = ConfigDict(extra="forbid", frozen=True)


class StoredGeneratedImageRecord(GeneratedImageWrite):
    """Internal database record with its resolved article snapshot."""

    article_snapshot_id: UUID
    regeneration_sequence: int = Field(ge=0)


class GeneratedImagePersistenceResult(BaseModel):
    """Indicate whether this operation or an earlier retry created the row."""

    record: StoredGeneratedImageRecord
    created: bool

    model_config = ConfigDict(extra="forbid", frozen=True)


class StoredGeneratedImage(BaseModel):
    """Safe result without a private storage key or provider image bytes."""

    id: UUID
    request_id: UUID
    owner_id: UUID
    article_id: UUID
    generated_post_id: UUID
    generation_run_id: UUID
    parent_image_id: UUID | None
    regeneration_sequence: int
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    width: int
    height: int
    file_size_bytes: int
    model_identifier: str
    prompt_version: str
    safety_policy_version: str
    safety_status: ImageSafetyReviewStatus
    validation_status: ImageValidationStatus
    generation_status: Literal["completed"]
    ai_generated: Literal[True]
    ai_disclosure_required: Literal[True]
    created_at: datetime

    @classmethod
    def from_record(cls, record: StoredGeneratedImageRecord) -> "StoredGeneratedImage":
        """Remove storage internals from a persisted record."""

        return cls.model_validate(
            record.model_dump(
                exclude={
                    "storage_key",
                    "storage_provider",
                    "content_sha256",
                    "article_snapshot_id",
                    "source_post_version_id",
                }
            )
        )

    model_config = ConfigDict(extra="forbid", frozen=True)
