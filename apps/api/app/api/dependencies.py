"""Reusable authentication and CSRF dependencies for protected API routes."""

from typing import Annotated

from fastapi import Header, Request, Security
from fastapi.security import APIKeyCookie

from app.core.errors import ApplicationError
from app.repositories import AuthenticatedSession, AuthenticationRepositoryError
from app.services import (
    AuthenticationRequiredError,
    AuthenticationService,
    CsrfValidationError,
)

SESSION_COOKIE_NAME = "newsflow_session"
CSRF_COOKIE_NAME = "newsflow_csrf"
session_cookie_scheme = APIKeyCookie(
    name=SESSION_COOKIE_NAME,
    scheme_name="SessionCookie",
    description="HTTP-only server-managed session cookie created by login.",
    auto_error=False,
)


def authentication_service(request: Request) -> AuthenticationService:
    """Return the configured authentication service or a safe 503 response."""

    service: AuthenticationService | None = getattr(
        request.app.state,
        "authentication_service",
        None,
    )
    if service is None:
        raise ApplicationError(
            status_code=503,
            code="authentication_unavailable",
            message="Authentication is temporarily unavailable.",
        )
    return service


async def require_authenticated_session(
    request: Request,
    session_token: Annotated[str | None, Security(session_cookie_scheme)],
) -> AuthenticatedSession:
    """Resolve the authenticated user from the server-managed session cookie."""

    try:
        return await authentication_service(request).authenticate(
            session_token=session_token
        )
    except AuthenticationRequiredError as exc:
        raise ApplicationError(
            status_code=401,
            code="authentication_required",
            message="Authentication is required.",
        ) from exc
    except AuthenticationRepositoryError as exc:
        raise ApplicationError(
            status_code=503,
            code="authentication_unavailable",
            message="Authentication is temporarily unavailable.",
        ) from exc


async def require_csrf_authenticated_session(
    request: Request,
    session_token: Annotated[str | None, Security(session_cookie_scheme)],
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> AuthenticatedSession:
    """Require an active session and matching CSRF proof before a data change."""

    try:
        return await authentication_service(request).authenticate_with_csrf(
            session_token=session_token,
            csrf_token=x_csrf_token,
        )
    except AuthenticationRequiredError as exc:
        raise ApplicationError(
            status_code=401,
            code="authentication_required",
            message="Authentication is required.",
        ) from exc
    except CsrfValidationError as exc:
        raise ApplicationError(
            status_code=403,
            code="csrf_validation_failed",
            message="CSRF validation failed.",
        ) from exc
    except AuthenticationRepositoryError as exc:
        raise ApplicationError(
            status_code=503,
            code="authentication_unavailable",
            message="Authentication is temporarily unavailable.",
        ) from exc
