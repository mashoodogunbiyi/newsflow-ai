"""Service health endpoints."""

from fastapi import APIRouter

from app.models.health import HealthResponse

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API health",
    description="Confirm that the NewsFlow AI API is running and able to respond.",
)
async def health_check() -> HealthResponse:
    """Return the current API availability status."""

    return HealthResponse(status="ok")
