"""Authenticated endpoints for private LinkedIn draft generation and retrieval."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response, status

from app.api.dependencies import (
    require_authenticated_session,
    require_csrf_authenticated_session,
)
from app.api.generation import create_generation_resource, require_generation_service
from app.core.errors import ApplicationError
from app.models.linkedin_generation import (
    LinkedInDraft,
    LinkedInDraftResponse,
    LinkedInGenerationRequest,
)
from app.repositories import AuthenticatedSession
from app.repositories.linkedin_generation import LinkedInGenerationRepositoryError
from app.services import PrivateResourceNotFoundError

router = APIRouter(prefix="/api/v1/linkedin-drafts", tags=["LinkedIn drafts"])


def _response(draft: LinkedInDraft) -> LinkedInDraftResponse:
    return LinkedInDraftResponse.model_validate(
        draft.model_dump(exclude={"owner_id", "prompt_version", "model_identifier"})
        | {
            "prompt_version": draft.prompt_version,
            "model_identifier": draft.model_identifier,
        }
    )


def _raise_private_not_found(exc: PrivateResourceNotFoundError) -> NoReturn:
    raise ApplicationError(
        status_code=404,
        code="private_resource_not_found",
        message="The requested resource was not found.",
    ) from exc


def _raise_storage_unavailable(
    exc: LinkedInGenerationRepositoryError,
) -> NoReturn:
    raise ApplicationError(
        status_code=503,
        code="linkedin_generation_unavailable",
        message="LinkedIn draft generation is temporarily unavailable.",
    ) from exc


@router.post(
    "",
    response_model=LinkedInDraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a private LinkedIn post draft",
    description=(
        "Require an authenticated session and CSRF proof, load the selected "
        "PostgreSQL article, verify current AI-processing rights, create a bounded "
        "source-grounded OpenAI request, validate the result, and store an "
        "owner-scoped draft for human review. Nothing is published automatically."
    ),
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "CSRF failed or article generation is not permitted."},
        404: {"description": "The selected article was not found."},
        409: {"description": "The idempotency key conflicts with another request."},
        422: {"description": "Inputs or permitted source information are invalid."},
        429: {"description": "The user generation limit was exceeded."},
        502: {"description": "The AI provider returned an invalid response."},
        503: {"description": "Generation, storage, or OpenAI is unavailable."},
    },
)
async def generate_linkedin_draft(
    payload: LinkedInGenerationRequest,
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
        ),
    ] = None,
) -> LinkedInDraftResponse:
    draft = await create_generation_resource(
        request=request,
        owner_id=active_session.user_id,
        payload=payload,
        idempotency_key=idempotency_key,
    )

    response.headers["Cache-Control"] = "no-store"
    return _response(draft)


@router.get(
    "/{draft_id}",
    response_model=LinkedInDraftResponse,
    summary="Retrieve one private generated draft",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Missing and differently owned drafts look identical."},
        503: {"description": "Draft storage is unavailable."},
    },
)
async def get_linkedin_draft(
    draft_id: UUID,
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> LinkedInDraftResponse:
    try:
        draft = await require_generation_service(request).get_draft(
            owner_id=active_session.user_id,
            draft_id=draft_id,
        )
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except LinkedInGenerationRepositoryError as exc:
        _raise_storage_unavailable(exc)

    response.headers["Cache-Control"] = "private, no-store"
    return _response(draft)
