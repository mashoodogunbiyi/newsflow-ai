"""Authenticated and owner-scoped private content-library endpoints."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from starlette.responses import PlainTextResponse

from app.api.dependencies import (
    require_authenticated_session,
    require_csrf_authenticated_session,
)
from app.core.errors import ApplicationError
from app.models.library import (
    SaveContentRequest,
    SavedContentCollectionResponse,
    SavedContentResponse,
    UpdateSavedContentRequest,
)
from app.repositories import (
    AuthenticatedSession,
    SavedContent,
    SavedContentConflictError,
    SavedContentRepositoryError,
)
from app.services import PrivateResourceNotFoundError, SavedContentService

router = APIRouter(prefix="/api/v1/library", tags=["Private content library"])


def _saved_content_service(request: Request) -> SavedContentService:
    service: SavedContentService | None = getattr(
        request.app.state,
        "saved_content_service",
        None,
    )
    if service is None:
        raise ApplicationError(
            status_code=503,
            code="content_library_unavailable",
            message="The content library is temporarily unavailable.",
        )
    return service


def _response(item: SavedContent) -> SavedContentResponse:
    return SavedContentResponse(
        id=item.id,
        generated_post_id=item.generated_post_id,
        selected_post_version_id=item.selected_post_version_id,
        selected_image_id=item.selected_image_id,
        library_title=item.library_title,
        rendered_text=item.rendered_text,
        source_attribution=item.source_attribution,
        saved_at=item.saved_at,
        updated_at=item.updated_at,
    )


def _raise_private_not_found(exc: PrivateResourceNotFoundError) -> NoReturn:
    raise ApplicationError(
        status_code=404,
        code="private_resource_not_found",
        message="The requested resource was not found.",
    ) from exc


def _raise_storage_unavailable(exc: SavedContentRepositoryError) -> NoReturn:
    raise ApplicationError(
        status_code=503,
        code="content_library_unavailable",
        message="The content library is temporarily unavailable.",
    ) from exc


@router.post(
    "/items",
    response_model=SavedContentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save an owned generated post",
    description=(
        "Save a generated post in the authenticated user's private library. "
        "Ownership comes only from the active session, and every referenced "
        "post, version, and image must belong to that owner."
    ),
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "CSRF validation failed."},
        404: {"description": "The private resource was not found for this user."},
        409: {"description": "The generated post is already saved."},
        503: {"description": "The content library is unavailable."},
    },
)
async def save_item(
    payload: SaveContentRequest,
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_csrf_authenticated_session),
    ],
) -> SavedContentResponse:
    try:
        item = await _saved_content_service(request).save_item(
            owner_id=active_session.user_id,
            generated_post_id=payload.generated_post_id,
            selected_post_version_id=payload.selected_post_version_id,
            selected_image_id=payload.selected_image_id,
            library_title=payload.library_title,
        )
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except SavedContentConflictError as exc:
        raise ApplicationError(
            status_code=409,
            code="saved_content_conflict",
            message="This generated post is already saved.",
        ) from exc
    except SavedContentRepositoryError as exc:
        _raise_storage_unavailable(exc)

    response.headers["Cache-Control"] = "no-store"
    return _response(item)


@router.get(
    "/items",
    response_model=SavedContentCollectionResponse,
    summary="List the authenticated user's saved content",
    description=(
        "Return only non-deleted content owned by the authenticated session user."
    ),
    responses={
        401: {"description": "Authentication is required."},
        503: {"description": "The content library is unavailable."},
    },
)
async def list_items(
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> SavedContentCollectionResponse:
    try:
        items = await _saved_content_service(request).list_items(
            owner_id=active_session.user_id
        )
    except SavedContentRepositoryError as exc:
        _raise_storage_unavailable(exc)

    response.headers["Cache-Control"] = "no-store"
    return SavedContentCollectionResponse(items=[_response(item) for item in items])


@router.get(
    "/items/{item_id}",
    response_model=SavedContentResponse,
    summary="Read one owned saved item",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Missing and differently owned items look identical."},
        503: {"description": "The content library is unavailable."},
    },
)
async def get_item(
    item_id: UUID,
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> SavedContentResponse:
    try:
        item = await _saved_content_service(request).get_item(
            owner_id=active_session.user_id,
            item_id=item_id,
        )
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except SavedContentRepositoryError as exc:
        _raise_storage_unavailable(exc)

    response.headers["Cache-Control"] = "no-store"
    return _response(item)


@router.patch(
    "/items/{item_id}",
    response_model=SavedContentResponse,
    summary="Rename one owned saved item",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "CSRF validation failed."},
        404: {"description": "Missing and differently owned items look identical."},
        503: {"description": "The content library is unavailable."},
    },
)
async def update_item(
    item_id: UUID,
    payload: UpdateSavedContentRequest,
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_csrf_authenticated_session),
    ],
) -> SavedContentResponse:
    try:
        item = await _saved_content_service(request).update_title(
            owner_id=active_session.user_id,
            item_id=item_id,
            library_title=payload.library_title,
        )
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except SavedContentRepositoryError as exc:
        _raise_storage_unavailable(exc)

    response.headers["Cache-Control"] = "no-store"
    return _response(item)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one owned saved item",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "CSRF validation failed."},
        404: {"description": "Missing and differently owned items look identical."},
        503: {"description": "The content library is unavailable."},
    },
)
async def delete_item(
    item_id: UUID,
    request: Request,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_csrf_authenticated_session),
    ],
) -> Response:
    try:
        await _saved_content_service(request).delete_item(
            owner_id=active_session.user_id,
            item_id=item_id,
        )
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except SavedContentRepositoryError as exc:
        _raise_storage_unavailable(exc)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/items/{item_id}/export",
    response_class=PlainTextResponse,
    summary="Export one owned saved item",
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Missing and differently owned items look identical."},
        503: {"description": "The content library is unavailable."},
    },
)
async def export_item(
    item_id: UUID,
    request: Request,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> PlainTextResponse:
    try:
        exported_text = await _saved_content_service(request).export_item(
            owner_id=active_session.user_id,
            item_id=item_id,
        )
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except SavedContentRepositoryError as exc:
        _raise_storage_unavailable(exc)

    return PlainTextResponse(
        content=exported_text,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="newsflow-{item_id}.txt"',
        },
    )
