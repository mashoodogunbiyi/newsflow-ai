"""Secure saved-content deletion and retention workflow."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.repositories.content_deletion import (
    ContentDeletionRepository,
    DeletionRequest,
    ImageCleanupTask,
)
from app.services.authorization import require_owned_resource
from app.services.image_storage import PrivateImageStorage, PrivateImageStorageError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetentionRunResult:
    """Content-free worker totals suitable for operations output."""

    images_completed: int
    images_retried: int
    drafts_redacted: int


class ContentDeletionService:
    """Remove active access immediately and safely finish asynchronous cleanup."""

    def __init__(
        self,
        *,
        repository: ContentDeletionRepository,
        storage: PrivateImageStorage,
        draft_retention: timedelta,
        audit_retention: timedelta,
        retry_delay: timedelta,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._draft_retention = draft_retention
        self._audit_retention = audit_retention
        self._retry_delay = retry_delay

    async def delete(self, *, owner_id: UUID, draft_id: UUID) -> DeletionRequest:
        now = datetime.now(UTC)
        deletion = require_owned_resource(
            await self._repository.request_for_owner(
                owner_id=owner_id,
                draft_id=draft_id,
                requested_at=now,
                purge_after=now + self._draft_retention,
            )
        )
        for task in deletion.cleanup_tasks:
            await self._attempt_cleanup(task, now=now)
        return deletion

    async def run_retention(self, *, limit: int = 100) -> RetentionRunResult:
        now = datetime.now(UTC)
        tasks = await self._repository.claim_due_image_cleanup(now=now, limit=limit)
        completed = 0
        retried = 0
        for task in tasks:
            if await self._attempt_cleanup(task, now=now):
                completed += 1
            else:
                retried += 1
        redacted = await self._repository.purge_due_content(
            now=now,
            audit_expiry=now - self._audit_retention,
            limit=limit,
        )
        return RetentionRunResult(
            images_completed=completed,
            images_retried=retried,
            drafts_redacted=redacted,
        )

    async def _attempt_cleanup(self, task: ImageCleanupTask, *, now: datetime) -> bool:
        try:
            await self._storage.delete(task.storage_key)
        except PrivateImageStorageError:
            await self._repository.retry_image_cleanup(
                job_id=task.job_id,
                retry_at=now + self._retry_delay,
            )
            logger.warning(
                "Private image cleanup will be retried.",
                extra={"event": "image_cleanup_retry", "image_id": str(task.image_id)},
            )
            return False
        await self._repository.complete_image_cleanup(
            job_id=task.job_id,
            completed_at=now,
        )
        return True
