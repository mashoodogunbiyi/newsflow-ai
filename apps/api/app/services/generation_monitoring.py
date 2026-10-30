"""Administrator monitoring views derived from safe generation records."""

from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.generation_audit import (
    GenerationAuditCollectionResponse,
    GenerationAuditEvent,
    GenerationAuditEventType,
    GenerationMetricsResponse,
)
from app.models.generation_usage import GenerationErrorCategory
from app.repositories.generation_audit import (
    GenerationAuditRepository,
    GenerationAuditRepositoryError,
)
from app.services.generation_audit import GenerationAuditUnavailable


class GenerationMonitoringService:
    """Provide bounded audit inspection and identifier-free aggregate metrics."""

    def __init__(
        self,
        *,
        repository: GenerationAuditRepository,
        default_window_hours: int = 24,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._default_window_hours = default_window_hours
        self._clock = clock or (lambda: datetime.now(UTC))

    async def list_events(
        self,
        *,
        limit: int,
        generation_request_id: UUID | None = None,
        event_type: GenerationAuditEventType | None = None,
    ) -> GenerationAuditCollectionResponse:
        try:
            events = await self._repository.list_events(
                limit=limit,
                generation_request_id=generation_request_id,
                event_type=event_type,
            )
        except GenerationAuditRepositoryError as exc:
            raise GenerationAuditUnavailable from exc
        return GenerationAuditCollectionResponse(items=tuple(events), count=len(events))

    async def metrics(
        self,
        *,
        window_hours: int | None = None,
    ) -> GenerationMetricsResponse:
        now = self._now()
        since = now - timedelta(hours=window_hours or self._default_window_hours)
        try:
            events = await self._repository.list_events_since(
                since=since,
                limit=50_000,
            )
            usage = await self._repository.usage_summary(since=since)
        except GenerationAuditRepositoryError as exc:
            raise GenerationAuditUnavailable from exc

        started = self._request_ids(events, GenerationAuditEventType.GENERATION_STARTED)
        succeeded = self._request_ids(
            events,
            GenerationAuditEventType.GENERATION_COMPLETED,
        )
        failed = self._request_ids(events, GenerationAuditEventType.GENERATION_FAILED)
        durations = [
            event.duration_ms
            for event in events
            if event.event_type
            in {
                GenerationAuditEventType.GENERATION_COMPLETED,
                GenerationAuditEventType.GENERATION_FAILED,
            }
            and event.duration_ms is not None
        ]
        error_counts = Counter(
            event.error_category.value
            for event in events
            if event.event_type == GenerationAuditEventType.GENERATION_FAILED
            and event.error_category is not None
        )
        return GenerationMetricsResponse(
            window_start=since,
            window_end=now,
            total_requests=len(started),
            successful_requests=len(started & succeeded),
            failed_requests=len(started & failed),
            active_requests=len(started - succeeded - failed),
            rights_rejections=self._event_count(
                events,
                GenerationAuditEventType.RIGHTS_DENIED,
            ),
            validation_failures=self._event_count(
                events,
                GenerationAuditEventType.VALIDATION_FAILED,
            ),
            usage_rejections=self._event_count(
                events,
                GenerationAuditEventType.USAGE_REJECTED,
            ),
            openai_timeouts=error_counts[GenerationErrorCategory.AI_TIMEOUT.value],
            openai_rate_limits=error_counts[
                GenerationErrorCategory.AI_RATE_LIMIT_ERROR.value
            ],
            average_duration_ms=(
                round(sum(durations) / len(durations)) if durations else None
            ),
            provider_attempts=usage.provider_attempts,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            error_counts=dict(sorted(error_counts.items())),
        )

    @staticmethod
    def _request_ids(
        events: list[GenerationAuditEvent],
        event_type: GenerationAuditEventType,
    ) -> set[UUID]:
        return {
            event.generation_request_id
            for event in events
            if event.event_type == event_type
        }

    @staticmethod
    def _event_count(
        events: list[GenerationAuditEvent],
        event_type: GenerationAuditEventType,
    ) -> int:
        return sum(event.event_type == event_type for event in events)

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("The generation monitoring clock must include a timezone.")
        return value.astimezone(UTC)
