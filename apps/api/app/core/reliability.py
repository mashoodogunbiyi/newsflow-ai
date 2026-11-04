"""Versioned reliability policy for critical NewsFlow AI dependencies."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings

RELIABILITY_POLICY_VERSION = "reliability_v1"


class ReliabilityDependency(str, Enum):
    """External and stateful components needed by application workflows."""

    POSTGRESQL = "postgresql"
    OPENAI_TEXT = "openai_text"
    OPENAI_IMAGE = "openai_image"
    ARTICLE_PROVIDER = "article_provider"
    PRIVATE_IMAGE_STORAGE = "private_image_storage"
    BACKEND_API = "backend_api"


class FailureDisposition(str, Enum):
    """Safe operation outcome after one dependency fails."""

    FAIL_CLOSED = "fail_closed"
    PRESERVE_AND_RETRY_LATER = "preserve_and_retry_later"
    COMPENSATE_OR_RECONCILE = "compensate_or_reconcile"
    MARK_INTERRUPTED = "mark_interrupted"


class DependencyReliabilityPolicy(BaseModel):
    """Reviewable timeout, retry, and recovery contract for one dependency."""

    dependency: ReliabilityDependency
    timeout_seconds: float | None = Field(default=None, gt=0, le=300)
    maximum_automatic_retries: int = Field(ge=0, le=5)
    automatic_retryable_failures: tuple[str, ...]
    manual_retry_failures: tuple[str, ...]
    non_retryable_failures: tuple[str, ...]
    disposition: FailureDisposition
    preserves_existing_content: bool
    health_signal: str = Field(min_length=1, max_length=120)

    model_config = ConfigDict(extra="forbid", frozen=True)


class ReliabilityPolicyReview(BaseModel):
    """Complete NFA-79 dependency and recovery policy."""

    policy_version: str = RELIABILITY_POLICY_VERSION
    dependencies: tuple[DependencyReliabilityPolicy, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)


def build_reliability_policy(settings: Settings) -> ReliabilityPolicyReview:
    """Build the policy from the same bounded values used by the application."""

    return ReliabilityPolicyReview(
        dependencies=(
            DependencyReliabilityPolicy(
                dependency=ReliabilityDependency.POSTGRESQL,
                timeout_seconds=float(settings.database_connect_timeout_seconds),
                maximum_automatic_retries=0,
                automatic_retryable_failures=(),
                manual_retry_failures=(
                    "connection_unavailable",
                    "transaction_conflict",
                ),
                non_retryable_failures=("invalid_configuration", "constraint_error"),
                disposition=FailureDisposition.FAIL_CLOSED,
                preserves_existing_content=True,
                health_signal="GET /ready executes a bounded PostgreSQL query.",
            ),
            DependencyReliabilityPolicy(
                dependency=ReliabilityDependency.OPENAI_TEXT,
                timeout_seconds=settings.openai_request_timeout,
                maximum_automatic_retries=settings.openai_max_retries,
                automatic_retryable_failures=(
                    "timeout",
                    "rate_limit",
                    "temporary_unavailable",
                ),
                manual_retry_failures=(),
                non_retryable_failures=(
                    "authentication",
                    "quota",
                    "invalid_request",
                    "invalid_response",
                ),
                disposition=FailureDisposition.MARK_INTERRUPTED,
                preserves_existing_content=True,
                health_signal="Generation audit and safe provider failure categories.",
            ),
            DependencyReliabilityPolicy(
                dependency=ReliabilityDependency.OPENAI_IMAGE,
                timeout_seconds=settings.image_generation_timeout,
                maximum_automatic_retries=settings.image_generation_max_retries,
                automatic_retryable_failures=("rate_limit",),
                manual_retry_failures=("temporary_unavailable",),
                non_retryable_failures=(
                    "timeout_with_uncertain_outcome",
                    "authentication",
                    "quota",
                    "invalid_response",
                    "safety_denial",
                    "rights_denial",
                ),
                disposition=FailureDisposition.MARK_INTERRUPTED,
                preserves_existing_content=True,
                health_signal="Image generation run and usage failure evidence.",
            ),
            DependencyReliabilityPolicy(
                dependency=ReliabilityDependency.ARTICLE_PROVIDER,
                timeout_seconds=None,
                maximum_automatic_retries=settings.article_sync_max_retries,
                automatic_retryable_failures=(
                    "timeout",
                    "rate_limit",
                    "temporary_unavailable",
                ),
                manual_retry_failures=(),
                non_retryable_failures=(
                    "authorisation_denied",
                    "invalid_contract",
                    "rights_denied",
                ),
                disposition=FailureDisposition.MARK_INTERRUPTED,
                preserves_existing_content=True,
                health_signal="Protected ingestion health and durable sync job status.",
            ),
            DependencyReliabilityPolicy(
                dependency=ReliabilityDependency.PRIVATE_IMAGE_STORAGE,
                timeout_seconds=None,
                maximum_automatic_retries=0,
                automatic_retryable_failures=(),
                manual_retry_failures=("read_unavailable", "delete_unavailable"),
                non_retryable_failures=("invalid_key", "unsupported_format"),
                disposition=FailureDisposition.COMPENSATE_OR_RECONCILE,
                preserves_existing_content=True,
                health_signal="Durable cleanup jobs and content-free recovery events.",
            ),
            DependencyReliabilityPolicy(
                dependency=ReliabilityDependency.BACKEND_API,
                timeout_seconds=None,
                maximum_automatic_retries=0,
                automatic_retryable_failures=(),
                manual_retry_failures=(
                    "network_interruption",
                    "temporary_unavailable",
                ),
                non_retryable_failures=(
                    "authentication",
                    "authorisation",
                    "validation",
                ),
                disposition=FailureDisposition.PRESERVE_AND_RETRY_LATER,
                preserves_existing_content=True,
                health_signal="Public liveness, readiness, and request correlation.",
            ),
        )
    )
