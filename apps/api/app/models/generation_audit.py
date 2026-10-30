"""Content-free generation audit events and aggregate monitoring responses."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.generation_usage import GenerationErrorCategory


class GenerationAuditEventType(StrEnum):
    """Stable event names for the LinkedIn generation lifecycle."""

    GENERATION_STARTED = "generation_started"
    RIGHTS_VERIFIED = "generation_rights_verified"
    RIGHTS_DENIED = "generation_rights_denied"
    USAGE_REJECTED = "generation_usage_rejected"
    VALIDATION_PASSED = "generation_validation_passed"
    VALIDATION_FAILED = "generation_validation_failed"
    GENERATION_COMPLETED = "generation_completed"
    GENERATION_FAILED = "generation_failed"


class GenerationAuditStatus(StrEnum):
    """Safe result states shared by audit events."""

    STARTED = "started"
    PASSED = "passed"
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    FAILED = "failed"


class GenerationAuditContext(BaseModel):
    """Identifiers and start time shared by one request's audit events."""

    generation_request_id: UUID
    user_id: UUID
    article_id: UUID
    started_at: datetime

    model_config = ConfigDict(extra="forbid", frozen=True)


class GenerationAuditEventCreate(BaseModel):
    """One safe event ready for persistence."""

    generation_request_id: UUID
    user_id: UUID
    article_id: UUID
    event_type: GenerationAuditEventType
    status: GenerationAuditStatus
    occurred_at: datetime
    duration_ms: int | None = Field(default=None, ge=0)
    generation_run_id: UUID | None = None
    usage_event_id: UUID | None = None
    model_identifier: str | None = Field(default=None, max_length=200)
    prompt_version: str | None = Field(default=None, max_length=50)
    error_category: GenerationErrorCategory | None = None
    rights_decision: str | None = Field(default=None, max_length=100)
    validation_status: str | None = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid", frozen=True)


class GenerationAuditEvent(GenerationAuditEventCreate):
    """Persisted audit event exposed only through an administrator route."""

    id: UUID


class GenerationAuditCollectionResponse(BaseModel):
    """Bounded administrator view of recent generation events."""

    items: tuple[GenerationAuditEvent, ...]
    count: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class GenerationUsageSummary(BaseModel):
    """Token totals reused from the existing NFA-43 usage records."""

    provider_attempts: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid", frozen=True)


class GenerationMetricsResponse(BaseModel):
    """Identifier-free operational measurements for a bounded time window."""

    window_start: datetime
    window_end: datetime
    total_requests: int = Field(ge=0)
    successful_requests: int = Field(ge=0)
    failed_requests: int = Field(ge=0)
    active_requests: int = Field(ge=0)
    rights_rejections: int = Field(ge=0)
    validation_failures: int = Field(ge=0)
    usage_rejections: int = Field(ge=0)
    openai_timeouts: int = Field(ge=0)
    openai_rate_limits: int = Field(ge=0)
    average_duration_ms: int | None = Field(default=None, ge=0)
    provider_attempts: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    error_counts: dict[str, int]

    model_config = ConfigDict(extra="forbid")
