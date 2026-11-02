"""Run one bounded content-retention and private-object cleanup cycle."""

import asyncio
import json
from datetime import timedelta

from app.core.config import get_settings
from app.database.sqlalchemy import SqlAlchemyDatabase
from app.repositories.content_deletion import SqlAlchemyContentDeletionRepository
from app.services.content_deletion import ContentDeletionService
from app.services.image_storage import LocalPrivateImageStorage


async def run() -> None:
    """Execute one worker batch using validated environment configuration."""

    settings = get_settings()
    database = SqlAlchemyDatabase(
        settings.require_database_url(),
        connect_timeout_seconds=settings.database_connect_timeout_seconds,
    )
    storage_settings = settings.require_image_storage_configuration()
    service = ContentDeletionService(
        repository=SqlAlchemyContentDeletionRepository(database),
        storage=LocalPrivateImageStorage(storage_settings.local_root),
        draft_retention=timedelta(days=settings.draft_deletion_retention_days),
        audit_retention=timedelta(days=settings.deletion_audit_retention_days),
        retry_delay=timedelta(seconds=settings.image_cleanup_retry_seconds),
    )
    try:
        result = await service.run_retention()
        print(json.dumps(result.__dict__, sort_keys=True))
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(run())
