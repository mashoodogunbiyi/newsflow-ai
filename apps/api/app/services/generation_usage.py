"""Configurable usage limits and safe lifecycle tracking for AI generation."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from app.core.logging_config import log_event
from app.models.ai import AITokenUsage
from app.models.generation_usage import (
    GenerationErrorCategory,
    GenerationUsageAttempt,
)
from app.repositories.generation_usage import (
    DuplicateGenerationInProgress,
    GenerationConcurrencyLimitReached,
    GenerationDailyLimitReached,
    GenerationUsageRepository,
    GenerationUsageRepositoryError,
)

logger = logging.getLogger(__name__)
Clock = Callable[[], datetime]


class GenerationUsageError(RuntimeError):
    """Safe base error for generation usage enforcement."""

    def __init__(self, *, code: str, message: str, retry_after_seconds: int = 0):
        self.code = code
        self.safe_message = message
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message)


class GenerationLimitExceeded(GenerationUsageError):
    """Raised when the user's daily allowance is exhausted."""


class GenerationConcurrencyLimitExceeded(GenerationUsageError):
    """Raised when too many provider calls are active for one user."""


class GenerationDuplicateInProgress(GenerationUsageError):
    """Raised when an identical idempotent request is active."""


class GenerationUsageUnavailable(GenerationUsageError):
    """Raised when shared controls fail closed before provider access."""


class GenerationUsageService:
    """Enforce limits through shared storage and record safe attempt outcomes."""

    def __init__(
        self,
        *,
        repository: GenerationUsageRepository,
        daily_limit: int,
        concurrent_limit: int,
        attempt_timeout: timedelta,
        retention: timedelta,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._daily_limit = daily_limit
        self._concurrent_limit = concurrent_limit
        self._attempt_timeout = attempt_timeout
        self._retention = retention
        self._clock = clock or (lambda: datetime.now(UTC))

    async def start_attempt(
        self,
        *,
        owner_id: UUID,
        request_fingerprint: str,
    ) -> GenerationUsageAttempt:
        now = self._clock()
        day_started_at = datetime.combine(now.date(), time.min, tzinfo=UTC)
        day_ends_at = day_started_at + timedelta(days=1)
        try:
            attempt = await self._repository.reserve_attempt(
                owner_id=owner_id,
                request_fingerprint=request_fingerprint,
                now=now,
                day_started_at=day_started_at,
                day_ends_at=day_ends_at,
                expires_at=now + self._attempt_timeout,
                retention_started_at=now - self._retention,
                daily_limit=self._daily_limit,
                concurrent_limit=self._concurrent_limit,
            )
        except GenerationDailyLimitReached as exc:
            self._log_rejection("generation_daily_limit_reached")
            raise GenerationLimitExceeded(
                code="generation_limit_exceeded",
                message="You have reached your current generation limit.",
                retry_after_seconds=exc.retry_after_seconds,
            ) from exc
        except GenerationConcurrencyLimitReached as exc:
            self._log_rejection("generation_concurrency_limit_reached")
            raise GenerationConcurrencyLimitExceeded(
                code="generation_concurrency_limit",
                message="Too many generations are already in progress.",
                retry_after_seconds=exc.retry_after_seconds,
            ) from exc
        except DuplicateGenerationInProgress as exc:
            self._log_rejection("generation_duplicate_in_progress")
            raise GenerationDuplicateInProgress(
                code="generation_in_progress",
                message="This generation request is already in progress.",
                retry_after_seconds=exc.retry_after_seconds,
            ) from exc
        except GenerationUsageRepositoryError as exc:
            raise GenerationUsageUnavailable(
                code="generation_usage_unavailable",
                message="Generation is temporarily unavailable.",
            ) from exc
        log_event(
            logger,
            logging.INFO,
            "generation_usage_started",
            job_id=str(attempt.id),
            status="started",
        )
        return attempt

    async def complete_attempt(
        self,
        *,
        attempt: GenerationUsageAttempt,
        generation_run_id: UUID,
        model_identifier: str,
        token_usage: AITokenUsage,
    ) -> None:
        completed_at = self._clock()
        try:
            await self._repository.complete_attempt(
                attempt=attempt,
                generation_run_id=generation_run_id,
                model_identifier=model_identifier,
                token_usage=token_usage,
                completed_at=completed_at,
            )
        except GenerationUsageRepositoryError as exc:
            raise GenerationUsageUnavailable(
                code="generation_usage_unavailable",
                message="Generation usage could not be recorded.",
            ) from exc
        log_event(
            logger,
            logging.INFO,
            "generation_usage_completed",
            job_id=str(attempt.id),
            status="succeeded",
            model=model_identifier,
            duration_ms=self._duration_ms(attempt, completed_at),
            counts=token_usage.model_dump(exclude_none=True),
        )

    async def fail_attempt(
        self,
        *,
        attempt: GenerationUsageAttempt,
        category: GenerationErrorCategory,
    ) -> None:
        completed_at = self._clock()
        try:
            await self._repository.fail_attempt(
                attempt=attempt,
                category=category,
                completed_at=completed_at,
            )
        except GenerationUsageRepositoryError as exc:
            raise GenerationUsageUnavailable(
                code="generation_usage_unavailable",
                message="Generation usage could not be recorded.",
            ) from exc
        log_event(
            logger,
            logging.WARNING,
            "generation_usage_failed",
            job_id=str(attempt.id),
            status="failed",
            error_category=category.value,
            duration_ms=self._duration_ms(attempt, completed_at),
        )

    def _log_rejection(self, event: str) -> None:
        log_event(logger, logging.WARNING, event, status="rejected")

    @staticmethod
    def _duration_ms(attempt: GenerationUsageAttempt, completed_at: datetime) -> int:
        return max(0, int((completed_at - attempt.created_at).total_seconds() * 1000))
