"""Synthetic provider used without live network or licensed news access."""

import base64
from collections.abc import Mapping, Sequence
from typing import Any

from app.providers.exceptions import (
    ArticleNotFoundError,
    InvalidProviderCursorError,
    ProviderDataError,
    ProviderError,
)
from app.providers.models import (
    SOURCE_ID_PATTERN,
    ArticleQuery,
    NewsArticle,
    ProviderCapabilities,
    ProviderPage,
)
from app.providers.normalisation import (
    ArticleNormalisationError,
    ArticleNormalisationService,
)

DEFAULT_FIXTURES: tuple[Mapping[str, Any], ...] = (
    {
        "record_key": "fixture-technology-001",
        "headline": "Synthetic company announces an energy-efficient data platform",
        "link": "https://example.invalid/newsflow-ai/fixture-technology-001",
        "published_at": "2026-10-12T09:00:00Z",
        "topic": "technology",
        "summary": (
            "A fictional technology company announced a test platform designed "
            "to reduce energy use."
        ),
        "body": (
            "This original synthetic report describes a fictional test platform. "
            "It is not based on a live CNN article."
        ),
        "collected_at": "2026-10-12T09:05:00Z",
        "changed_at": None,
    },
    {
        "record_key": "fixture-business-001",
        "headline": "Fictional retailer tests reusable delivery packaging",
        "link": "https://example.invalid/newsflow-ai/fixture-business-001",
        "published_at": "2026-10-13T10:00:00Z",
        "topic": "business",
        "summary": "A fictional retailer is evaluating reusable packaging in a trial.",
        "body": (
            "This synthetic business fixture was written for NewsFlow AI testing "
            "and contains no licensed news text."
        ),
        "collected_at": "2026-10-13T10:04:00Z",
        "changed_at": None,
    },
    {
        "record_key": "fixture-science-001",
        "headline": "Imaginary research team publishes a coastal sensor experiment",
        "link": "https://example.invalid/newsflow-ai/fixture-science-001",
        "published_at": "2026-10-14T11:00:00Z",
        "topic": "science",
        "summary": None,
        "body": (
            "This fictional science record exists only to test permitted article "
            "discovery and pagination."
        ),
        "collected_at": "2026-10-14T11:03:00Z",
        "changed_at": None,
    },
)


class FixtureNewsProvider:
    """Return original synthetic records through the common provider contract."""

    def __init__(
        self,
        fixtures: Sequence[Mapping[str, Any]] | None = None,
        *,
        simulated_error: ProviderError | None = None,
        normalisation_service: ArticleNormalisationService | None = None,
    ) -> None:
        self._fixtures = tuple(fixtures) if fixtures is not None else DEFAULT_FIXTURES
        self._simulated_error = simulated_error
        self._normalisation_service = (
            normalisation_service or ArticleNormalisationService()
        )

    @property
    def provider_id(self) -> str:
        return "fixture"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(pagination=True, incremental_retrieval=True)

    async def fetch_articles(self, query: ArticleQuery) -> ProviderPage:
        self._raise_simulated_error()
        articles = tuple(self._map_fixture(raw) for raw in self._fixtures)
        if query.published_after is not None:
            articles = tuple(
                article
                for article in articles
                if article.publication_date > query.published_after
            )

        offset = self._decode_cursor(query.cursor, result_count=len(articles))
        end = min(offset + query.limit, len(articles))
        next_cursor = self._encode_cursor(end) if end < len(articles) else None
        return ProviderPage(
            provider_id=self.provider_id,
            items=articles[offset:end],
            next_cursor=next_cursor,
            capabilities=self.capabilities,
        )

    async def fetch_article(self, source_item_id: str) -> NewsArticle:
        self._raise_simulated_error()
        for raw in self._fixtures:
            if raw.get("record_key") == source_item_id:
                return self._map_fixture(raw)
        raise ArticleNotFoundError

    def _raise_simulated_error(self) -> None:
        if self._simulated_error is not None:
            raise self._simulated_error

    def _map_fixture(self, raw: Mapping[str, Any]) -> NewsArticle:
        source_item_id = raw.get("record_key")
        safe_item_id = (
            source_item_id
            if isinstance(source_item_id, str)
            and len(source_item_id) <= 200
            and SOURCE_ID_PATTERN.fullmatch(source_item_id)
            else None
        )
        try:
            return self._normalisation_service.normalise(raw)
        except ArticleNormalisationError as exc:
            raise ProviderDataError(safe_item_id) from exc

    def _encode_cursor(self, offset: int) -> str:
        value = f"{self.provider_id}:{offset}".encode()
        return base64.urlsafe_b64encode(value).decode()

    def _decode_cursor(self, cursor: str | None, *, result_count: int) -> int:
        if cursor is None:
            return 0
        try:
            decoded = base64.b64decode(
                cursor.encode(), altchars=b"-_", validate=True
            ).decode()
            provider_id, offset_text = decoded.split(":", maxsplit=1)
            offset = int(offset_text)
        except (UnicodeDecodeError, ValueError) as exc:
            raise InvalidProviderCursorError from exc
        if provider_id != self.provider_id or offset < 0 or offset > result_count:
            raise InvalidProviderCursorError
        return offset
