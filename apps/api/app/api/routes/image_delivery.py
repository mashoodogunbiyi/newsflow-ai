"""Authenticated metadata, preview, and download routes for private images."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import require_authenticated_session
from app.core.errors import ApplicationError
from app.models.image_delivery import ImageMetadataResponse, PrivateImageDelivery
from app.repositories import AuthenticatedSession
from app.repositories.generated_images import GeneratedImageRepositoryError
from app.services import PrivateResourceNotFoundError
from app.services.image_delivery import (
    ImageContentUnavailableError,
    ImageDeliveryService,
)

router = APIRouter(prefix="/api/images", tags=["Generated images"])

_PRIVATE_CACHE_HEADERS = {
    "Cache-Control": "private, no-store, max-age=0",
    "Pragma": "no-cache",
    "Vary": "Cookie",
    "X-Content-Type-Options": "nosniff",
}


def require_image_delivery_service(request: Request) -> ImageDeliveryService:
    """Return the private delivery boundary without exposing storage settings."""

    service: ImageDeliveryService | None = getattr(
        request.app.state,
        "image_delivery_service",
        None,
    )
    if service is None:
        raise ApplicationError(
            status_code=503,
            code="image_delivery_unavailable",
            message="Image delivery is temporarily unavailable.",
        )
    return service


def _raise_private_not_found(exc: PrivateResourceNotFoundError) -> NoReturn:
    raise ApplicationError(
        status_code=404,
        code="private_resource_not_found",
        message="The requested image was not found.",
    ) from exc


def _raise_delivery_unavailable(exc: Exception) -> NoReturn:
    raise ApplicationError(
        status_code=503,
        code="image_delivery_unavailable",
        message="The image is temporarily unavailable.",
    ) from exc


async def _metadata(
    *,
    service: ImageDeliveryService,
    owner_id: UUID,
    image_id: UUID,
) -> ImageMetadataResponse:
    try:
        return await service.get_metadata(owner_id=owner_id, image_id=image_id)
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except GeneratedImageRepositoryError as exc:
        _raise_delivery_unavailable(exc)


async def _content(
    *,
    service: ImageDeliveryService,
    owner_id: UUID,
    image_id: UUID,
) -> PrivateImageDelivery:
    try:
        return await service.get_content(owner_id=owner_id, image_id=image_id)
    except PrivateResourceNotFoundError as exc:
        _raise_private_not_found(exc)
    except (GeneratedImageRepositoryError, ImageContentUnavailableError) as exc:
        _raise_delivery_unavailable(exc)


@router.get(
    "/{image_id}",
    response_model=ImageMetadataResponse,
    summary="Read private generated-image metadata",
    description=(
        "Authenticate the caller, apply owner-scoped object authorisation, and "
        "return AI-generation metadata without a storage key, credential, digest, "
        "filesystem path, or public object URL."
    ),
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Missing and differently owned images look identical."},
        503: {"description": "Image metadata is temporarily unavailable."},
    },
)
async def get_image_metadata(
    image_id: UUID,
    request: Request,
    response: Response,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> ImageMetadataResponse:
    metadata = await _metadata(
        service=require_image_delivery_service(request),
        owner_id=active_session.user_id,
        image_id=image_id,
    )
    response.headers.update(_PRIVATE_CACHE_HEADERS)
    return metadata


_BINARY_RESPONSE = {
    "content": {
        "image/png": {"schema": {"type": "string", "format": "binary"}},
        "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
        "image/webp": {"schema": {"type": "string", "format": "binary"}},
    },
    "description": "Authorised private image bytes.",
}


@router.get(
    "/{image_id}/content",
    response_class=Response,
    summary="Preview a private generated image",
    description=(
        "Deliver validated image bytes through FastAPI only after authentication, "
        "owner-scoped authorisation, private-storage retrieval, and an integrity "
        "check. No public or signed object URL is created."
    ),
    responses={
        200: _BINARY_RESPONSE,
        401: {"description": "Authentication is required."},
        404: {"description": "Missing and differently owned images look identical."},
        503: {"description": "Private image content is temporarily unavailable."},
    },
)
async def preview_image(
    image_id: UUID,
    request: Request,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> Response:
    delivered = await _content(
        service=require_image_delivery_service(request),
        owner_id=active_session.user_id,
        image_id=image_id,
    )
    return Response(
        content=delivered.content,
        media_type=delivered.metadata.mime_type,
        headers={
            **_PRIVATE_CACHE_HEADERS,
            "Content-Disposition": (
                f'inline; filename="{delivered.download_filename}"'
            ),
        },
    )


@router.get(
    "/{image_id}/download",
    response_class=Response,
    summary="Download a private generated image",
    description=(
        "Deliver an owner-authorised private image with a server-generated safe "
        "filename. Arbitrary client filenames and storage keys are never accepted."
    ),
    responses={
        200: _BINARY_RESPONSE,
        401: {"description": "Authentication is required."},
        404: {"description": "Missing and differently owned images look identical."},
        503: {"description": "Private image content is temporarily unavailable."},
    },
)
async def download_image(
    image_id: UUID,
    request: Request,
    active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> Response:
    delivered = await _content(
        service=require_image_delivery_service(request),
        owner_id=active_session.user_id,
        image_id=image_id,
    )
    return Response(
        content=delivered.content,
        media_type=delivered.metadata.mime_type,
        headers={
            **_PRIVATE_CACHE_HEADERS,
            "Content-Disposition": (
                f'attachment; filename="{delivered.download_filename}"'
            ),
        },
    )
