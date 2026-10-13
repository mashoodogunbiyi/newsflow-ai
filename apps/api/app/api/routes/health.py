"""Service health and database readiness endpoints."""

from fastapi import APIRouter, Request

from app.core.errors import ApplicationError
from app.database import DatabaseConnection, DatabaseConnectionError
from app.models.health import HealthResponse, ReadinessResponse

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


def _get_database(request: Request) -> DatabaseConnection:
    database: DatabaseConnection | None = getattr(
        request.app.state,
        "database",
        None,
    )
    if database is None:
        raise ApplicationError(
            status_code=503,
            code="database_unavailable",
            message="The database is not available.",
        )
    return database


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Check API readiness",
    description="Confirm that the API can connect to its PostgreSQL database.",
    responses={
        503: {
            "description": "PostgreSQL is unavailable.",
        }
    },
)
async def readiness_check(request: Request) -> ReadinessResponse:
    """Return readiness only after a successful PostgreSQL query."""

    database = _get_database(request)
    try:
        await database.check_connection()
    except DatabaseConnectionError as exc:
        raise ApplicationError(
            status_code=503,
            code="database_unavailable",
            message="The database is temporarily unavailable.",
        ) from exc

    return ReadinessResponse(status="ready", database="connected")
