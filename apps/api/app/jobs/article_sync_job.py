"""Run the durable NFA-33 scheduled article synchronisation once."""

import asyncio
from datetime import timedelta

from app.core.config import get_settings
from app.database.sqlalchemy import SqlAlchemyDatabase
from app.providers.factory import create_news_provider
from app.repositories.article_sync import SqlAlchemyArticleSyncRepository
from app.repositories.articles import SqlAlchemyArticleRepository
from app.services.article_deduplication import ArticleDeduplicationService
from app.services.article_sync import ArticleSyncScheduler, ArticleSyncService


async def run() -> None:
    """Build the shared pipeline and run one due scheduled job."""

    settings = get_settings()
    database = SqlAlchemyDatabase(
        settings.require_database_url(),
        connect_timeout_seconds=settings.database_connect_timeout_seconds,
    )
    try:
        provider = create_news_provider(settings)
        repository = SqlAlchemyArticleSyncRepository(database)
        service = ArticleSyncService(
            provider=provider,
            source_profile_key="fixture-v1",
            ingestion=ArticleDeduplicationService(
                SqlAlchemyArticleRepository(database)
            ),
            repository=repository,
            page_size=settings.article_sync_page_size,
            max_retries=settings.article_sync_max_retries,
            retry_base_seconds=settings.article_sync_retry_base_seconds,
            lease_duration=timedelta(seconds=settings.article_sync_lease_seconds),
        )
        scheduler = ArticleSyncScheduler(
            service=service,
            interval=timedelta(seconds=settings.article_sync_interval_seconds),
        )
        await scheduler.run_due()
    finally:
        await database.close()


def main() -> None:
    """CLI entry point for cron, a container job, or a managed scheduler."""

    asyncio.run(run())


if __name__ == "__main__":
    main()
