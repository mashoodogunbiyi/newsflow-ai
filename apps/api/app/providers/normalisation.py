"""Rights-aware article normalisation before storage or application use."""

import html
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from urllib.parse import SplitResult, urlsplit, urlunsplit

from pydantic import ValidationError

from app.providers.models import (
    AccessMethod,
    ArticleCategory,
    ContentType,
    NewsArticle,
)
from app.services.article_identity import ArticleIdentityError, ArticleIdentityService

UNSAFE_MARKUP_PATTERN = re.compile(r"<\s*/?\s*[A-Za-z]")
CATEGORY_TEXT_PATTERN = re.compile(r"\s+")


class ArticleNormalisationErrorCode(str, Enum):
    """Stable failure codes that do not contain provider content."""

    INVALID_RECORD = "INVALID_ARTICLE_RECORD"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_ARTICLE_FIELD"
    INVALID_DATE = "INVALID_ARTICLE_DATE"
    INVALID_URL = "INVALID_ARTICLE_URL"
    UNSAFE_TEXT = "UNSAFE_ARTICLE_TEXT"
    RIGHTS_NOT_PERMITTED = "ARTICLE_RIGHTS_NOT_PERMITTED"
    CONTRACT_VALIDATION_FAILED = "ARTICLE_CONTRACT_VALIDATION_FAILED"


class ArticleNormalisationError(RuntimeError):
    """A safe normalisation failure with no raw article content."""

    def __init__(
        self,
        *,
        code: ArticleNormalisationErrorCode,
        message: str,
        field_name: str | None = None,
    ) -> None:
        self.code = code
        self.safe_message = message
        self.field_name = field_name
        super().__init__(message)


@dataclass(frozen=True)
class ArticleFieldMapping:
    """Provider field names that the approved policy permits us to read."""

    source_item_id: str
    title: str
    url: str
    publication_date: str
    category: str
    description: str
    permitted_content: str
    retrieved_at: str
    modified_at: str

    @property
    def permitted_input_fields(self) -> frozenset[str]:
        """Return the exact provider fields that may be processed."""

        return frozenset(
            {
                self.source_item_id,
                self.title,
                self.url,
                self.publication_date,
                self.category,
                self.description,
                self.permitted_content,
                self.retrieved_at,
                self.modified_at,
            }
        )


@dataclass(frozen=True)
class ArticleNormalisationPolicy:
    """Approved mapping, provenance, rights, and URL controls for one source."""

    field_mapping: ArticleFieldMapping
    source_profile: Literal["fixture-v1"]
    source_name: str
    decision_id: str
    access_method: AccessMethod
    attribution_text: str
    retention_rule: str
    allowed_hosts: frozenset[str]
    fallback_identity_prefix: str
    category_mapping: Mapping[str, ArticleCategory] = field(default_factory=dict)
    content_type: ContentType = ContentType.SYNTHETIC
    storage_allowed: bool = True
    display_allowed: bool = True
    ai_processing_allowed: bool = True
    derivative_output_allowed: bool = True


FIXTURE_FIELD_MAPPING = ArticleFieldMapping(
    source_item_id="record_key",
    title="headline",
    url="link",
    publication_date="published_at",
    category="topic",
    description="summary",
    permitted_content="body",
    retrieved_at="collected_at",
    modified_at="changed_at",
)

FIXTURE_NORMALISATION_POLICY = ArticleNormalisationPolicy(
    field_mapping=FIXTURE_FIELD_MAPPING,
    source_profile="fixture-v1",
    source_name="NewsFlow AI synthetic fixture",
    decision_id="NFA-SRC-AUTH-001",
    access_method=AccessMethod.FIXTURE,
    attribution_text="Source: NewsFlow AI synthetic fixture - not live news",
    retention_rule="fixture-until-replaced-or-deleted",
    allowed_hosts=frozenset({"example.invalid"}),
    fallback_identity_prefix="fixture-url-",
    category_mapping={
        "technology": ArticleCategory.TECHNOLOGY,
        "business": ArticleCategory.BUSINESS,
        "world": ArticleCategory.WORLD_NEWS,
        "world news": ArticleCategory.WORLD_NEWS,
        "science": ArticleCategory.SCIENCE,
    },
)


class ArticleNormalisationService:
    """Convert one provider record into the approved provider-neutral contract."""

    def __init__(
        self,
        policy: ArticleNormalisationPolicy = FIXTURE_NORMALISATION_POLICY,
        identity_service: ArticleIdentityService | None = None,
    ) -> None:
        self._policy = policy
        self._identity_service = identity_service or ArticleIdentityService()

    @property
    def permitted_input_fields(self) -> frozenset[str]:
        """Expose the allowlist for review and tests."""

        return self._policy.field_mapping.permitted_input_fields

    def normalise(self, record: Mapping[str, Any]) -> NewsArticle:
        """Return a safe validated article or raise a documented failure."""

        if not isinstance(record, Mapping):
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.INVALID_RECORD,
                message="The provider article record has an invalid structure.",
            )
        self._require_permitted_rights()

        mapping = self._policy.field_mapping
        title = self._required_text(
            record,
            mapping.title,
            collapse_whitespace=True,
        )
        canonical_url = self._normalise_url(
            self._required_text(record, mapping.url, collapse_whitespace=True),
            field_name=mapping.url,
        )
        source_item_id = self._normalise_identity(
            record,
            field_name=mapping.source_item_id,
            canonical_url=canonical_url,
        )
        publication_date = self._normalise_datetime(
            self._required_value(record, mapping.publication_date),
            field_name=mapping.publication_date,
        )
        category = self._normalise_category(
            self._required_text(
                record,
                mapping.category,
                collapse_whitespace=True,
            )
        )
        description = self._optional_text(record, mapping.description)
        permitted_content = self._required_text(
            record,
            mapping.permitted_content,
            collapse_whitespace=False,
        )
        retrieved_at = self._normalise_datetime(
            self._required_value(record, mapping.retrieved_at),
            field_name=mapping.retrieved_at,
        )
        modified_at = self._optional_datetime(record, mapping.modified_at)

        try:
            return NewsArticle.model_validate(
                {
                    "contract_version": "1.0",
                    "source_profile": self._policy.source_profile,
                    "source_item_id": source_item_id,
                    "source_name": self._policy.source_name,
                    "title": title,
                    "publication_date": publication_date,
                    "category": category,
                    "description": description,
                    "url": canonical_url,
                    "permitted_content": {
                        "status": "available",
                        "content_type": self._policy.content_type,
                        "text": permitted_content,
                        "ai_processing_allowed": (self._policy.ai_processing_allowed),
                        "derivative_output_allowed": (
                            self._policy.derivative_output_allowed
                        ),
                    },
                    "attribution": {
                        "display_name": self._policy.source_name,
                        "canonical_url": canonical_url,
                        "attribution_text": self._policy.attribution_text,
                        "byline": None,
                        "copyright_notice": None,
                    },
                    "rights": {
                        "decision_id": self._policy.decision_id,
                        "access_method": self._policy.access_method,
                        "storage_allowed": self._policy.storage_allowed,
                        "display_allowed": self._policy.display_allowed,
                        "expires_at": None,
                        "retention_rule": self._policy.retention_rule,
                    },
                    "retrieved_at": retrieved_at,
                    "modified_at": modified_at,
                }
            )
        except ValidationError as exc:
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.CONTRACT_VALIDATION_FAILED,
                message="The article failed the approved source data contract.",
            ) from exc

    def _require_permitted_rights(self) -> None:
        if not self._policy.storage_allowed or not self._policy.display_allowed:
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.RIGHTS_NOT_PERMITTED,
                message="The article cannot be retained under the active rights policy.",
            )

    def _required_value(self, record: Mapping[str, Any], field_name: str) -> Any:
        if field_name not in record or record[field_name] is None:
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.MISSING_REQUIRED_FIELD,
                message="A required article field is missing.",
                field_name=field_name,
            )
        return record[field_name]

    def _required_text(
        self,
        record: Mapping[str, Any],
        field_name: str,
        *,
        collapse_whitespace: bool,
    ) -> str:
        value = self._required_value(record, field_name)
        if not isinstance(value, str):
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.INVALID_RECORD,
                message="An article field has an invalid type.",
                field_name=field_name,
            )
        cleaned = self._normalise_text(
            value,
            field_name=field_name,
            collapse_whitespace=collapse_whitespace,
        )
        if not cleaned:
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.MISSING_REQUIRED_FIELD,
                message="A required article field is missing.",
                field_name=field_name,
            )
        return cleaned

    def _optional_text(
        self,
        record: Mapping[str, Any],
        field_name: str,
    ) -> str | None:
        value = record.get(field_name)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.INVALID_RECORD,
                message="An article field has an invalid type.",
                field_name=field_name,
            )
        cleaned = self._normalise_text(
            value,
            field_name=field_name,
            collapse_whitespace=True,
        )
        return cleaned or None

    def _normalise_text(
        self,
        value: str,
        *,
        field_name: str,
        collapse_whitespace: bool,
    ) -> str:
        cleaned = unicodedata.normalize("NFC", html.unescape(value)).strip()
        if UNSAFE_MARKUP_PATTERN.search(cleaned):
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.UNSAFE_TEXT,
                message="The article contains unsafe markup.",
                field_name=field_name,
            )
        if any(
            unicodedata.category(character) == "Cc"
            and character not in {"\n", "\r", "\t"}
            for character in cleaned
        ):
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.UNSAFE_TEXT,
                message="The article contains unsafe control characters.",
                field_name=field_name,
            )
        if collapse_whitespace:
            return " ".join(cleaned.split())
        return "\n".join(" ".join(line.split()) for line in cleaned.splitlines())

    def _normalise_category(self, value: str) -> ArticleCategory:
        normalised = CATEGORY_TEXT_PATTERN.sub(" ", value).strip().lower()
        return self._policy.category_mapping.get(normalised, ArticleCategory.OTHER)

    def _normalise_datetime(self, value: Any, *, field_name: str) -> datetime:
        parsed: datetime
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError as exc:
                raise ArticleNormalisationError(
                    code=ArticleNormalisationErrorCode.INVALID_DATE,
                    message="An article timestamp is invalid.",
                    field_name=field_name,
                ) from exc
        else:
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.INVALID_DATE,
                message="An article timestamp is invalid.",
                field_name=field_name,
            )
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.INVALID_DATE,
                message="An article timestamp must include a timezone.",
                field_name=field_name,
            )
        return parsed.astimezone(timezone.utc)

    def _optional_datetime(
        self,
        record: Mapping[str, Any],
        field_name: str,
    ) -> datetime | None:
        value = record.get(field_name)
        if value is None:
            return None
        return self._normalise_datetime(value, field_name=field_name)

    def _normalise_identity(
        self,
        record: Mapping[str, Any],
        *,
        field_name: str,
        canonical_url: str,
    ) -> str:
        value = record.get(field_name)
        if value is not None and not isinstance(value, str):
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.INVALID_RECORD,
                message="An article field has an invalid type.",
                field_name=field_name,
            )
        try:
            identity = self._identity_service.resolve(
                provider_id=self._policy.source_profile,
                external_article_id=value,
                canonical_url=canonical_url,
                fallback_prefix=self._policy.fallback_identity_prefix,
            )
        except ArticleIdentityError as exc:
            raise ArticleNormalisationError(
                code=ArticleNormalisationErrorCode.INVALID_RECORD,
                message="The article identity is invalid.",
                field_name=field_name,
            ) from exc
        return identity.external_article_id

    def _normalise_url(self, value: str, *, field_name: str) -> str:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as exc:
            raise self._invalid_url(field_name) from exc
        if (
            parsed.scheme.lower() != "https"
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.hostname.lower() not in self._policy.allowed_hosts
        ):
            raise self._invalid_url(field_name)

        host = parsed.hostname.lower()
        netloc = f"{host}:{port}" if port is not None else host
        canonical = SplitResult(
            scheme="https",
            netloc=netloc,
            path=parsed.path or "/",
            query=parsed.query,
            fragment="",
        )
        return urlunsplit(canonical)

    @staticmethod
    def _invalid_url(field_name: str) -> ArticleNormalisationError:
        return ArticleNormalisationError(
            code=ArticleNormalisationErrorCode.INVALID_URL,
            message="The article URL is invalid or outside the approved source policy.",
            field_name=field_name,
        )
