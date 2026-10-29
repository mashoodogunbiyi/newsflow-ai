"""Disabled CNN adapter boundary enforced by the active No-Go decision."""

from dataclasses import dataclass
from typing import Literal

from app.providers.exceptions import SourceNotAuthorisedError
from app.providers.models import (
    ArticleQuery,
    NewsArticle,
    ProviderCapabilities,
    ProviderPage,
)


@dataclass(frozen=True)
class CnnAdapterDecision:
    """Non-secret evidence explaining why live access is blocked."""

    authorisation_decision_id: str = "NFA-SRC-AUTH-001"
    architecture_decision_id: str = "ADR-001"
    status: Literal["blocked"] = "blocked"
    live_access_authorised: Literal[False] = False


class CnnSourceAdapter:
    """Implement NewsProvider while making all live CNN access impossible."""

    @property
    def provider_id(self) -> str:
        """Return a stable identifier without naming an endpoint or product."""

        return "cnn-disabled"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Expose no assumed live-provider capabilities."""

        return ProviderCapabilities(
            pagination=False,
            incremental_retrieval=False,
        )

    @property
    def decision(self) -> CnnAdapterDecision:
        """Return the active authorisation and architecture decision references."""

        return CnnAdapterDecision()

    async def fetch_articles(self, query: ArticleQuery) -> ProviderPage:
        """Block discovery before any live request can occur."""

        del query
        self._raise_not_authorised()

    async def fetch_article(self, source_item_id: str) -> NewsArticle:
        """Block detail retrieval before any live request can occur."""

        del source_item_id
        self._raise_not_authorised()

    @staticmethod
    def _raise_not_authorised() -> None:
        raise SourceNotAuthorisedError
