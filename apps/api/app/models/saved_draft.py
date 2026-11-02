"""Validated contracts for saving and updating private LinkedIn drafts."""

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


class PatchSavedDraftRequest(BaseModel):
    """Partial editable state plus the version the client last read."""

    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=200)
    edited_text: str | None = Field(default=None, min_length=1, max_length=12_000)
    selected_image_id: UUID | None = None

    _strip_title = field_validator("title", mode="before")(_clean_title)

    @field_validator("edited_text")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_edited_text(value)

    @model_validator(mode="after")
    def require_editable_change(self) -> "PatchSavedDraftRequest":
        editable_fields = {"title", "edited_text", "selected_image_id"}
        if not editable_fields.intersection(self.model_fields_set):
            raise ValueError("At least one editable draft field is required.")
        if "edited_text" in self.model_fields_set and self.edited_text is None:
            raise ValueError("Draft text cannot be null.")
        return self

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


class SavedDraftImageResponse(BaseModel):
    """Permitted image metadata without private storage information."""

    id: UUID
    alt_text: str | None
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)
    ai_generated: bool
    ai_disclosure_required: bool


class SavedDraftResponse(BaseModel):
    """Owner-safe saved-draft representation returned to the frontend."""

    id: UUID
    generated_post_id: UUID
    current_post_version_id: UUID
    selected_image_id: UUID | None
    selected_image: SavedDraftImageResponse | None
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


class SavedDraftCollectionResponse(BaseModel):
    """Bounded private content-library page in a documented sort order."""

    items: list[SavedDraftResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    sort: Literal["updated_at_desc"] = "updated_at_desc"

    model_config = ConfigDict(extra="forbid")


SavedDraftChangeType = Literal[
    "initial_save",
    "manual_edit",
    "text_regeneration",
    "image_selection",
    "image_regeneration",
    "metadata_update",
    "version_restoration",
]


class RestoreSavedDraftVersionRequest(BaseModel):
    """Optimistic concurrency input for a history restoration."""

    expected_version: int = Field(ge=1)

    model_config = ConfigDict(extra="forbid")


class SavedDraftVersionResponse(BaseModel):
    """Immutable historical state safe for the owning user."""

    id: UUID
    draft_id: UUID
    post_version_id: UUID
    selected_image_id: UUID | None
    selected_image: SavedDraftImageResponse | None
    generation_id: UUID | None
    restored_from_version_id: UUID | None
    version_number: int = Field(ge=1)
    change_type: SavedDraftChangeType
    title: str | None
    edited_text: str
    tone: str
    length: str
    source: SavedDraftSourceResponse
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class SavedDraftVersionCollectionResponse(BaseModel):
    """Bounded immutable history page in newest-first order."""

    items: list[SavedDraftVersionResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    sort: Literal["version_desc"] = "version_desc"

    model_config = ConfigDict(extra="forbid")
