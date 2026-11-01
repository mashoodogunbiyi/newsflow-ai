"""Validated contracts for saving and updating private LinkedIn drafts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


def _clean_title(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    return cleaned or None


def _validate_edited_text(value: str) -> str:
    if not value.strip():
        raise ValueError("Draft text must contain visible characters.")
    if "\x00" in value:
        raise ValueError("Draft text contains an unsupported character.")
    return value


class CreateSavedDraftRequest(BaseModel):
    """Complete state required for the first durable save."""

    generation_id: UUID
    title: str | None = Field(default=None, max_length=200)
    edited_text: str = Field(min_length=1, max_length=12_000)
    selected_image_id: UUID | None = None

    _strip_title = field_validator("title", mode="before")(_clean_title)
    _check_text = field_validator("edited_text")(_validate_edited_text)

    model_config = ConfigDict(extra="forbid")


class UpdateSavedDraftRequest(BaseModel):
    """Complete editable state plus the version the client last read."""

    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=200)
    edited_text: str = Field(min_length=1, max_length=12_000)
    selected_image_id: UUID | None = None

    _strip_title = field_validator("title", mode="before")(_clean_title)
    _check_text = field_validator("edited_text")(_validate_edited_text)

    model_config = ConfigDict(extra="forbid")


class SavedDraftSourceResponse(BaseModel):
    """Permitted source reference retained by a saved draft."""

    article_id: UUID
    title: str
    url: HttpUrl
    attribution: str


class SavedDraftGenerationResponse(BaseModel):
    """Non-secret metadata for the AI generation that started the draft."""

    generation_id: UUID
    original_post_version_id: UUID
    model_identifier: str
    prompt_version: str
    created_at: datetime


class SavedDraftResponse(BaseModel):
    """Owner-safe saved-draft representation returned to the frontend."""

    id: UUID
    generated_post_id: UUID
    current_post_version_id: UUID
    selected_image_id: UUID | None
    title: str | None
    edited_text: str
    tone: str
    length: str
    status: Literal["saved"]
    version: int
    source: SavedDraftSourceResponse
    generation: SavedDraftGenerationResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(extra="forbid")
