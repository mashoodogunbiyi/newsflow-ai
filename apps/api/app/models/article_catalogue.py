"""Validated query parameters and public article catalogue responses."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class ArticleCatalogueSort(str, Enum):
    """Supported stable catalogue orderings."""

    NEWEST = "newest"
    OLDEST = "oldest"


class ArticleCatalogueCategory(str, Enum):
    """Stable category identifiers approved by the source data contract."""

    TECHNOLOGY = "technology"
    BUSINESS = "business"
    WORLD_NEWS = "world_news"
    SCIENCE = "science"
    OTHER = "other"


class ArticleGenerationStatus(str, Enum):
    """Safe frontend state for the current article generation decision."""

    AVAILABLE = "available"
    RESTRICTED = "restricted"
    INSUFFICIENT_SOURCE_INFORMATION = "insufficient_source_information"


def _normalise_utc(value: datetime | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone.")
    return value.astimezone(UTC)


class ArticleCatalogueQuery(BaseModel):
    """Validated search, filter, ordering, and pagination parameters."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, min_length=1, max_length=512)
    search: str | None = Field(default=None, min_length=1, max_length=200)
    source_url: HttpUrl | None = Field(default=None, max_length=2048)
    category: ArticleCatalogueCategory | None = None
    provider: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )
    published_from: datetime | None = None
    published_to: datetime | None = None
    sort: ArticleCatalogueSort = ArticleCatalogueSort.NEWEST

    @field_validator("search", "provider", mode="before")
    @classmethod
    def reject_blank_filters(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("The filter cannot be blank.")
        return cleaned

    @field_validator("provider")
    @classmethod
    def normalise_provider(cls, value: str | None) -> str | None:
        return None if value is None else value.lower()

    @field_validator("published_from", "published_to")
    @classmethod
    def validate_dates(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        return _normalise_utc(value, getattr(info, "field_name", "published date"))

    @model_validator(mode="after")
    def validate_date_range(self) -> "ArticleCatalogueQuery":
        if (
            self.published_from is not None
            and self.published_to is not None
            and self.published_from > self.published_to
        ):
            raise ValueError("published_from cannot be later than published_to.")
        return self


class ArticleAttributionResponse(BaseModel):
    """Approved attribution that must accompany displayed metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    display_name: str
    text: str
    byline: str | None
    copyright_notice: str | None


class ArticleResponse(BaseModel):
    """Public article metadata with no internal rights or storage fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    title: str
    description: str | None
    source_url: HttpUrl
    provider: str
    published_at: datetime
    category: str
    attribution: ArticleAttributionResponse


class ArticleGenerationAvailabilityResponse(BaseModel):
    """Minimal current permission result without confidential rights details."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool
    status: ArticleGenerationStatus

    @model_validator(mode="after")
    def validate_allowed_status(self) -> "ArticleGenerationAvailabilityResponse":
        if self.allowed != (self.status == ArticleGenerationStatus.AVAILABLE):
            raise ValueError("Generation availability and status must agree.")
        return self


class ArticleDetailResponse(ArticleResponse):
    """Permitted article detail plus a safe current generation decision."""

    generation: ArticleGenerationAvailabilityResponse


class ArticleCollectionResponse(BaseModel):
    """One stable page of rights-approved article metadata."""

    model_config = ConfigDict(extra="forbid")

    items: list[ArticleResponse]
    next_cursor: str | None = None
