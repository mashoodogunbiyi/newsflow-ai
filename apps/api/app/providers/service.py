"""Provider-independent article discovery consumer."""

from app.providers.base import NewsProvider
from app.providers.models import ArticleQuery, NewsArticle, ProviderPage


class ArticleDiscoveryService:
    """Use any compliant provider without provider-specific application logic."""

    def __init__(self, provider: NewsProvider) -> None:
        self._provider = provider

    async def discover(self, query: ArticleQuery) -> ProviderPage:
        """Return one provider-neutral article page."""

        return await self._provider.fetch_articles(query)

    async def retrieve(self, source_item_id: str) -> NewsArticle:
        """Return one provider-neutral article."""

        return await self._provider.fetch_article(source_item_id)
