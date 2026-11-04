"""Bounded recovery coordination for durable private-storage cleanup work."""

import logging
from dataclasses import dataclass
from typing import Protocol

from app.core.logging_config import log_event
from app.services.content_deletion import RetentionRunResult

logger = logging.getLogger(__name__)


class StorageRecoveryWorker(Protocol):
    """Small boundary implemented by the existing deletion and retention service."""

    async def run_retention(self, *, limit: int = 100) -> RetentionRunResult: ...


class RecoveryOperationError(RuntimeError):
    """Safe failure raised when reconciliation cannot be completed."""

    code = "storage_reconciliation_unavailable"
    safe_message = "Private storage reconciliation could not be completed safely."


@dataclass(frozen=True)
class StorageRecoveryResult:
    """Content-free reconciliation totals for operational evidence."""

    objects_completed: int
    objects_rescheduled: int
    drafts_redacted: int
    status: str = "completed"


class ReliabilityRecoveryService:
    """Run one bounded reconciliation batch without exposing private object keys."""

    def __init__(self, worker: StorageRecoveryWorker) -> None:
        self._worker = worker

    async def reconcile_private_storage(
        self,
        *,
        limit: int = 100,
        request_id: str | None = None,
    ) -> StorageRecoveryResult:
        """Retry durable cleanup work and emit content-free recovery evidence."""

        if not 1 <= limit <= 500:
            raise ValueError("Recovery batch limit must be between 1 and 500.")
        log_event(
            logger,
            logging.INFO,
            "storage_reconciliation_started",
            component="private_image_storage",
            operation="reconcile_cleanup_jobs",
            recovery_status="started",
            request_id=request_id,
            counts={"limit": limit},
        )
        try:
            outcome = await self._worker.run_retention(limit=limit)
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "storage_reconciliation_failed",
                component="private_image_storage",
                operation="reconcile_cleanup_jobs",
                recovery_status="retry_required",
                request_id=request_id,
                error_category="reconciliation_unavailable",
            )
            raise RecoveryOperationError(RecoveryOperationError.safe_message) from exc

        result = StorageRecoveryResult(
            objects_completed=outcome.images_completed,
            objects_rescheduled=outcome.images_retried,
            drafts_redacted=outcome.drafts_redacted,
        )
        log_event(
            logger,
            logging.INFO,
            "storage_reconciliation_completed",
            component="private_image_storage",
            operation="reconcile_cleanup_jobs",
            recovery_status="completed",
            request_id=request_id,
            counts={
                "objects_completed": result.objects_completed,
                "objects_rescheduled": result.objects_rescheduled,
                "drafts_redacted": result.drafts_redacted,
            },
        )
        return result
