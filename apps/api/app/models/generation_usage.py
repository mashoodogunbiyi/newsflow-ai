"""Safe operational records for controlled AI generation attempts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenerationUsageStatus(StrEnum):
    """Lifecycle states stored without prompt or generated content."""

    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GenerationErrorCategory(StrEnum):
    """Stable, non-sensitive categories used for operations and support."""

    AI_AUTHENTICATION_ERROR = "ai_authentication_error"
    AI_RATE_LIMIT_ERROR = "ai_rate_limit_error"
    AI_QUOTA_ERROR = "ai_quota_error"
    AI_TIMEOUT = "ai_timeout"
    AI_SERVICE_UNAVAILABLE = "ai_service_unavailable"
    AI_INVALID_RESPONSE = "ai_invalid_response"
    AI_CONFIGURATION_ERROR = "ai_configuration_error"
    GENERATION_VALIDATION_ERROR = "generation_validation_error"
    GENERATION_STORAGE_ERROR = "generation_storage_error"
    GENERATION_ABANDONED = "generation_abandoned"
    GENERATION_UNEXPECTED_ERROR = "generation_unexpected_error"


class GenerationUsageAttempt(BaseModel):
    """One reserved provider attempt owned by one authenticated user."""

    id: UUID
    owner_id: UUID = Field(exclude=True)
    request_fingerprint: str = Field(min_length=64, max_length=64, exclude=True)
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(frozen=True)
