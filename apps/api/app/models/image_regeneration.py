"""Strict API contracts for private generated-image regeneration."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.generated_image import ImageSafetyReviewStatus
from app.models.image_prompt import (
    IllustrationStyle,
    ImageAspectRatio,
    ImageComposition,
)


class ImagePreferences(BaseModel):
    """Controlled creative choices accepted from an authenticated user."""

    style: IllustrationStyle
    aspect_ratio: ImageAspectRatio
    composition: ImageComposition = ImageComposition.BALANCED

    model_config = ConfigDict(extra="forbid", frozen=True)


class ImageCreationRequest(ImagePreferences):
    """Initial image request linked to one owner-scoped text generation."""

    generation_id: UUID


class ImageRegenerationRequest(ImagePreferences):
    """Controlled choices for a new version of an existing private image."""


class ImageCreationResponse(BaseModel):
    """Safe metadata for an initially generated private illustration."""

    image_id: UUID
    parent_image_id: Literal[None] = None
    generation_id: UUID
    generated_post_id: UUID
    regeneration_sequence: Literal[0] = 0
    status: Literal["completed"] = "completed"
    safety_status: ImageSafetyReviewStatus
    is_ai_generated: Literal[True] = True
    review_required: Literal[True] = True
    created_at: datetime

    model_config = ConfigDict(extra="forbid", frozen=True)


class ImageRegenerationResponse(BaseModel):
    """Safe metadata for one newly stored or idempotently replayed image."""

    image_id: UUID
    parent_image_id: UUID
    generation_id: UUID
    generated_post_id: UUID
    regeneration_sequence: int
    status: Literal["completed"] = "completed"
    safety_status: ImageSafetyReviewStatus
    is_ai_generated: Literal[True] = True
    review_required: Literal[True] = True
    created_at: datetime

    model_config = ConfigDict(extra="forbid", frozen=True)
