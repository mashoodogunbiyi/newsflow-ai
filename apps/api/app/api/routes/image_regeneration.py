"""Authenticated REST endpoint for private image regeneration."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response, status

from app.api.dependencies import require_csrf_authenticated_session
from app.core.errors import ApplicationError
from app.models.image_generation import ImageGenerationErrorCategory
from app.models.image_regeneration import (
    ImageRegenerationRequest,
    ImageRegenerationResponse,
)
from app.repositories import AuthenticatedSession
from app.repositories.article_rights import ArticleRightsRepositoryError
from app.repositories.generated_images import (
    GeneratedImageContextNotFoundError,
    GeneratedImageIdempotencyConflict,
    GeneratedImageRepositoryError,
)
from app.repositories.image_regeneration import (
    ImageRegenerationIdempotencyConflict,
    ImageRegenerationRepositoryError,
)
from app.repositories.linkedin_generation import LinkedInGenerationRepositoryError
from app.security import InMemoryRateLimiter, RateLimitExceeded
from app.services.generated_image_storage import (
    GeneratedImageStorageWorkflowError,
)
from app.services.generation_usage import (
    GenerationConcurrencyLimitExceeded,
    GenerationDuplicateInProgress,
    GenerationLimitExceeded,
    GenerationUsageUnavailable,
)
from app.services.image_regeneration import (
    ImageRegenerationConfigurationError,
    ImageRegenerationContextError,
    ImageRegenerationNotFoundError,
    ImageRegenerationRightsDeniedError,
    ImageRegenerationSafetyDeniedError,
    ImageRegenerationService,
)
from app.services.image_validation import GeneratedImageValidationError
from app.services.openai_image_service import OpenAIImageGenerationError

router = APIRouter(prefix="/api/images", tags=["Generated images"])


def require_image_regeneration_service(request: Request) -> ImageRegenerationService:
    """Return the configured service without exposing backend configuration."""

    service: ImageRegenerationService | None = getattr(
        request.app.state,
        "image_regeneration_service",
        None,
    )
    if service is None:
        raise ApplicationError(
            status_code=503,
            code="image_regeneration_unavailable",
            message="Image regeneration is temporarily unavailable.",
        )
    return service


async def enforce_image_regeneration_rate(
    request: Request,
    owner_id: UUID,
) -> None:
    """Apply the existing per-user burst limit before regeneration."""

    limiter: InMemoryRateLimiter | None = getattr(
        request.app.state,
        "generation_rate_limiter",
        None,
    )
    if limiter is None:
        raise ApplicationError(
            status_code=503,
            code="image_regeneration_unavailable",
            message="Image regeneration is temporarily unavailable.",
        )
    try:
        await limiter.check(str(owner_id))
    except RateLimitExceeded as exc:
        raise ApplicationError(
            status_code=429,
            code="generation_limit_exceeded",
            message="Too many generation requests. Please try again later.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc


def _raise_provider_error(exc: OpenAIImageGenerationError) -> NoReturn:
    if exc.category == ImageGenerationErrorCategory.TIMEOUT:
        status_code = 504
    elif exc.category == ImageGenerationErrorCategory.DUPLICATE_REQUEST:
        status_code = 409
    elif exc.category in {
        ImageGenerationErrorCategory.RIGHTS_DENIED,
        ImageGenerationErrorCategory.SAFETY_DENIED,
    }:
        status_code = 403
    elif exc.category in {
        ImageGenerationErrorCategory.INVALID_RESPONSE,
        ImageGenerationErrorCategory.MODERATION_BLOCKED,
        ImageGenerationErrorCategory.REQUEST_REJECTED,
    }:
        status_code = 502
    else:
        status_code = 503
    headers = (
        {"Retry-After": str(exc.retry_after_seconds)}
        if exc.retry_after_seconds is not None
        else None
    )
    raise ApplicationError(
        status_code=status_code,
        code=exc.code,
        message=exc.safe_message,
        headers=headers,
    ) from exc


@router.post(
    "/{image_id}/regenerate",
    response_model=ImageRegenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Regenerate a private AI illustration",
    description=(
        "Require an authenticated session and CSRF proof, verify private image "
        "ownership and current source rights, reapply the central sensitive-news "
        "policy, generate through the approved OpenAI image boundary, validate and "
        "privately store a new immutable image version, and preserve its parent "
        "relationship. The original image is never overwritten and the result "
        "requires human review."
    ),
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "CSRF, rights, or safety checks denied the request."},
        404: {"description": "Missing and differently owned images look identical."},
        409: {"description": "The request conflicts or is already in progress."},
        422: {
            "description": "Preferences or the linked generation context are invalid."
        },
        429: {"description": "A per-user generation limit was exceeded."},
        502: {"description": "The provider output failed generation or validation."},
        503: {"description": "Generation, persistence, or storage is unavailable."},
        504: {"description": "The image provider request timed out."},
    },
)
async def regenerate_image(
    image_id: UUID,
    payload: ImageRegenerationRequest,
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_csrf_authenticated_session),
    ],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
            description=(
                "Optional client key that returns the same completed image version "
                "without another provider call."
            ),
        ),
    ] = None,
) -> ImageRegenerationResponse:
    await enforce_image_regeneration_rate(request, active_session.user_id)
    try:
        result = await require_image_regeneration_service(request).regenerate(
            owner_id=active_session.user_id,
            parent_image_id=image_id,
            preferences=payload,
            idempotency_key=idempotency_key,
        )
    except ImageRegenerationNotFoundError as exc:
        raise ApplicationError(
            status_code=404,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except (
        ImageRegenerationRightsDeniedError,
        ImageRegenerationSafetyDeniedError,
    ) as exc:
        raise ApplicationError(
            status_code=403,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except ImageRegenerationContextError as exc:
        raise ApplicationError(
            status_code=422,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except ImageRegenerationIdempotencyConflict as exc:
        raise ApplicationError(
            status_code=409,
            code="idempotency_key_conflict",
            message="The idempotency key cannot be used for this request.",
        ) from exc
    except GeneratedImageContextNotFoundError as exc:
        raise ApplicationError(
            status_code=404,
            code="image_context_not_found",
            message="The requested image was not found.",
        ) from exc
    except GeneratedImageIdempotencyConflict as exc:
        raise ApplicationError(
            status_code=409,
            code="image_storage_idempotency_conflict",
            message="The image request conflicts with an existing result.",
        ) from exc
    except (GenerationLimitExceeded, GenerationConcurrencyLimitExceeded) as exc:
        raise ApplicationError(
            status_code=429,
            code=exc.code,
            message=exc.safe_message,
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except GenerationDuplicateInProgress as exc:
        raise ApplicationError(
            status_code=409,
            code=exc.code,
            message=exc.safe_message,
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except OpenAIImageGenerationError as exc:
        _raise_provider_error(exc)
    except GeneratedImageValidationError as exc:
        raise ApplicationError(
            status_code=502,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except GeneratedImageStorageWorkflowError as exc:
        status_code = 503 if "storage" in exc.code else 502
        raise ApplicationError(
            status_code=status_code,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except ImageRegenerationConfigurationError as exc:
        raise ApplicationError(
            status_code=503,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except (
        GeneratedImageRepositoryError,
        ImageRegenerationRepositoryError,
        LinkedInGenerationRepositoryError,
        ArticleRightsRepositoryError,
        GenerationUsageUnavailable,
    ) as exc:
        raise ApplicationError(
            status_code=503,
            code="image_regeneration_unavailable",
            message="Image regeneration is temporarily unavailable.",
        ) from exc

    response.headers["Cache-Control"] = "private, no-store"
    return result
