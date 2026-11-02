"""Authenticated endpoints for durable, versioned LinkedIn drafts."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status

from app.api.dependencies import (
    require_authenticated_session,
    require_csrf_authenticated_session,
)
from app.core.errors import ApplicationError
from app.models.saved_draft import (
    CreateSavedDraftRequest,
    PatchSavedDraftRequest,
    SavedDraftCollectionResponse,
    SavedDraftGenerationResponse,
    SavedDraftImageResponse,
    SavedDraftResponse,
    SavedDraftSourceResponse,
    UpdateSavedDraftRequest,
)
from app.repositories import AuthenticatedSession
from app.repositories.saved_drafts import (
    SavedDraft,
    SavedDraftDuplicateError,
    SavedDraftIdempotencyConflict,
    SavedDraftRepositoryError,
    SavedDraftVersionConflict,
)
from app.services import PrivateResourceNotFoundError
from app.services.saved_drafts import SavedDraftService

router = APIRouter(prefix="/api/v1/drafts", tags=["Saved LinkedIn drafts"])


def _service(request: Request) -> SavedDraftService:
    service: SavedDraftService | None = getattr(
        request.app.state,
        "saved_draft_service",
        None,
    )
    if service is None:
        raise ApplicationError(
            status_code=503,
            code="draft_persistence_unavailable",
            message="Draft persistence is temporarily unavailable.",
        )
    return service


def _response(item: SavedDraft) -> SavedDraftResponse:
    selected_image = None
    if item.selected_image is not None:
        selected_image = SavedDraftImageResponse(
            id=item.selected_image.id,
            alt_text=item.selected_image.alt_text,
            mime_type=item.selected_image.mime_type,
            width_px=item.selected_image.width_px,
            height_px=item.selected_image.height_px,
            ai_generated=item.selected_image.ai_generated,
            ai_disclosure_required=item.selected_image.ai_disclosure_required,
        )
    return SavedDraftResponse(
        id=item.id,
        generated_post_id=item.generated_post_id,
        current_post_version_id=item.current_post_version_id,
        selected_image_id=item.selected_image_id,
        selected_image=selected_image,
        title=item.title,
        edited_text=item.edited_text,
        tone=item.tone,
        length=item.length_option,
        status="saved",
        version=item.version,
        source=SavedDraftSourceResponse(
            article_id=item.article_id,
            title=item.source_title,
            url=item.source_url,
            attribution=item.source_attribution,
        ),
        generation=SavedDraftGenerationResponse(
            generation_id=item.source_generation_id,
            original_post_version_id=item.original_post_version_id,
            model_identifier=item.model_identifier,
            prompt_version=item.prompt_version,
            created_at=item.generation_created_at,
        ),
        created_at=item.saved_at,
        updated_at=item.updated_at,
    )


def _raise_private_not_found(exc: PrivateResourceNotFoundError) -> NoReturn:
    raise ApplicationError(
        status_code=404,
        code="private_resource_not_found",
        message="The requested resource was not found.",
    ) from exc


def _raise_storage_unavailable(exc: SavedDraftRepositoryError) -> NoReturn:
    raise ApplicationError(
        status_code=503,
        code="draft_persistence_unavailable",
        message="Draft persistence is temporarily unavailable.",
    ) from exc


@router.post(
    "",
    response_model=SavedDraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save an edited LinkedIn draft",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "CSRF validation failed."},
        404: {"description": "A referenced private resource was not found."},
        409: {"description": "The draft or idempotency key conflicts."},
        503: {"description": "Draft persistence is unavailable."},
    },
)
async def create_saved_draft(
    payload: CreateSavedDraftRequest,
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_csrf_authenticated_session),
    ],
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
) -> SavedDraftResponse:
    try:
        item = await _service(request).create(
            owner_id=active_session.user_id,
            generation_id=payload.generation_id,
            title=payload.title,
            edited_text=payload.edited_text,
            selected_image_id=payload.selected_image_id,
            idempotency_key=idempotency_key,
        )
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except SavedDraftIdempotencyConflict as exc:
        raise ApplicationError(
            status_code=409,
            code="idempotency_key_conflict",
            message="This idempotency key was already used for different content.",
        ) from exc
    except SavedDraftDuplicateError as exc:
        raise ApplicationError(
            status_code=409,
            code="draft_already_saved",
            message="This generated post is already saved.",
        ) from exc
    except SavedDraftRepositoryError as exc:
        _raise_storage_unavailable(exc)

    response.headers["Cache-Control"] = "private, no-store"
    return _response(item)


@router.get(
    "",
    response_model=SavedDraftCollectionResponse,
    summary="List the authenticated user's saved drafts",
    description=(
        "Return only drafts owned by the authenticated user. Results use stable "
        "newest-updated-first ordering with the draft ID as the tie-breaker."
    ),
    responses={
        401: {"description": "Authentication is required."},
        422: {"description": "Pagination parameters are invalid."},
        503: {"description": "Draft persistence is unavailable."},
    },
)
async def list_saved_drafts(
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SavedDraftCollectionResponse:
    try:
        result = await _service(request).list(
            owner_id=active_session.user_id,
            page=page,
            page_size=page_size,
        )
    except SavedDraftRepositoryError as exc:
        _raise_storage_unavailable(exc)

    response.headers["Cache-Control"] = "private, no-store"
    total_pages = (
        (result.total_items + result.page_size - 1) // result.page_size
        if result.total_items
        else 0
    )
    return SavedDraftCollectionResponse(
        items=[_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total_items=result.total_items,
        total_pages=total_pages,
    )


@router.get(
    "/{saved_draft_id}",
    response_model=SavedDraftResponse,
    summary="Read one owned saved draft",
)
async def get_saved_draft(
    saved_draft_id: UUID,
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> SavedDraftResponse:
    try:
        item = await _service(request).get(
            owner_id=active_session.user_id,
            saved_draft_id=saved_draft_id,
        )
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except SavedDraftRepositoryError as exc:
        _raise_storage_unavailable(exc)

    response.headers["Cache-Control"] = "private, no-store"
    return _response(item)


@router.patch(
    "/{saved_draft_id}",
    response_model=SavedDraftResponse,
    summary="Partially update one owned saved draft",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "CSRF validation failed."},
        404: {"description": "A private resource was not found."},
        409: {"description": "The supplied version is stale."},
        422: {"description": "The update body is invalid."},
        503: {"description": "Draft persistence is unavailable."},
    },
)
async def patch_saved_draft(
    saved_draft_id: UUID,
    payload: PatchSavedDraftRequest,
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_csrf_authenticated_session),
    ],
) -> SavedDraftResponse:
    try:
        current = await _service(request).get(
            owner_id=active_session.user_id,
            saved_draft_id=saved_draft_id,
        )
        supplied = payload.model_fields_set
        item = await _service(request).update(
            owner_id=active_session.user_id,
            saved_draft_id=saved_draft_id,
            expected_version=payload.expected_version,
            title=payload.title if "title" in supplied else current.title,
            edited_text=(
                payload.edited_text
                if "edited_text" in supplied and payload.edited_text is not None
                else current.edited_text
            ),
            selected_image_id=(
                payload.selected_image_id
                if "selected_image_id" in supplied
                else current.selected_image_id
            ),
        )
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except SavedDraftVersionConflict as exc:
        raise ApplicationError(
            status_code=409,
            code="draft_version_conflict",
            message="The draft changed after it was loaded. Refresh and try again.",
        ) from exc
    except SavedDraftRepositoryError as exc:
        _raise_storage_unavailable(exc)

    response.headers["Cache-Control"] = "private, no-store"
    return _response(item)


@router.put(
    "/{saved_draft_id}",
    response_model=SavedDraftResponse,
    summary="Update one owned saved draft",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "CSRF validation failed."},
        404: {"description": "A private resource was not found."},
        409: {"description": "The supplied version is stale."},
        503: {"description": "Draft persistence is unavailable."},
    },
)
async def update_saved_draft(
    saved_draft_id: UUID,
    payload: UpdateSavedDraftRequest,
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_csrf_authenticated_session),
    ],
) -> SavedDraftResponse:
    try:
        item = await _service(request).update(
            owner_id=active_session.user_id,
            saved_draft_id=saved_draft_id,
            expected_version=payload.expected_version,
            title=payload.title,
            edited_text=payload.edited_text,
            selected_image_id=payload.selected_image_id,
        )
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except SavedDraftVersionConflict as exc:
        raise ApplicationError(
            status_code=409,
            code="draft_version_conflict",
            message="The draft changed after it was loaded. Refresh and try again.",
        ) from exc
    except SavedDraftRepositoryError as exc:
        _raise_storage_unavailable(exc)

    response.headers["Cache-Control"] = "private, no-store"
    return _response(item)
