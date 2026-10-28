"""Account registration and server-managed authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Header, Request, Response, Security, status

from app.api.dependencies import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    authentication_service,
    session_cookie_scheme,
)
from app.core.errors import ApplicationError
from app.models.auth import (
    AuthenticatedUserResponse,
    LoginUserRequest,
    LoginUserResponse,
    RegisterUserRequest,
    RegisterUserResponse,
)
from app.repositories import (
    AuthenticationRepositoryError,
    DuplicateUserEmailError,
    UserRepositoryError,
)
from app.services import (
    AuthenticationRequiredError,
    CsrfValidationError,
    InvalidCredentialsError,
    LoginSession,
    RegistrationService,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _registration_service(request: Request) -> RegistrationService:
    service: RegistrationService | None = getattr(
        request.app.state,
        "registration_service",
        None,
    )
    if service is None:
        raise ApplicationError(
            status_code=503,
            code="registration_unavailable",
            message="Registration is temporarily unavailable.",
        )
    return service


def _set_session_cookies(
    *,
    response: Response,
    request: Request,
    login_session: LoginSession,
) -> None:
    """Send the raw random tokens only in purpose-limited browser cookies."""

    secure = bool(request.app.state.session_cookie_secure)
    max_age = int(request.app.state.session_cookie_max_age_seconds)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=login_session.session_token,
        max_age=max_age,
        expires=login_session.expires_at,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=login_session.csrf_token,
        max_age=max_age,
        expires=login_session.expires_at,
        path="/",
        secure=secure,
        httponly=False,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _clear_session_cookies(*, response: Response, request: Request) -> None:
    """Expire both browser cookies using their original security attributes."""

    secure = bool(request.app.state.session_cookie_secure)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        secure=secure,
        httponly=False,
        samesite="lax",
    )


@router.post(
    "/register",
    response_model=RegisterUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user account",
    description=(
        "Validate an email address and password, hash the password with Argon2id, "
        "and create an active PostgreSQL user account. Passwords and hashes are "
        "never returned."
    ),
    responses={
        409: {"description": "An account already uses the supplied email."},
        422: {"description": "The email or password failed validation."},
        429: {"description": "Too many registration attempts."},
        503: {"description": "Registration storage is temporarily unavailable."},
    },
)
async def register_user(
    payload: RegisterUserRequest,
    request: Request,
) -> RegisterUserResponse:
    """Create one user account and expose only non-sensitive account fields."""

    try:
        user = await _registration_service(request).register(
            email=str(payload.email),
            password=payload.password,
        )
    except DuplicateUserEmailError as exc:
        raise ApplicationError(
            status_code=409,
            code="email_already_registered",
            message="An account with this email already exists.",
        ) from exc
    except UserRepositoryError as exc:
        raise ApplicationError(
            status_code=503,
            code="registration_unavailable",
            message="Registration is temporarily unavailable.",
        ) from exc

    return RegisterUserResponse(id=user.id, email=user.email)


@router.post(
    "/login",
    response_model=LoginUserResponse,
    summary="Log in and create a server-managed session",
    description=(
        "Verify an account password, create an expiring PostgreSQL session, and "
        "set an HTTP-only session cookie plus a CSRF cookie. Invalid accounts and "
        "passwords receive the same response."
    ),
    responses={
        401: {"description": "The supplied credentials are invalid."},
        422: {"description": "The request failed validation."},
        429: {"description": "Too many login attempts."},
        503: {"description": "Authentication storage is temporarily unavailable."},
    },
)
async def login_user(
    payload: LoginUserRequest,
    request: Request,
    response: Response,
) -> LoginUserResponse:
    """Authenticate one account and issue securely configured cookies."""

    try:
        login_session = await authentication_service(request).login(
            email=str(payload.email),
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise ApplicationError(
            status_code=401,
            code="invalid_credentials",
            message="Invalid email address or password.",
        ) from exc
    except AuthenticationRepositoryError as exc:
        raise ApplicationError(
            status_code=503,
            code="authentication_unavailable",
            message="Authentication is temporarily unavailable.",
        ) from exc

    _set_session_cookies(
        response=response,
        request=request,
        login_session=login_session,
    )
    return LoginUserResponse(
        id=login_session.user_id,
        email=login_session.email,
        expires_at=login_session.expires_at,
    )


@router.get(
    "/me",
    response_model=AuthenticatedUserResponse,
    summary="Get the authenticated user",
    responses={
        401: {"description": "No valid active session was supplied."},
        503: {"description": "Authentication storage is temporarily unavailable."},
    },
)
async def get_authenticated_user(
    request: Request,
    session_token: Annotated[str | None, Security(session_cookie_scheme)],
) -> AuthenticatedUserResponse:
    """Return public identity fields for the current active session."""

    try:
        active_session = await authentication_service(request).authenticate(
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

    return AuthenticatedUserResponse(
        id=active_session.user_id,
        email=active_session.email,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out and invalidate the current session",
    responses={
        401: {"description": "No valid active session was supplied."},
        403: {"description": "The CSRF proof is missing or invalid."},
        503: {"description": "Authentication storage is temporarily unavailable."},
    },
)
async def logout_user(
    request: Request,
    session_token: Annotated[str | None, Security(session_cookie_scheme)],
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> Response:
    """Require CSRF proof, revoke the session, and expire its cookies."""

    try:
        await authentication_service(request).logout(
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

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookies(response=response, request=request)
    response.headers["Cache-Control"] = "no-store"
    return response
