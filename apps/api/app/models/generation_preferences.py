"""Validated LinkedIn generation preferences and prompt metadata."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models.ai import AITextGenerationRequest


class LinkedInTone(str, Enum):
    """Supported application-owned writing styles."""

    PROFESSIONAL = "professional"
    CONVERSATIONAL = "conversational"
    ANALYTICAL = "analytical"


class LinkedInPostLength(str, Enum):
    """Supported bounded draft lengths."""

    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class LinkedInGenerationPreferences(BaseModel):
    """Strict user choices converted into trusted application constants."""

    tone: LinkedInTone = LinkedInTone.PROFESSIONAL
    post_length: LinkedInPostLength = LinkedInPostLength.MEDIUM

    model_config = ConfigDict(extra="forbid", frozen=True)


class LinkedInArticleReference(BaseModel):
    """Exact approved source reference kept outside generated prose."""

    article_id: UUID
    source_item_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    source_name: str = Field(min_length=1, max_length=200)
    publication_date: datetime
    canonical_url: HttpUrl
    attribution_text: str = Field(min_length=1, max_length=500)
    rights_version_id: UUID

    @field_validator("publication_date")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("publication_date must include a timezone.")
        return value

    model_config = ConfigDict(extra="forbid", frozen=True)


class LinkedInPromptPackage(BaseModel):
    """Prompt request and auditable non-generated metadata for one article."""

    prompt_version: str = Field(pattern=r"^linkedin_post_v[1-9][0-9]*$")
    preferences: LinkedInGenerationPreferences
    included_source_fields: tuple[str, ...]
    article_reference: LinkedInArticleReference
    generation_request: AITextGenerationRequest

    model_config = ConfigDict(extra="forbid", frozen=True)
