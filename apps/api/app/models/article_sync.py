"""Validated article synchronisation jobs, statistics, and API responses."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SyncTriggerType(str, Enum):
    """Supported ways to start the shared synchronisation workflow."""

    SCHEDULED = "scheduled"
    MANUAL = "manual"


class SyncJobStatus(str, Enum):
    """Durable lifecycle states for a synchronisation job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    INTERRUPTED = "interrupted"


TERMINAL_SYNC_STATUSES = {
    SyncJobStatus.COMPLETED,
    SyncJobStatus.FAILED,
    SyncJobStatus.PARTIALLY_COMPLETED,
    SyncJobStatus.INTERRUPTED,
}


def _aware_utc(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone.")
    return value.astimezone(UTC)


class SyncStatistics(BaseModel):
    """Counters recorded for one synchronisation attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    retrieved: int = Field(default=0, ge=0)
    created: int = Field(default=0, ge=0)
    updated: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)
    provider_attempts: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_processed_total(self) -> "SyncStatistics":
        if self.created + self.updated + self.skipped + self.rejected > self.retrieved:
            raise ValueError(
                "Processed article counts cannot exceed retrieved articles."
            )
        return self


class SyncJobRecord(BaseModel):
    """Safe job information stored in PostgreSQL and returned by the API."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: UUID
    provider_id: str = Field(min_length=1, max_length=100)
    trigger_type: SyncTriggerType
    status: SyncJobStatus
    requested_by_user_id: UUID | None = None
    checkpoint_from: datetime | None = None
    checkpoint_candidate: datetime | None = None
    scheduled_for: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    lease_expires_at: datetime | None = None
    statistics: SyncStatistics = Field(default_factory=SyncStatistics)
    error_code: str | None = Field(default=None, max_length=60)
    error_summary: str | None = Field(default=None, max_length=500)
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "checkpoint_from",
        "checkpoint_candidate",
        "scheduled_for",
        "started_at",
        "completed_at",
        "lease_expires_at",
        "created_at",
        "updated_at",
    )
    @classmethod
    def validate_timestamps(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        return _aware_utc(value, getattr(info, "field_name", "timestamp"))


class SyncCheckpoint(BaseModel):
    """Position used only after a completely successful job."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: str = Field(min_length=1, max_length=100)
    last_successful_publication_at: datetime | None = None
    last_successful_completed_at: datetime | None = None
    next_scheduled_at: datetime | None = None

    @field_validator(
        "last_successful_publication_at",
        "last_successful_completed_at",
        "next_scheduled_at",
    )
    @classmethod
    def validate_checkpoint_time(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        return _aware_utc(value, getattr(info, "field_name", "timestamp"))


class SyncJobResponse(BaseModel):
    """Public response without credentials or raw provider data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    provider_id: str
    trigger_type: SyncTriggerType
    status: SyncJobStatus
    articles_retrieved: int
    articles_created: int
    articles_updated: int
    articles_skipped: int
    articles_rejected: int
    error_code: str | None
    error_summary: str | None
    started_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_record(cls, record: SyncJobRecord) -> "SyncJobResponse":
        """Convert the internal record to its safe API shape."""

        return cls(
            id=record.id,
            provider_id=record.provider_id,
            trigger_type=record.trigger_type,
            status=record.status,
            articles_retrieved=record.statistics.retrieved,
            articles_created=record.statistics.created,
            articles_updated=record.statistics.updated,
            articles_skipped=record.statistics.skipped,
            articles_rejected=record.statistics.rejected,
            error_code=record.error_code,
            error_summary=record.error_summary,
            started_at=record.started_at,
            completed_at=record.completed_at,
        )
