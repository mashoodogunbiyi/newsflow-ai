"""Safe API models for article-ingestion operations and health."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.article_sync import SyncJobResponse


class IngestionHealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class SyncJobCollectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[SyncJobResponse]
    count: int = Field(ge=0)


class IngestionMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = True
    window_start: datetime
    window_end: datetime
    total_jobs: int = Field(ge=0)
    completed_jobs: int = Field(ge=0)
    failed_jobs: int = Field(ge=0)
    partially_completed_jobs: int = Field(ge=0)
    interrupted_jobs: int = Field(ge=0)
    active_jobs: int = Field(ge=0)
    articles_retrieved: int = Field(ge=0)
    articles_created: int = Field(ge=0)
    articles_updated: int = Field(ge=0)
    articles_skipped: int = Field(ge=0)
    articles_rejected: int = Field(ge=0)
    provider_attempts: int = Field(ge=0)
    provider_request_failures: int = Field(ge=0)
    database_failures: int = Field(ge=0)
    average_duration_ms: int | None = Field(default=None, ge=0)
    average_provider_duration_ms: int | None = Field(default=None, ge=0)


class IngestionHealthIndicator(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    status: IngestionHealthStatus
    summary: str


class IngestionHealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: IngestionHealthStatus
    checked_at: datetime
    last_successful_sync_at: datetime | None
    consecutive_failures: int = Field(ge=0)
    active_jobs: int = Field(ge=0)
    indicators: list[IngestionHealthIndicator]
