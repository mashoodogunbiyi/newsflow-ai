"""Administrator-only generation audit and aggregate monitoring endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import require_authenticated_session
from app.core.errors import ApplicationError
from app.models.generation_audit import (
    GenerationAuditCollectionResponse,
    GenerationAuditEventType,
    GenerationMetricsResponse,
)
from app.repositories import AuthenticatedSession
from app.repositories.article_sync import (
    ArticleSyncRepository,
    ArticleSyncRepositoryError,
)
from app.services.generation_audit import GenerationAuditUnavailable
from app.services.generation_monitoring import GenerationMonitoringService

router = APIRouter(prefix="/api/admin/generations", tags=["generation monitoring"])


def _service(request: Request) -> GenerationMonitoringService:
    service: GenerationMonitoringService | None = getattr(
        request.app.state,
        "generation_monitoring_service",
        None,
    )
    if service is None:
        raise _unavailable()
    return service


async def _authorise(
    request: Request,
    session: AuthenticatedSession,
) -> GenerationMonitoringService:
    await _require_generation_admin(request, session)
    return _service(request)


async def _require_generation_admin(
    request: Request,
    session: AuthenticatedSession,
) -> None:
    repository: ArticleSyncRepository | None = getattr(
        request.app.state,
        "article_sync_repository",
        None,
    )
    if repository is None:
        raise _unavailable()
    try:
        is_admin = await repository.user_is_admin(session.user_id)
    except ArticleSyncRepositoryError as exc:
        raise _unavailable() from exc
    if not is_admin:
        raise ApplicationError(
            status_code=403,
            code="administrator_required",
            message="Administrator access is required.",
        )


@router.get(
    "/audit",
    response_model=GenerationAuditCollectionResponse,
    summary="List safe generation lifecycle events",
)
async def list_generation_audit_events(
    request: Request,
    session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    generation_request_id: UUID | None = None,
    event_type: GenerationAuditEventType | None = None,
) -> GenerationAuditCollectionResponse:
    service = await _authorise(request, session)
    try:
        return await service.list_events(
            limit=limit,
            generation_request_id=generation_request_id,
            event_type=event_type,
        )
    except GenerationAuditUnavailable as exc:
        raise _unavailable() from exc


@router.get(
    "/metrics",
    response_model=GenerationMetricsResponse,
    summary="Read aggregate generation metrics",
)
async def get_generation_metrics(
    request: Request,
    session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
    window_hours: Annotated[int | None, Query(ge=1, le=168)] = None,
) -> GenerationMetricsResponse:
    service = await _authorise(request, session)
    try:
        return await service.metrics(window_hours=window_hours)
    except GenerationAuditUnavailable as exc:
        raise _unavailable() from exc


def _unavailable() -> ApplicationError:
    return ApplicationError(
        status_code=503,
        code="generation_monitoring_unavailable",
        message="Generation monitoring is temporarily unavailable.",
    )
