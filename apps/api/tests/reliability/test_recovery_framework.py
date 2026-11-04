"""NFA-79 cross-cutting reliability, health, logging, and recovery tests."""

import asyncio
import logging
import re

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.core.reliability import (
    FailureDisposition,
    ReliabilityDependency,
    build_reliability_policy,
)
from app.database import DatabaseConnectionError
from app.main import create_app
from app.services.content_deletion import RetentionRunResult
from app.services.recovery import RecoveryOperationError, ReliabilityRecoveryService


def run(coroutine):
    return asyncio.run(coroutine)


def settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        database_url=SecretStr(
            "postgresql://test-user:test-password@localhost:5432/test-newsflow"
        ),
        **overrides,
    )


class StubDatabase:
    def __init__(self, *, fail_after_checks: int | None = None) -> None:
        self.checks = 0
        self.fail_after_checks = fail_after_checks

    async def check_connection(self) -> None:
        self.checks += 1
        if self.fail_after_checks is not None and self.checks > self.fail_after_checks:
            raise DatabaseConnectionError("private database detail")


class RecoveryWorker:
    def __init__(
        self,
        *,
        outcome: RetentionRunResult | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.outcome = outcome or RetentionRunResult(0, 0, 0)
        self.failure = failure
        self.limits: list[int] = []

    async def run_retention(self, *, limit: int = 100) -> RetentionRunResult:
        self.limits.append(limit)
        if self.failure is not None:
            raise self.failure
        return self.outcome


def test_policy_identifies_every_critical_dependency_and_preserves_content() -> None:
    review = build_reliability_policy(
        settings(
            database_connect_timeout_seconds=7,
            openai_request_timeout=24,
            openai_max_retries=2,
            image_generation_timeout=90,
            image_generation_max_retries=1,
            article_sync_max_retries=2,
        )
    )
    policies = {item.dependency: item for item in review.dependencies}

    assert set(policies) == set(ReliabilityDependency)
    assert all(item.preserves_existing_content for item in review.dependencies)
    assert policies[ReliabilityDependency.POSTGRESQL].timeout_seconds == 7
    assert policies[ReliabilityDependency.POSTGRESQL].maximum_automatic_retries == 0
    assert policies[ReliabilityDependency.OPENAI_TEXT].timeout_seconds == 24
    assert policies[ReliabilityDependency.OPENAI_TEXT].maximum_automatic_retries == 2
    assert policies[ReliabilityDependency.OPENAI_IMAGE].timeout_seconds == 90
    assert policies[ReliabilityDependency.OPENAI_IMAGE].maximum_automatic_retries == 1
    assert policies[
        ReliabilityDependency.OPENAI_IMAGE
    ].automatic_retryable_failures == ("rate_limit",)
    assert policies[ReliabilityDependency.OPENAI_IMAGE].manual_retry_failures == (
        "temporary_unavailable",
    )
    assert (
        "timeout_with_uncertain_outcome"
        in policies[ReliabilityDependency.OPENAI_IMAGE].non_retryable_failures
    )
    assert policies[ReliabilityDependency.PRIVATE_IMAGE_STORAGE].disposition == (
        FailureDisposition.COMPENSATE_OR_RECONCILE
    )


def test_reconciliation_runs_one_bounded_batch_and_records_safe_totals(
    caplog: pytest.LogCaptureFixture,
) -> None:
    worker = RecoveryWorker(outcome=RetentionRunResult(2, 1, 3))
    service = ReliabilityRecoveryService(worker)

    with caplog.at_level(logging.INFO, logger="app.services.recovery"):
        result = run(
            service.reconcile_private_storage(limit=25, request_id="recovery-123")
        )

    assert worker.limits == [25]
    assert result.objects_completed == 2
    assert result.objects_rescheduled == 1
    assert result.drafts_redacted == 3
    completed = next(
        record
        for record in caplog.records
        if record.getMessage() == "storage_reconciliation_completed"
    )
    assert completed.component == "private_image_storage"
    assert completed.recovery_status == "completed"
    assert completed.request_id == "recovery-123"
    assert completed.counts == {
        "objects_completed": 2,
        "objects_rescheduled": 1,
        "drafts_redacted": 3,
    }


def test_reconciliation_failure_is_safe_and_remains_retryable(
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_detail = "password=private-value object=generated-images/private.png"
    service = ReliabilityRecoveryService(
        RecoveryWorker(failure=RuntimeError(private_detail))
    )

    with caplog.at_level(logging.ERROR, logger="app.services.recovery"):
        with pytest.raises(RecoveryOperationError) as error:
            run(service.reconcile_private_storage(request_id="recovery-456"))

    assert error.value.code == "storage_reconciliation_unavailable"
    assert private_detail not in str(error.value)
    assert private_detail not in caplog.text
    failed = next(
        record
        for record in caplog.records
        if record.getMessage() == "storage_reconciliation_failed"
    )
    assert failed.recovery_status == "retry_required"
    assert failed.error_category == "reconciliation_unavailable"


@pytest.mark.parametrize("limit", [0, 501])
def test_reconciliation_rejects_unbounded_batches(limit: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 500"):
        run(
            ReliabilityRecoveryService(RecoveryWorker()).reconcile_private_storage(
                limit=limit
            )
        )


def test_liveness_and_readiness_are_request_correlated_and_safe() -> None:
    application = create_app(settings=settings(), database=StubDatabase())

    with TestClient(application) as client:
        liveness = client.get("/health")
        readiness = client.get("/ready")

    assert liveness.status_code == 200
    assert liveness.json() == {"status": "ok"}
    assert readiness.status_code == 200
    assert readiness.json() == {
        "status": "ready",
        "database": "connected",
        "configuration": "valid",
    }
    assert re.fullmatch(r"[a-f0-9]{32}", liveness.headers["x-request-id"])
    assert re.fullmatch(r"[a-f0-9]{32}", readiness.headers["x-request-id"])
    assert liveness.headers["x-request-id"] != readiness.headers["x-request-id"]


def test_database_unavailability_returns_safe_correlated_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    application = create_app(
        settings=settings(),
        database=StubDatabase(fail_after_checks=1),
    )

    with caplog.at_level(logging.WARNING, logger="app.core.errors"):
        with TestClient(application) as client:
            response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "database_unavailable",
        "message": "The database is temporarily unavailable.",
    }
    assert "private database detail" not in response.text
    assert "private database detail" not in caplog.text
    failure = next(
        record
        for record in caplog.records
        if record.getMessage() == "api_dependency_failure"
    )
    assert failure.request_id == response.headers["x-request-id"]
    assert failure.component == "backend_api"
    assert failure.error_category == "database_unavailable"
    assert failure.recovery_status == "retry_later"


def test_unexpected_api_failure_does_not_log_private_exception_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_detail = "secret=private-value draft=private-user-content"
    application = create_app(settings=settings(), database=StubDatabase())

    @application.get("/synthetic-reliability-failure")
    async def synthetic_failure() -> None:
        raise RuntimeError(private_detail)

    with caplog.at_level(logging.ERROR, logger="app.core.errors"):
        with TestClient(application, raise_server_exceptions=False) as client:
            response = client.get("/synthetic-reliability-failure")

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "internal_server_error",
        "message": "An unexpected error occurred.",
    }
    assert private_detail not in response.text
    assert private_detail not in caplog.text
    failure = next(
        record
        for record in caplog.records
        if record.getMessage() == "api_request_failed"
    )
    assert failure.request_id == response.headers["x-request-id"]
    assert failure.operation == "get"
    assert failure.error_category == "unexpected_error"
    assert failure.error_code == "RuntimeError"
    assert failure.recovery_status == "investigation_required"
