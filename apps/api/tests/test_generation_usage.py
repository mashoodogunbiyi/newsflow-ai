"""NFA-43 generation usage limit and lifecycle tests."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.models.ai import AITokenUsage
from app.models.generation_usage import (
    GenerationErrorCategory,
    GenerationUsageAttempt,
)
from app.repositories.generation_usage import (
    DuplicateGenerationInProgress,
    GenerationConcurrencyLimitReached,
    GenerationDailyLimitReached,
    GenerationUsageRepositoryError,
)
from app.services.generation_usage import (
    GenerationConcurrencyLimitExceeded,
    GenerationDuplicateInProgress,
    GenerationLimitExceeded,
    GenerationUsageService,
    GenerationUsageUnavailable,
)

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
OWNER_ID = UUID("43000000-0000-4000-8000-000000000001")
FINGERPRINT = "a" * 64


def run(coroutine):
    return asyncio.run(coroutine)


class RecordingRepository:
    def __init__(self, reserve_failure: Exception | None = None) -> None:
        self.reserve_failure = reserve_failure
        self.reservations: list[dict[str, object]] = []
        self.completed: list[dict[str, object]] = []
        self.failed: list[dict[str, object]] = []

    async def reserve_attempt(self, **values: object) -> GenerationUsageAttempt:
        self.reservations.append(values)
        if self.reserve_failure is not None:
            raise self.reserve_failure
        return GenerationUsageAttempt(
            id=uuid4(),
            owner_id=values["owner_id"],
            request_fingerprint=values["request_fingerprint"],
            created_at=values["now"],
            expires_at=values["expires_at"],
        )

    async def complete_attempt(self, **values: object) -> None:
        self.completed.append(values)

    async def fail_attempt(self, **values: object) -> None:
        self.failed.append(values)


def service(repository: RecordingRepository) -> GenerationUsageService:
    return GenerationUsageService(
        repository=repository,
        daily_limit=50,
        concurrent_limit=2,
        attempt_timeout=timedelta(minutes=3),
        retention=timedelta(days=90),
        clock=lambda: NOW,
    )


def test_reservation_passes_configured_shared_limits_and_utc_boundaries() -> None:
    repository = RecordingRepository()

    attempt = run(
        service(repository).start_attempt(
            owner_id=OWNER_ID,
            request_fingerprint=FINGERPRINT,
        )
    )

    assert attempt.owner_id == OWNER_ID
    assert repository.reservations == [
        {
            "owner_id": OWNER_ID,
            "request_fingerprint": FINGERPRINT,
            "now": NOW,
            "day_started_at": datetime(2026, 10, 30, tzinfo=UTC),
            "day_ends_at": datetime(2026, 10, 31, tzinfo=UTC),
            "expires_at": NOW + timedelta(minutes=3),
            "retention_started_at": NOW - timedelta(days=90),
            "daily_limit": 50,
            "concurrent_limit": 2,
        }
    ]


@pytest.mark.parametrize(
    ("repository_error", "service_error", "code"),
    [
        (
            GenerationDailyLimitReached(43_200),
            GenerationLimitExceeded,
            "generation_limit_exceeded",
        ),
        (
            GenerationConcurrencyLimitReached(30),
            GenerationConcurrencyLimitExceeded,
            "generation_concurrency_limit",
        ),
        (
            DuplicateGenerationInProgress(25),
            GenerationDuplicateInProgress,
            "generation_in_progress",
        ),
    ],
)
def test_limit_and_duplicate_failures_are_safe_and_include_retry_delay(
    repository_error: Exception,
    service_error: type[Exception],
    code: str,
) -> None:
    usage = service(RecordingRepository(repository_error))

    with pytest.raises(service_error) as error:
        run(
            usage.start_attempt(
                owner_id=OWNER_ID,
                request_fingerprint=FINGERPRINT,
            )
        )

    assert error.value.code == code
    assert error.value.retry_after_seconds > 0
    assert str(OWNER_ID) not in str(error.value)


def test_repository_failure_fails_closed_before_provider_access() -> None:
    usage = service(
        RecordingRepository(GenerationUsageRepositoryError("private db detail"))
    )

    with pytest.raises(GenerationUsageUnavailable) as error:
        run(
            usage.start_attempt(
                owner_id=OWNER_ID,
                request_fingerprint=FINGERPRINT,
            )
        )

    assert error.value.code == "generation_usage_unavailable"
    assert "private" not in str(error.value)


def test_success_and_failure_record_tokens_status_and_safe_category(
    caplog: pytest.LogCaptureFixture,
) -> None:
    repository = RecordingRepository()
    usage = service(repository)
    caplog.set_level(logging.INFO)
    attempt = run(
        usage.start_attempt(
            owner_id=OWNER_ID,
            request_fingerprint=FINGERPRINT,
        )
    )
    tokens = AITokenUsage(input_tokens=120, output_tokens=80, total_tokens=200)
    generation_id = uuid4()

    run(
        usage.complete_attempt(
            attempt=attempt,
            generation_run_id=generation_id,
            model_identifier="test-model",
            token_usage=tokens,
        )
    )
    run(
        usage.fail_attempt(
            attempt=attempt,
            category=GenerationErrorCategory.AI_TIMEOUT,
        )
    )

    assert repository.completed[0]["generation_run_id"] == generation_id
    assert repository.completed[0]["token_usage"] == tokens
    assert repository.failed[0]["category"] == GenerationErrorCategory.AI_TIMEOUT
    assert "generation_usage_completed" in caplog.text
    assert caplog.records[-1].error_category == "ai_timeout"
    assert str(OWNER_ID) not in caplog.text
    assert FINGERPRINT not in caplog.text
