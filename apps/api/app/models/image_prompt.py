"""Validated preferences and structured results for safe image prompts."""

from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr


class IllustrationStyle(str, Enum):
    """Application-owned illustration styles available to users."""

    EDITORIAL_ILLUSTRATION = "editorial_illustration"
    MINIMALIST_ILLUSTRATION = "minimalist_illustration"
    ABSTRACT_TECHNOLOGY = "abstract_technology"
    PROFESSIONAL_INFOGRAPHIC_STYLE = "professional_infographic_style"


class ImageAspectRatio(str, Enum):
    """Supported output shapes expressed without provider-specific dimensions."""

    LANDSCAPE = "landscape"
    SQUARE = "square"
    PORTRAIT = "portrait"


class ImageComposition(str, Enum):
    """Safe, bounded layout choices for later frontend controls."""

    BALANCED = "balanced"
    FOCAL_POINT_LEFT = "focal_point_left"
    FOCAL_POINT_RIGHT = "focal_point_right"


class ImagePromptContextKind(str, Enum):
    """Approved context types accepted by the composer."""

    ARTICLE = "article"
    LINKEDIN_DRAFT = "linkedin_draft"


class ImagePromptRequest(BaseModel):
    """Strict internal request containing only controlled user selections."""

    article_id: UUID
    generation_id: UUID | None = None
    style: IllustrationStyle
    aspect_ratio: ImageAspectRatio
    composition: ImageComposition = ImageComposition.BALANCED

    model_config = ConfigDict(extra="forbid", frozen=True)


class ImagePromptSourceReference(BaseModel):
    """Approved source metadata retained outside the image-model prompt."""

    article_id: UUID
    title: str = Field(min_length=1, max_length=300)
    source_name: str = Field(min_length=1, max_length=200)
    canonical_url: HttpUrl
    attribution_text: str = Field(min_length=1, max_length=500)
    rights_version_id: UUID

    model_config = ConfigDict(extra="forbid", frozen=True)


class ImagePromptResult(BaseModel):
    """Versioned prompt parts and non-generated audit metadata."""

    prompt_version: str = Field(pattern=r"^image_prompt_v[1-9][0-9]*$")
    context_kind: ImagePromptContextKind
    generation_id: UUID | None = None
    preferences: ImagePromptRequest
    included_source_fields: tuple[str, ...]
    included_derived_fields: tuple[str, ...] = ()
    source_reference: ImagePromptSourceReference
    trusted_instructions: SecretStr
    untrusted_context: SecretStr
    human_review_required: Literal[True] = True
    documentary_use_allowed: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)
