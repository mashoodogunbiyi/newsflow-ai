"""Validated API and persistence models for LinkedIn draft generation."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from app.models.ai import AITokenUsage
from app.models.generation_preferences import LinkedInPostLength, LinkedInTone


class LinkedInGenerationRequest(BaseModel):
    """Strict user-selectable inputs for one generation request."""

    article_id: UUID
    tone: LinkedInTone = LinkedInTone.PROFESSIONAL
    length: LinkedInPostLength = LinkedInPostLength.MEDIUM

    model_config = ConfigDict(extra="forbid")


class GenerationRequest(BaseModel):
    """Strict NFA-41 request requiring every user selection explicitly."""

    article_id: UUID
    tone: LinkedInTone
    length: LinkedInPostLength

    model_config = ConfigDict(extra="forbid")


class LinkedInModelOutput(BaseModel):
    """Exact JSON contract expected from the OpenAI response."""

    status: Literal["ready", "insufficient_source_information"]
    draft: str = Field(max_length=12_000)
    insufficiency_reason: str | None = Field(default=None, max_length=500)

    @field_validator("draft", "insufficiency_reason")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return None if value is None else value.strip()

    @model_validator(mode="after")
    def validate_status_fields(self) -> "LinkedInModelOutput":
        if self.status == "ready":
            if not self.draft:
                raise ValueError("A ready result requires a nonempty draft.")
            if self.insufficiency_reason is not None:
                raise ValueError(
                    "A ready result cannot include an insufficiency reason."
                )
        elif self.draft or not self.insufficiency_reason:
            raise ValueError(
                "An insufficient result requires an empty draft and a reason."
            )
        return self

    model_config = ConfigDict(extra="forbid", frozen=True)


class LinkedInDraftSourceReference(BaseModel):
    """Approved source reference preserved outside generated prose."""

    article_id: UUID
    title: str = Field(min_length=1, max_length=300)
    source_name: str = Field(min_length=1, max_length=200)
    source_url: HttpUrl
    attribution_text: str = Field(min_length=1, max_length=500)
    rights_version_id: UUID

    model_config = ConfigDict(extra="forbid", frozen=True)


class LinkedInDraft(BaseModel):
    """Private generated draft and non-sensitive audit metadata."""

    draft_id: UUID
    generation_id: UUID
    owner_id: UUID = Field(exclude=True)
    draft: str = Field(min_length=1, max_length=12_000)
    source: LinkedInDraftSourceReference
    tone: LinkedInTone
    length: LinkedInPostLength
    status: Literal["draft"] = "draft"
    review_required: Literal[True] = True
    prompt_version: str = Field(pattern=r"^linkedin_post_v[1-9][0-9]*$")
    model_identifier: str = Field(min_length=1, max_length=200)
    token_usage: AITokenUsage
    created_at: datetime

    model_config = ConfigDict(extra="forbid", frozen=True)


class LinkedInDraftResponse(BaseModel):
    """User-facing generation result with no owner or provider secrets."""

    draft_id: UUID
    generation_id: UUID
    draft: str
    source: LinkedInDraftSourceReference
    tone: LinkedInTone
    length: LinkedInPostLength
    status: Literal["draft"]
    review_required: Literal[True]
    prompt_version: str
    model_identifier: str
    token_usage: AITokenUsage
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class GenerationResponse(BaseModel):
    """Minimal frontend response without provider or rights internals."""

    generation_id: UUID
    article_id: UUID
    draft: str = Field(min_length=1, max_length=12_000)
    tone: LinkedInTone
    length: LinkedInPostLength
    source_title: str = Field(min_length=1, max_length=300)
    source_name: str = Field(min_length=1, max_length=200)
    source_url: HttpUrl
    source_attribution: str = Field(min_length=1, max_length=500)
    status: Literal["draft"]
    review_required: Literal[True]
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
