"""Shared HTTP boundary for authenticated LinkedIn draft generation."""

from uuid import UUID

from fastapi import Request

from app.core.errors import ApplicationError
from app.models.generation_preferences import LinkedInGenerationPreferences
from app.models.linkedin_generation import (
    GenerationRequest,
    LinkedInDraft,
    LinkedInGenerationRequest,
)
from app.repositories.article_rights import ArticleRightsRepositoryError
from app.repositories.linkedin_generation import (
    LinkedInGenerationIdempotencyConflict,
    LinkedInGenerationRepositoryError,
)
from app.security import InMemoryRateLimiter, RateLimitExceeded
from app.services.linkedin_generation import (
    GenerationArticleNotFoundError,
    GenerationInsufficientSourceError,
    GenerationProviderConfigurationError,
    GenerationRightsDeniedError,
    InvalidGeneratedDraftError,
    LinkedInGenerationService,
)
from app.services.openai_service import (
    OpenAIInvalidResponseError,
    OpenAIRequestFailure,
    OpenAIServiceError,
    OpenAITimeoutFailure,
)


def require_generation_service(request: Request) -> LinkedInGenerationService:
    """Return the configured service without exposing application internals."""

    service: LinkedInGenerationService | None = getattr(
        request.app.state,
        "linkedin_generation_service",
        None,
    )
    if service is None:
        raise ApplicationError(
            status_code=503,
            code="linkedin_generation_unavailable",
            message="LinkedIn draft generation is temporarily unavailable.",
        )
    return service


async def enforce_generation_limit(request: Request, owner_id: UUID) -> None:
    """Apply the configured per-user request limit before generation."""

    limiter: InMemoryRateLimiter | None = getattr(
        request.app.state,
        "generation_rate_limiter",
        None,
    )
    if limiter is None:
        raise ApplicationError(
            status_code=503,
            code="linkedin_generation_unavailable",
            message="LinkedIn draft generation is temporarily unavailable.",
        )
    try:
        await limiter.check(str(owner_id))
    except RateLimitExceeded as exc:
        raise ApplicationError(
            status_code=429,
            code="linkedin_generation_rate_limited",
            message="Too many generation requests. Please try again later.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc


async def create_generation_resource(
    *,
    request: Request,
    owner_id: UUID,
    payload: LinkedInGenerationRequest | GenerationRequest,
    idempotency_key: str | None,
) -> LinkedInDraft:
    """Validate API controls and delegate all generation logic to NFA-40."""

    await enforce_generation_limit(request, owner_id)
    try:
        return await require_generation_service(request).generate_draft(
            owner_id=owner_id,
            article_id=payload.article_id,
            preferences=LinkedInGenerationPreferences(
                tone=payload.tone,
                post_length=payload.length,
            ),
            idempotency_key=idempotency_key,
        )
    except GenerationArticleNotFoundError as exc:
        raise ApplicationError(
            status_code=404,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except GenerationRightsDeniedError as exc:
        raise ApplicationError(
            status_code=403,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except GenerationInsufficientSourceError as exc:
        raise ApplicationError(
            status_code=422,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except InvalidGeneratedDraftError as exc:
        raise ApplicationError(
            status_code=502,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except GenerationProviderConfigurationError as exc:
        raise ApplicationError(
            status_code=503,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except OpenAITimeoutFailure as exc:
        raise ApplicationError(
            status_code=504,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except (OpenAIInvalidResponseError, OpenAIRequestFailure) as exc:
        raise ApplicationError(
            status_code=502,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except OpenAIServiceError as exc:
        raise ApplicationError(
            status_code=503,
            code=exc.code,
            message=exc.safe_message,
        ) from exc
    except LinkedInGenerationIdempotencyConflict as exc:
        raise ApplicationError(
            status_code=409,
            code="idempotency_key_conflict",
            message="The idempotency key has already been used for another request.",
        ) from exc
    except (
        LinkedInGenerationRepositoryError,
        ArticleRightsRepositoryError,
    ) as exc:
        raise ApplicationError(
            status_code=503,
            code="linkedin_generation_unavailable",
            message="LinkedIn draft generation is temporarily unavailable.",
        ) from exc
