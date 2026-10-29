"""Application workflow for idempotent normalised article ingestion."""

from app.providers.models import NewsArticle
from app.repositories.articles import (
    ArticleIngestionResult,
    ArticleRepository,
)


class ArticleStorageNotPermittedError(RuntimeError):
    """Raised before persistence when the active rights decision blocks storage."""


class ArticleDeduplicationService:
    """Persist only validated and storage-permitted provider articles."""

    def __init__(self, repository: ArticleRepository) -> None:
        self._repository = repository

    async def ingest(self, article: NewsArticle) -> ArticleIngestionResult:
        """Create, update, or skip one already-normalised article."""

        if not article.rights.storage_allowed:
            raise ArticleStorageNotPermittedError(
                "The active source rights decision does not permit storage."
            )
        return await self._repository.ingest(article)
