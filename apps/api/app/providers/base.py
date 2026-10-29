"""Provider interface consumed by NewsFlow AI application services."""

from typing import Protocol, runtime_checkable

from app.providers.models import (
    ArticleQuery,
    NewsArticle,
    ProviderCapabilities,
    ProviderPage,
)


@runtime_checkable
class NewsProvider(Protocol):
    """Agreement every authorised news-source adapter must implement."""

    @property
    def provider_id(self) -> str:
        """Return a stable non-secret provider identifier."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Describe pagination and incremental-retrieval support."""

    async def fetch_articles(self, query: ArticleQuery) -> ProviderPage:
        """Discover a validated page of permitted article information."""

    async def fetch_article(self, source_item_id: str) -> NewsArticle:
        """Retrieve one validated article or raise a documented provider error."""
