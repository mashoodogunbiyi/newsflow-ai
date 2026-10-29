"""Provider-neutral models for permitted news information."""

import html
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")
HTML_TAG_PATTERN = re.compile(r"<\s*/?\s*[A-Za-z]")


def _normalise_plain_text(value: object) -> object:
    """Trim and normalise provider text while rejecting executable markup."""

    if not isinstance(value, str):
        return value
    cleaned = unicodedata.normalize("NFC", html.unescape(value)).strip()
    if HTML_TAG_PATTERN.search(cleaned):
        raise ValueError("Provider text must be plain text.")
    if any(
        unicodedata.category(character) == "Cc" and character not in {"\n", "\r", "\t"}
        for character in cleaned
    ):
        raise ValueError("Provider text contains unsupported control characters.")
    return cleaned


def _require_aware_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone.")
    return value.astimezone(timezone.utc)


def _require_safe_https_url(value: HttpUrl) -> HttpUrl:
    if value.scheme != "https":
        raise ValueError("Source URLs must use HTTPS.")
    if value.username is not None or value.password is not None:
        raise ValueError("Source URLs must not contain credentials.")
    if value.fragment is not None:
        raise ValueError("Source URLs must not contain a fragment.")
    return value


class ArticleCategory(str, Enum):
    """Categories approved by the NFA-6 source data contract."""

    TECHNOLOGY = "Technology"
    BUSINESS = "Business"
    WORLD_NEWS = "World News"
    SCIENCE = "Science"
    OTHER = "Other"


class ContentStatus(str, Enum):
    """Availability and permission state for article content."""

    AVAILABLE = "available"
    MISSING = "missing"
    NOT_PERMITTED = "not_permitted"


class ContentType(str, Enum):
    """Permitted content types in contract version 1.0."""

    SYNTHETIC = "synthetic"
    PROVIDER_DESCRIPTION = "provider_description"
    LICENSED_ARTICLE_TEXT = "licensed_article_text"
    NONE = "none"


class AccessMethod(str, Enum):
    """Currently approved source access methods."""

    FIXTURE = "fixture"


class ContractModel(BaseModel):
    """Strict immutable base for source-contract values."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class PermittedContent(ContractModel):
    """Content and explicit permission flags supplied by a provider."""

    status: ContentStatus
    content_type: ContentType
    text: str | None = Field(max_length=20_000)
    ai_processing_allowed: bool
    derivative_output_allowed: bool

    _clean_text = field_validator("text", mode="before")(_normalise_plain_text)

    @model_validator(mode="after")
    def validate_content_state(self) -> "PermittedContent":
        if self.status == ContentStatus.AVAILABLE:
            if self.content_type == ContentType.NONE or not self.text:
                raise ValueError("Available content requires a permitted text value.")
        elif self.content_type != ContentType.NONE or self.text is not None:
            raise ValueError("Missing or restricted content must not include text.")

        if self.status == ContentStatus.NOT_PERMITTED and (
            self.ai_processing_allowed or self.derivative_output_allowed
        ):
            raise ValueError("Restricted content cannot allow AI or derivative use.")
        return self


class Attribution(ContractModel):
    """Source wording that must accompany displayed or generated content."""

    display_name: str = Field(min_length=1, max_length=200)
    canonical_url: HttpUrl
    attribution_text: str = Field(min_length=1, max_length=500)
    byline: str | None = Field(max_length=300)
    copyright_notice: str | None = Field(max_length=500)

    _clean_text = field_validator(
        "display_name",
        "attribution_text",
        "byline",
        "copyright_notice",
        mode="before",
    )(_normalise_plain_text)
    _safe_url = field_validator("canonical_url")(_require_safe_https_url)


class RightsMetadata(ContractModel):
    """Recorded decision controlling storage and display."""

    decision_id: str = Field(min_length=1, max_length=200)
    access_method: AccessMethod
    storage_allowed: bool
    display_allowed: bool
    expires_at: datetime | None
    retention_rule: str = Field(min_length=1, max_length=200)

    _clean_text = field_validator("decision_id", "retention_rule", mode="before")(
        _normalise_plain_text
    )

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _require_aware_datetime(value, "expires_at")


class NewsArticle(ContractModel):
    """Provider-neutral NFA-6 article contract used by application code."""

    contract_version: Literal["1.0"]
    source_profile: Literal["fixture-v1"]
    source_item_id: str = Field(min_length=1, max_length=200)
    source_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    publication_date: datetime
    category: ArticleCategory
    description: str | None = Field(max_length=1_000)
    url: HttpUrl
    permitted_content: PermittedContent
    attribution: Attribution
    rights: RightsMetadata
    retrieved_at: datetime
    modified_at: datetime | None

    _clean_text = field_validator(
        "source_item_id",
        "source_name",
        "title",
        "description",
        mode="before",
    )(_normalise_plain_text)
    _safe_url = field_validator("url")(_require_safe_https_url)

    @field_validator("description", mode="before")
    @classmethod
    def blank_description_is_missing(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("source_item_id")
    @classmethod
    def validate_source_item_id(cls, value: str) -> str:
        if not SOURCE_ID_PATTERN.fullmatch(value):
            raise ValueError("Source identifiers contain unsupported characters.")
        return value

    @field_validator("publication_date", "retrieved_at", "modified_at")
    @classmethod
    def validate_timestamps(
        cls, value: datetime | None, info: object
    ) -> datetime | None:
        if value is None:
            return None
        field_name = getattr(info, "field_name", "timestamp")
        return _require_aware_datetime(value, field_name)

    @model_validator(mode="after")
    def validate_contract_relationships(self) -> "NewsArticle":
        if not self.source_item_id.startswith("fixture-"):
            raise ValueError("Fixture identifiers must start with 'fixture-'.")
        if str(self.attribution.canonical_url) != str(self.url):
            raise ValueError("Attribution URL must match the canonical article URL.")
        if self.publication_date > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Publication date is unreasonably far in the future.")
        if self.retrieved_at < self.publication_date:
            raise ValueError("Retrieval time cannot precede publication time.")
        if self.modified_at is not None and self.modified_at < self.publication_date:
            raise ValueError("Modification time cannot precede publication time.")
        return self


class ArticleQuery(ContractModel):
    """Provider-neutral discovery request."""

    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, min_length=1, max_length=512)
    published_after: datetime | None = None

    @field_validator("published_after")
    @classmethod
    def validate_published_after(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _require_aware_datetime(value, "published_after")


class ProviderCapabilities(ContractModel):
    """Features callers can safely request from a provider."""

    pagination: bool
    incremental_retrieval: bool


class ProviderPage(ContractModel):
    """One normalised page returned by any compliant provider."""

    provider_id: str = Field(min_length=1, max_length=100)
    items: tuple[NewsArticle, ...]
    next_cursor: str | None = Field(default=None, max_length=512)
    capabilities: ProviderCapabilities
