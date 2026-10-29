"""Authenticated REST endpoints for rights-approved article metadata."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.dependencies import require_authenticated_session
from app.core.errors import ApplicationError
from app.models.article_catalogue import (
    ArticleCatalogueQuery,
    ArticleCollectionResponse,
    ArticleResponse,
)
from app.repositories import AuthenticatedSession
from app.repositories.article_catalogue import ArticleCatalogueRepositoryError
from app.services.article_catalogue import (
    ArticleCatalogueCursorError,
    ArticleCatalogueDataError,
    ArticleCatalogueNotFoundError,
    ArticleCatalogueService,
)

router = APIRouter(prefix="/api/articles", tags=["Article catalogue"])


def _service(request: Request) -> ArticleCatalogueService:
    service: ArticleCatalogueService | None = getattr(
        request.app.state,
        "article_catalogue_service",
        None,
    )
    if service is None:
        raise ApplicationError(
            status_code=503,
            code="article_catalogue_unavailable",
            message="The article catalogue is temporarily unavailable.",
        )
    return service


def _raise_unavailable(
    exc: ArticleCatalogueRepositoryError | ArticleCatalogueDataError,
) -> NoReturn:
    raise ApplicationError(
        status_code=503,
        code="article_catalogue_unavailable",
        message="The article catalogue is temporarily unavailable.",
    ) from exc


@router.get(
    "",
    response_model=ArticleCollectionResponse,
    summary="Browse authorised articles",
    description=(
        "Return one cursor-paginated page of current article metadata. "
        "Only active records with enabled sources and verified, unexpired display "
        "rights are returned. Search covers the permitted title and description."
    ),
    responses={
        401: {"description": "Authentication is required."},
        422: {"description": "A query parameter or cursor is invalid."},
        503: {"description": "The article catalogue is unavailable."},
    },
)
async def list_articles(
    query: Annotated[ArticleCatalogueQuery, Query()],
    request: Request,
    response: Response,
    _active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> ArticleCollectionResponse:
    try:
        result = await _service(request).list_articles(query)
    except ArticleCatalogueCursorError as exc:
        raise ApplicationError(
            status_code=422,
            code="invalid_article_cursor",
            message="The article cursor is invalid for this request.",
        ) from exc
    except (ArticleCatalogueRepositoryError, ArticleCatalogueDataError) as exc:
        _raise_unavailable(exc)

    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.get(
    "/{article_id}",
    response_model=ArticleResponse,
    summary="Retrieve one authorised article",
    description=(
        "Return current permitted metadata and required attribution for one "
        "article. Missing and non-disclosable records both return 404."
    ),
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The article was not found or cannot be disclosed."},
        422: {"description": "The article identifier is invalid."},
        503: {"description": "The article catalogue is unavailable."},
    },
)
async def get_article(
    article_id: UUID,
    request: Request,
    response: Response,
    _active_session: Annotated[
        AuthenticatedSession,
        Depends(require_authenticated_session),
    ],
) -> ArticleResponse:
    try:
        result = await _service(request).get_article(article_id)
    except ArticleCatalogueNotFoundError as exc:
        raise ApplicationError(
            status_code=404,
            code="article_not_found",
            message="The requested article was not found.",
        ) from exc
    except (ArticleCatalogueRepositoryError, ArticleCatalogueDataError) as exc:
        _raise_unavailable(exc)

    response.headers["Cache-Control"] = "private, no-store"
    return result
