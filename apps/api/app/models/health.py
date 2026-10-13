"""Health-check response models."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response returned when the API is available."""

    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    """Response returned when the API and PostgreSQL are ready for requests."""

    status: Literal["ready"]
    database: Literal["connected"]
