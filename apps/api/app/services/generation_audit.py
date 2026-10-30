"""Safe audit writer for the LinkedIn generation request lifecycle."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.core.logging_config import log_event
from app.models.generation_audit import (
    GenerationAuditContext,
    GenerationAuditEvent,
    GenerationAuditEventCreate,
    GenerationAuditEventType,
    GenerationAuditStatus,
)
from app.models.generation_usage import GenerationErrorCategory
from app.repositories.generation_audit import (
    GenerationAuditRepository,
    GenerationAuditRepositoryError,
)

logger = logging.getLogger(__name__)
Clock = Callable[[], datetime]


class GenerationAuditUnavailable(RuntimeError):
    """Raised when required lifecycle evidence cannot be recorded."""

    code = "generation_audit_unavailable"
    safe_message = "Generation monitoring is temporarily unavailable."


class GenerationAuditService:
    """Record only identifiers, decisions, timings, and safe categories."""

    def __init__(
        self,
        *,
        repository: GenerationAuditRepository,
        retention: timedelta,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._retention = retention
        self._clock = clock or (lambda: datetime.now(UTC))

    async def start_request(
        self,
        *,
        user_id: UUID,
        article_id: UUID,
    ) -> GenerationAuditContext:
        now = self._now()
        try:
            await self._repository.delete_before(now - self._retention)
        except GenerationAuditRepositoryError as exc:
            raise GenerationAuditUnavailable from exc
        context = GenerationAuditContext(
            generation_request_id=uuid4(),
            user_id=user_id,
            article_id=article_id,
            started_at=now,
        )
        await self._record(
            context=context,
            event_type=GenerationAuditEventType.GENERATION_STARTED,
            status=GenerationAuditStatus.STARTED,
        )
        return context

    async def record_rights_decision(
        self,
        *,
        context: GenerationAuditContext,
        allowed: bool,
        decision: str,
    ) -> GenerationAuditEvent:
        return await self._record(
            context=context,
            event_type=(
                GenerationAuditEventType.RIGHTS_VERIFIED
                if allowed
                else GenerationAuditEventType.RIGHTS_DENIED
            ),
            status=(
                GenerationAuditStatus.PASSED
                if allowed
                else GenerationAuditStatus.REJECTED
            ),
            rights_decision=decision,
        )

    async def record_validation(
        self,
        *,
        context: GenerationAuditContext,
        passed: bool,
        validation_status: str,
        prompt_version: str | None = None,
    ) -> GenerationAuditEvent:
        return await self._record(
            context=context,
            event_type=(
                GenerationAuditEventType.VALIDATION_PASSED
                if passed
                else GenerationAuditEventType.VALIDATION_FAILED
            ),
            status=(
                GenerationAuditStatus.PASSED
                if passed
                else GenerationAuditStatus.REJECTED
            ),
            validation_status=validation_status,
            prompt_version=prompt_version,
        )

    async def record_usage_rejection(
        self,
        *,
        context: GenerationAuditContext,
        category: GenerationErrorCategory,
    ) -> GenerationAuditEvent:
        return await self._record(
            context=context,
            event_type=GenerationAuditEventType.USAGE_REJECTED,
            status=GenerationAuditStatus.REJECTED,
            error_category=category,
        )

    async def complete_request(
        self,
        *,
        context: GenerationAuditContext,
        generation_run_id: UUID,
        usage_event_id: UUID | None,
        model_identifier: str,
        prompt_version: str,
    ) -> GenerationAuditEvent:
        return await self._record(
            context=context,
            event_type=GenerationAuditEventType.GENERATION_COMPLETED,
            status=GenerationAuditStatus.SUCCEEDED,
            duration_ms=self._duration_ms(context),
            generation_run_id=generation_run_id,
            usage_event_id=usage_event_id,
            model_identifier=model_identifier,
            prompt_version=prompt_version,
        )

    async def fail_request(
        self,
        *,
        context: GenerationAuditContext,
        category: GenerationErrorCategory,
        usage_event_id: UUID | None = None,
    ) -> GenerationAuditEvent:
        return await self._record(
            context=context,
            event_type=GenerationAuditEventType.GENERATION_FAILED,
            status=GenerationAuditStatus.FAILED,
            duration_ms=self._duration_ms(context),
            usage_event_id=usage_event_id,
            error_category=category,
        )

    async def _record(
        self,
        *,
        context: GenerationAuditContext,
        event_type: GenerationAuditEventType,
        status: GenerationAuditStatus,
        duration_ms: int | None = None,
        generation_run_id: UUID | None = None,
        usage_event_id: UUID | None = None,
        model_identifier: str | None = None,
        prompt_version: str | None = None,
        error_category: GenerationErrorCategory | None = None,
        rights_decision: str | None = None,
        validation_status: str | None = None,
    ) -> GenerationAuditEvent:
        event = GenerationAuditEventCreate(
            generation_request_id=context.generation_request_id,
            user_id=context.user_id,
            article_id=context.article_id,
            event_type=event_type,
            status=status,
            occurred_at=self._now(),
            duration_ms=duration_ms,
            generation_run_id=generation_run_id,
            usage_event_id=usage_event_id,
            model_identifier=model_identifier,
            prompt_version=prompt_version,
            error_category=error_category,
            rights_decision=rights_decision,
            validation_status=validation_status,
        )
        try:
            recorded = await self._repository.record_event(event)
        except GenerationAuditRepositoryError as exc:
            raise GenerationAuditUnavailable from exc
        log_event(
            logger,
            logging.INFO,
            event_type.value,
            job_id=str(context.generation_request_id),
            status=status.value,
            duration_ms=duration_ms,
            model=model_identifier,
            error_category=(error_category.value if error_category else None),
        )
        return recorded

    def _duration_ms(self, context: GenerationAuditContext) -> int:
        return max(
            0,
            int((self._now() - context.started_at).total_seconds() * 1000),
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("The generation audit clock must include a timezone.")
        return value.astimezone(UTC)
