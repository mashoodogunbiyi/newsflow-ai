"""Protected operational views for the article-ingestion pipeline."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import require_authenticated_session
from app.api.routes.article_sync import _require_admin
from app.core.errors import ApplicationError
from app.models.article_sync import SyncJobResponse
from app.models.ingestion_observability import (
    IngestionHealthResponse,
    IngestionMetricsResponse,
    SyncJobCollectionResponse,
)
from app.repositories import AuthenticatedSession
from app.repositories.article_sync import ArticleSyncRepositoryError
from app.services.article_sync import ArticleSyncJobNotFoundError
from app.services.ingestion_observability import IngestionObservabilityService

router = APIRouter(prefix="/api/admin/sync", tags=["ingestion observability"])


def _service(request: Request) -> IngestionObservabilityService:
    service: IngestionObservabilityService | None = getattr(
        request.app.state,
        "ingestion_observability_service",
        None,
    )
    if service is None:
        raise ApplicationError(
            status_code=503,
            code="ingestion_observability_unavailable",
            message="Ingestion observability is unavailable.",
        )
    return service


async def _authorise(
    request: Request,
    session: AuthenticatedSession,
) -> IngestionObservabilityService:
    await _require_admin(request, session)
    return _service(request)


@router.get(
    "/jobs",
    response_model=SyncJobCollectionResponse,
    summary="List recent ingestion jobs",
)
async def list_ingestion_jobs(
    request: Request,
    session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    provider_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> SyncJobCollectionResponse:
    service = await _authorise(request, session)
    try:
        return await service.list_recent_jobs(
            limit=limit,
            provider_id=provider_id,
        )
    except ArticleSyncRepositoryError as exc:
        raise _unavailable() from exc


@router.get(
    "/jobs/{job_id}",
    response_model=SyncJobResponse,
    summary="Read one ingestion job",
)
async def get_ingestion_job(
    job_id: UUID,
    request: Request,
    session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> SyncJobResponse:
    service = await _authorise(request, session)
    try:
        return await service.get_job(job_id)
    except ArticleSyncJobNotFoundError as exc:
        raise ApplicationError(
            status_code=404,
            code="article_sync_job_not_found",
            message="The synchronisation job was not found.",
        ) from exc
    except ArticleSyncRepositoryError as exc:
        raise _unavailable() from exc


@router.get(
    "/metrics",
    response_model=IngestionMetricsResponse,
    summary="Read aggregate ingestion metrics",
)
async def get_ingestion_metrics(
    request: Request,
    session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
    window_hours: Annotated[int | None, Query(ge=1, le=168)] = None,
) -> IngestionMetricsResponse:
    service = await _authorise(request, session)
    try:
        return await service.metrics(window_hours=window_hours)
    except ArticleSyncRepositoryError as exc:
        raise _unavailable() from exc


@router.get(
    "/health",
    response_model=IngestionHealthResponse,
    summary="Read ingestion health indicators",
)
async def get_ingestion_health(
    request: Request,
    session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> IngestionHealthResponse:
    service = await _authorise(request, session)
    try:
        return await service.health()
    except ArticleSyncRepositoryError as exc:
        raise _unavailable() from exc


def _unavailable() -> ApplicationError:
    return ApplicationError(
        status_code=503,
        code="ingestion_observability_unavailable",
        message="Ingestion observability is unavailable.",
    )
