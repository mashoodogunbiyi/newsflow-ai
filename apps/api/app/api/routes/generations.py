"""Frontend-facing REST endpoint for LinkedIn post generation."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response, status

from app.api.dependencies import require_csrf_authenticated_session
from app.api.generation import create_generation_resource
from app.models.linkedin_generation import (
    GenerationRequest,
    GenerationResponse,
    LinkedInDraft,
)
from app.repositories import AuthenticatedSession

router = APIRouter(prefix="/api/generations", tags=["Generations"])


def _public_response(draft: LinkedInDraft) -> GenerationResponse:
    """Return only fields required by the frontend generation experience."""

    return GenerationResponse(
        generation_id=draft.generation_id,
        article_id=draft.source.article_id,
        draft=draft.draft,
        tone=draft.tone,
        length=draft.length,
        source_title=draft.source.title,
        source_name=draft.source.source_name,
        source_url=draft.source.source_url,
        source_attribution=draft.source.attribution_text,
        status=draft.status,
        review_required=draft.review_required,
        grounding_status=draft.grounding.status,
        validation_warnings=draft.grounding.warnings,
        grounding_policy_version=draft.grounding.policy_version,
        created_at=draft.created_at,
    )


@router.post(
    "",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a LinkedIn post draft",
    description=(
        "Create a private LinkedIn post draft for the authenticated user. The "
        "request requires the HTTP-only session cookie and matching CSRF header. "
        "Before OpenAI is called, the reused NFA-40 service loads the selected "
        "PostgreSQL article and verifies current display and AI-processing rights. "
        "A per-user request limit applies. Deterministic factual-grounding checks "
        "run before a draft is saved. The result requires human review, is never "
        "described as factually verified, and is never published automatically."
    ),
    responses={
        400: {"description": "The request cannot be processed."},
        401: {"description": "Authentication is missing or invalid."},
        403: {"description": "CSRF failed or article generation is not permitted."},
        404: {"description": "The selected article was not found."},
        409: {"description": "The idempotency key conflicts with another request."},
        422: {"description": "The request or permitted source information is invalid."},
        429: {"description": "The per-user generation limit was exceeded."},
        502: {"description": "The AI provider failed or returned an invalid result."},
        503: {"description": "Generation, storage, or OpenAI is unavailable."},
        504: {"description": "The upstream AI request timed out."},
    },
)
async def create_generation(
    payload: GenerationRequest,
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
                "Optional client key used to return the same completed generation "
                "rather than create a duplicate."
            ),
        ),
    ] = None,
) -> GenerationResponse:
    draft = await create_generation_resource(
        request=request,
        owner_id=active_session.user_id,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    response.headers["Cache-Control"] = "no-store"
    return _public_response(draft)
