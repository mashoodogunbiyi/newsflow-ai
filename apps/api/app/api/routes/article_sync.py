"""Protected manual article synchronisation and safe job-status routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.api.dependencies import (
    require_authenticated_session,
    require_csrf_authenticated_session,
)
from app.core.errors import ApplicationError
from app.models.article_sync import SyncJobResponse, SyncTriggerType
from app.repositories import AuthenticatedSession
from app.repositories.article_sync import (
    ActiveSyncJobError,
    ArticleSyncRepository,
    ArticleSyncRepositoryError,
)
from app.security import InMemoryRateLimiter, RateLimitExceeded
from app.services.article_sync import (
    ArticleSyncJobNotFoundError,
    ArticleSyncService,
    ArticleSyncUnavailableError,
)

router = APIRouter(prefix="/api/v1/admin/articles", tags=["article synchronisation"])


def _sync_service(request: Request) -> ArticleSyncService:
    service: ArticleSyncService | None = getattr(
        request.app.state,
        "article_sync_service",
        None,
    )
    if service is None:
        raise ApplicationError(
            status_code=503,
            code="article_sync_unavailable",
            message="Article synchronisation is unavailable.",
        )
    return service


async def _require_admin(
    request: Request,
    session: AuthenticatedSession,
) -> None:
    repository: ArticleSyncRepository | None = getattr(
        request.app.state,
        "article_sync_repository",
        None,
    )
    if repository is None:
        raise ApplicationError(
            status_code=503,
            code="article_sync_unavailable",
            message="Article synchronisation is unavailable.",
        )
    try:
        is_admin = await repository.user_is_admin(session.user_id)
    except ArticleSyncRepositoryError as exc:
        raise ApplicationError(
            status_code=503,
            code="article_sync_unavailable",
            message="Article synchronisation is unavailable.",
        ) from exc
    if not is_admin:
        raise ApplicationError(
            status_code=403,
            code="administrator_required",
            message="Administrator access is required.",
        )


@router.post(
    "/sync",
    response_model=SyncJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an authorised article synchronisation job",
)
async def start_manual_sync(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Annotated[
        AuthenticatedSession,
        Depends(require_csrf_authenticated_session),
    ],
) -> SyncJobResponse:
    """Create a durable job and run it after returning the initial response."""

    await _require_admin(request, session)
    limiter: InMemoryRateLimiter | None = getattr(
        request.app.state,
        "manual_sync_rate_limiter",
        None,
    )
    if limiter is None:
        raise ApplicationError(
            status_code=503,
            code="article_sync_unavailable",
            message="Article synchronisation is unavailable.",
        )
    try:
        await limiter.check(f"admin:{session.user_id}")
    except RateLimitExceeded as exc:
        raise ApplicationError(
            status_code=429,
            code="article_sync_rate_limited",
            message="Too many synchronisation requests. Please try again later.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    service = _sync_service(request)
    try:
        job = await service.start_job(
            trigger_type=SyncTriggerType.MANUAL,
            requested_by_user_id=session.user_id,
        )
    except ActiveSyncJobError as exc:
        raise ApplicationError(
            status_code=409,
            code="article_sync_already_running",
            message="A synchronisation job is already active.",
        ) from exc
    except ArticleSyncUnavailableError as exc:
        raise ApplicationError(
            status_code=503,
            code="article_sync_source_disabled",
            message="The configured news source is not authorised for synchronisation.",
        ) from exc
    except ArticleSyncRepositoryError as exc:
        raise ApplicationError(
            status_code=503,
            code="article_sync_unavailable",
            message="Article synchronisation is unavailable.",
        ) from exc

    background_tasks.add_task(service.run_job, job.id)
    return SyncJobResponse.from_record(job)


@router.get(
    "/sync/{job_id}",
    response_model=SyncJobResponse,
    summary="Read an article synchronisation job",
)
async def get_sync_job(
    job_id: UUID,
    request: Request,
    session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> SyncJobResponse:
    """Return safe statistics to an authenticated administrator."""

    await _require_admin(request, session)
    try:
        job = await _sync_service(request).get_job(job_id)
    except ArticleSyncJobNotFoundError as exc:
        raise ApplicationError(
            status_code=404,
            code="article_sync_job_not_found",
            message="The synchronisation job was not found.",
        ) from exc
    except ArticleSyncRepositoryError as exc:
        raise ApplicationError(
            status_code=503,
            code="article_sync_unavailable",
            message="Article synchronisation is unavailable.",
        ) from exc
    return SyncJobResponse.from_record(job)
