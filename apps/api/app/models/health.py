"""Health-check response models."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response returned when the API is available."""

    status: Literal["ok"]
