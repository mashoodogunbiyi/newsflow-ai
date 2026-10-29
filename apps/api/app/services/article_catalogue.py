"""Authenticated, rights-aware article catalogue workflow."""

import base64
import binascii
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError

from app.models.article_catalogue import (
    ArticleAttributionResponse,
    ArticleCatalogueQuery,
    ArticleCollectionResponse,
    ArticleResponse,
)
from app.repositories.article_catalogue import (
    ArticleCatalogueCursor,
    ArticleCatalogueFilters,
    ArticleCatalogueRecord,
    ArticleCatalogueRepository,
)

CATEGORY_LABELS = {
    "technology": "Technology",
    "business": "Business",
    "world_news": "World News",
    "science": "Science",
    "other": "Other",
}


class ArticleCatalogueNotFoundError(RuntimeError):
    """Raised for both missing and non-disclosable articles."""


class ArticleCatalogueCursorError(ValueError):
    """Raised when a continuation cursor is invalid for the current query."""


class ArticleCatalogueDataError(RuntimeError):
    """Raised when stored public metadata cannot be returned safely."""


class ArticleCatalogueService:
    """Apply public-field, visibility, and stable-pagination rules."""

    def __init__(
        self,
        repository: ArticleCatalogueRepository,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))

    async def list_articles(
        self,
        query: ArticleCatalogueQuery,
    ) -> ArticleCollectionResponse:
        checked_at = self._checked_at()
        fingerprint = self._query_fingerprint(query)
        cursor = (
            None
            if query.cursor is None
            else self._decode_cursor(query.cursor, fingerprint=fingerprint)
        )
        records = await self._repository.list_visible(
            filters=ArticleCatalogueFilters(
                search=query.search,
                provider=query.provider,
                published_from=query.published_from,
                published_to=query.published_to,
                sort=query.sort,
            ),
            cursor=cursor,
            checked_at=checked_at,
            limit=query.limit + 1,
        )
        visible = [record for record in records if self._is_visible(record, checked_at)]
        has_more = len(records) > query.limit
        page_records = visible[: query.limit]
        items = [self._public_response(record) for record in page_records]

        next_cursor = None
        if has_more and page_records:
            last = page_records[-1]
            next_cursor = self._encode_cursor(
                ArticleCatalogueCursor(
                    published_at=last.published_at,
                    article_id=last.id,
                ),
                fingerprint=fingerprint,
            )
        return ArticleCollectionResponse(items=items, next_cursor=next_cursor)

    async def get_article(self, article_id: UUID) -> ArticleResponse:
        checked_at = self._checked_at()
        record = await self._repository.get_visible(
            article_id=article_id,
            checked_at=checked_at,
        )
        if record is None or not self._is_visible(record, checked_at):
            raise ArticleCatalogueNotFoundError(
                "The article is missing or cannot be disclosed."
            )
        return self._public_response(record)

    def _checked_at(self) -> datetime:
        checked_at = self._clock()
        if checked_at.tzinfo is None or checked_at.utcoffset() is None:
            raise ValueError("The catalogue clock must include a timezone.")
        return checked_at.astimezone(UTC)

    @staticmethod
    def _is_visible(record: ArticleCatalogueRecord, checked_at: datetime) -> bool:
        return all(
            (
                record.article_status == "active",
                record.source_status == "enabled",
                record.snapshot_display_allowed,
                record.rights_verification_status == "verified",
                record.rights_display_allowed,
                record.rights_last_verified_at is not None,
                record.rights_last_verified_at is not None
                and record.rights_last_verified_at <= checked_at,
                record.rights_effective_from <= checked_at,
                record.retention_expires_at is None
                or record.retention_expires_at > checked_at,
                not record.attribution_required or bool(record.rights_attribution_text),
            )
        )

    @staticmethod
    def _public_response(record: ArticleCatalogueRecord) -> ArticleResponse:
        attribution_text = (
            record.rights_attribution_text
            if record.attribution_required
            else record.attribution_text
        )
        try:
            return ArticleResponse(
                id=record.id,
                title=record.title,
                description=record.description,
                source_url=record.canonical_url,
                provider=record.provider,
                published_at=record.published_at,
                category=CATEGORY_LABELS.get(record.category, "Other"),
                attribution=ArticleAttributionResponse(
                    display_name=record.attribution_display_name,
                    text=attribution_text,
                    byline=record.byline,
                    copyright_notice=record.copyright_notice,
                ),
            )
        except ValidationError as exc:
            raise ArticleCatalogueDataError(
                "Stored article metadata is not safe to disclose."
            ) from exc

    @classmethod
    def _query_fingerprint(cls, query: ArticleCatalogueQuery) -> str:
        payload = query.model_dump(
            mode="json",
            exclude={"cursor", "limit"},
        )
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _encode_cursor(
        cursor: ArticleCatalogueCursor,
        *,
        fingerprint: str,
    ) -> str:
        payload = json.dumps(
            {
                "v": 1,
                "published_at": cursor.published_at.astimezone(UTC).isoformat(),
                "article_id": str(cursor.article_id),
                "query": fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(
        value: str,
        *,
        fingerprint: str,
    ) -> ArticleCatalogueCursor:
        try:
            padded = value + "=" * (-len(value) % 4)
            payload = json.loads(
                base64.b64decode(
                    padded.encode("ascii"),
                    altchars=b"-_",
                    validate=True,
                ).decode("utf-8")
            )
            if set(payload) != {"v", "published_at", "article_id", "query"}:
                raise ValueError
            if payload["v"] != 1 or payload["query"] != fingerprint:
                raise ValueError
            published_at = datetime.fromisoformat(payload["published_at"])
            if published_at.tzinfo is None or published_at.utcoffset() is None:
                raise ValueError
            return ArticleCatalogueCursor(
                published_at=published_at.astimezone(UTC),
                article_id=UUID(payload["article_id"]),
            )
        except (
            UnicodeError,
            ValueError,
            TypeError,
            KeyError,
            json.JSONDecodeError,
            binascii.Error,
        ) as exc:
            raise ArticleCatalogueCursorError(
                "The catalogue cursor is invalid for this query."
            ) from exc
