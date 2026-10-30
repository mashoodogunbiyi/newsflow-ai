"""NFA-45 generation audit and aggregate monitoring tests."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.models.generation_audit import (
    GenerationAuditEvent,
    GenerationAuditEventCreate,
    GenerationAuditEventType,
    GenerationUsageSummary,
)
from app.models.generation_usage import GenerationErrorCategory
from app.services.generation_audit import GenerationAuditService
from app.services.generation_monitoring import GenerationMonitoringService

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
USER_ID = UUID("45000000-0000-4000-8000-000000000001")
ARTICLE_ID = UUID("45000000-0000-4000-8000-000000000002")


def run(coroutine):
    return asyncio.run(coroutine)


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self.events: list[GenerationAuditEvent] = []
        self.deleted_before: list[datetime] = []
        self.usage = GenerationUsageSummary(
            provider_attempts=2,
            input_tokens=300,
            output_tokens=180,
            total_tokens=480,
        )

    async def record_event(
        self,
        event: GenerationAuditEventCreate,
    ) -> GenerationAuditEvent:
        saved = GenerationAuditEvent(id=uuid4(), **event.model_dump())
        self.events.append(saved)
        return saved

    async def delete_before(self, cutoff: datetime) -> int:
        self.deleted_before.append(cutoff)
        retained = [event for event in self.events if event.occurred_at >= cutoff]
        deleted = len(self.events) - len(retained)
        self.events = retained
        return deleted

    async def list_events(
        self,
        *,
        limit: int,
        generation_request_id: UUID | None = None,
        event_type: GenerationAuditEventType | None = None,
    ) -> list[GenerationAuditEvent]:
        events = self.events
        if generation_request_id is not None:
            events = [
                event
                for event in events
                if event.generation_request_id == generation_request_id
            ]
        if event_type is not None:
            events = [event for event in events if event.event_type == event_type]
        return list(reversed(events))[:limit]

    async def list_events_since(
        self,
        *,
        since: datetime,
        limit: int,
    ) -> list[GenerationAuditEvent]:
        return [event for event in self.events if event.occurred_at >= since][:limit]

    async def usage_summary(self, *, since: datetime) -> GenerationUsageSummary:
        del since
        return self.usage


def test_lifecycle_events_share_one_request_id_and_record_duration() -> None:
    clock = MutableClock(NOW)
    repository = InMemoryAuditRepository()
    service = GenerationAuditService(
        repository=repository,
        retention=timedelta(days=90),
        clock=clock,
    )

    context = run(service.start_request(user_id=USER_ID, article_id=ARTICLE_ID))
    run(
        service.record_rights_decision(
            context=context,
            allowed=True,
            decision="permitted",
        )
    )
    run(
        service.record_validation(
            context=context,
            passed=True,
            validation_status="review_required",
            prompt_version="linkedin_post_v1",
        )
    )
    clock.value = NOW + timedelta(milliseconds=425)
    run(
        service.complete_request(
            context=context,
            generation_run_id=uuid4(),
            usage_event_id=uuid4(),
            model_identifier="approved-model",
            prompt_version="linkedin_post_v1",
        )
    )

    assert {event.generation_request_id for event in repository.events} == {
        context.generation_request_id
    }
    assert [event.event_type for event in repository.events] == [
        GenerationAuditEventType.GENERATION_STARTED,
        GenerationAuditEventType.RIGHTS_VERIFIED,
        GenerationAuditEventType.VALIDATION_PASSED,
        GenerationAuditEventType.GENERATION_COMPLETED,
    ]
    assert repository.events[-1].duration_ms == 425
    assert repository.deleted_before == [NOW - timedelta(days=90)]


def test_failure_and_rejection_events_use_safe_categories() -> None:
    repository = InMemoryAuditRepository()
    service = GenerationAuditService(
        repository=repository,
        retention=timedelta(days=90),
        clock=lambda: NOW,
    )
    context = run(service.start_request(user_id=USER_ID, article_id=ARTICLE_ID))

    run(
        service.record_rights_decision(
            context=context,
            allowed=False,
            decision="operation_restricted",
        )
    )
    run(
        service.record_usage_rejection(
            context=context,
            category=GenerationErrorCategory.GENERATION_DAILY_LIMIT,
        )
    )
    run(
        service.fail_request(
            context=context,
            category=GenerationErrorCategory.GENERATION_RIGHTS_DENIED,
        )
    )

    assert repository.events[1].event_type == GenerationAuditEventType.RIGHTS_DENIED
    assert repository.events[2].event_type == GenerationAuditEventType.USAGE_REJECTED
    assert repository.events[3].error_category == (
        GenerationErrorCategory.GENERATION_RIGHTS_DENIED
    )


def test_audit_logs_and_models_do_not_contain_sensitive_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_values = (
        "sk-private-api-key",
        "private prompt instructions",
        "private article body",
        "private generated draft",
    )
    repository = InMemoryAuditRepository()
    service = GenerationAuditService(
        repository=repository,
        retention=timedelta(days=90),
        clock=lambda: NOW,
    )
    caplog.set_level(logging.INFO)

    context = run(service.start_request(user_id=USER_ID, article_id=ARTICLE_ID))
    run(
        service.fail_request(
            context=context,
            category=GenerationErrorCategory.AI_TIMEOUT,
        )
    )

    serialised = (
        " ".join(event.model_dump_json() for event in repository.events) + caplog.text
    )
    for private_value in private_values:
        assert private_value not in serialised
    assert "prompt" not in repository.events[0].model_fields_set
    assert "draft" not in repository.events[0].model_fields_set
    assert "article_content" not in repository.events[0].model_fields_set


def test_metrics_aggregate_results_durations_tokens_and_error_categories() -> None:
    clock = MutableClock(NOW)
    repository = InMemoryAuditRepository()
    audit = GenerationAuditService(
        repository=repository,
        retention=timedelta(days=90),
        clock=clock,
    )

    successful = run(audit.start_request(user_id=USER_ID, article_id=ARTICLE_ID))
    clock.value = NOW + timedelta(milliseconds=100)
    run(
        audit.complete_request(
            context=successful,
            generation_run_id=uuid4(),
            usage_event_id=uuid4(),
            model_identifier="approved-model",
            prompt_version="linkedin_post_v1",
        )
    )
    failed = run(audit.start_request(user_id=USER_ID, article_id=ARTICLE_ID))
    run(
        audit.record_validation(
            context=failed,
            passed=False,
            validation_status="grounding_rejected",
        )
    )
    clock.value = NOW + timedelta(milliseconds=300)
    run(
        audit.fail_request(
            context=failed,
            category=GenerationErrorCategory.AI_TIMEOUT,
        )
    )

    monitoring = GenerationMonitoringService(
        repository=repository,
        clock=clock,
    )
    metrics = run(monitoring.metrics(window_hours=24))

    assert metrics.total_requests == 2
    assert metrics.successful_requests == 1
    assert metrics.failed_requests == 1
    assert metrics.validation_failures == 1
    assert metrics.openai_timeouts == 1
    assert metrics.average_duration_ms == 150
    assert metrics.provider_attempts == 2
    assert metrics.total_tokens == 480
    assert metrics.error_counts == {"ai_timeout": 1}
    assert "user_id" not in metrics.model_dump()
    assert "article_id" not in metrics.model_dump()
