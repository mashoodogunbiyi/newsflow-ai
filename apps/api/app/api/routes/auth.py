"""Authentication and account-registration endpoints."""

from fastapi import APIRouter, Request, status

from app.core.errors import ApplicationError
from app.models.auth import RegisterUserRequest, RegisterUserResponse
from app.repositories import DuplicateUserEmailError, UserRepositoryError
from app.services import RegistrationService

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
