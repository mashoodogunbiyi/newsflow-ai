"""Validated requests and safe responses for the private content library."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_optional_title(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    return cleaned or None


class SaveContentRequest(BaseModel):
    """References required to save an owned generated post."""

    generated_post_id: UUID
    selected_post_version_id: UUID
    selected_image_id: UUID | None = None
    library_title: str | None = Field(default=None, max_length=200)

    _strip_title = field_validator("library_title", mode="before")(
        _clean_optional_title
    )

    model_config = ConfigDict(extra="forbid")


class UpdateSavedContentRequest(BaseModel):
    """Editable fields for an existing private content-library item."""

    library_title: str | None = Field(max_length=200)

    _strip_title = field_validator("library_title", mode="before")(
        _clean_optional_title
    )

    model_config = ConfigDict(extra="forbid")


class SavedContentResponse(BaseModel):
    """A saved item with no internal ownership or storage fields exposed."""

    id: UUID
    generated_post_id: UUID
    selected_post_version_id: UUID
    selected_image_id: UUID | None
    library_title: str | None
    rendered_text: str
    source_attribution: str
    saved_at: datetime
    updated_at: datetime


class SavedContentCollectionResponse(BaseModel):
    """Only the authenticated user's visible saved items."""

    items: list[SavedContentResponse]
