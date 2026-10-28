"""Credential verification and server-managed session workflows."""

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import SecretStr
from starlette.concurrency import run_in_threadpool

from app.repositories import (
    AuthenticatedSession,
    AuthenticationRepository,
)
from app.security import PasswordHasher


class InvalidCredentialsError(RuntimeError):
    """Raised for every unknown account or incorrect password."""


class AuthenticationRequiredError(RuntimeError):
    """Raised when a request has no valid active session."""


class CsrfValidationError(RuntimeError):
    """Raised when a state-changing request lacks its session CSRF proof."""


@dataclass(frozen=True)
class LoginSession:
    """New session values returned only to the cookie-setting API boundary."""

    user_id: UUID
    email: str
    session_token: str
    csrf_token: str
    expires_at: datetime


def hash_session_token(token: str) -> bytes:
    """Create the fixed-length SHA-256 value persisted for a random token."""

    return hashlib.sha256(token.encode("ascii")).digest()


class AuthenticationService:
    """Authenticate credentials and manage absolute-lifetime sessions."""

    def __init__(
        self,
        *,
        repository: AuthenticationRepository,
        password_hasher: PasswordHasher,
        session_lifetime: timedelta,
        clock: Callable[[], datetime] | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._session_lifetime = session_lifetime
        self._clock = clock or (lambda: datetime.now(UTC))
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._dummy_password_hash = password_hasher.hash(
            "Dummy-Credential-Check-Only-57!"
        )

    async def login(self, *, email: str, password: SecretStr) -> LoginSession:
        """Verify credentials and create a session without storing raw tokens."""

        account = await self._repository.get_account_credentials(email=email)
        password_hash = (
            account.password_hash if account is not None else self._dummy_password_hash
        )
        password_matches = await run_in_threadpool(
            self._password_hasher.verify,
            password_hash,
            password.get_secret_value(),
        )

        if account is None or not password_matches or account.status != "active":
            raise InvalidCredentialsError("Invalid email address or password.")

        session_token = self._token_factory()
        csrf_token = self._token_factory()
        issued_at = self._clock()
        expires_at = issued_at + self._session_lifetime
        await self._repository.create_session(
            user_id=account.id,
            token_hash=hash_session_token(session_token),
            csrf_token_hash=hash_session_token(csrf_token),
            expires_at=expires_at,
        )
        return LoginSession(
            user_id=account.id,
            email=account.email,
            session_token=session_token,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )

    async def authenticate(self, *, session_token: str | None) -> AuthenticatedSession:
        """Resolve a valid session or return the same safe unauthorised outcome."""

        if not session_token:
            raise AuthenticationRequiredError("Authentication is required.")

        active_session = await self._repository.get_active_session(
            token_hash=hash_session_token(session_token),
            checked_at=self._clock(),
        )
        if active_session is None:
            raise AuthenticationRequiredError("Authentication is required.")
        return active_session

    async def authenticate_with_csrf(
        self,
        *,
        session_token: str | None,
        csrf_token: str | None,
    ) -> AuthenticatedSession:
        """Require both an active session and its matching CSRF proof."""

        active_session = await self.authenticate(session_token=session_token)
        if not csrf_token or not secrets.compare_digest(
            hash_session_token(csrf_token),
            active_session.csrf_token_hash,
        ):
            raise CsrfValidationError("The CSRF token is missing or invalid.")
        return active_session

    async def logout(
        self,
        *,
        session_token: str | None,
        csrf_token: str | None,
    ) -> None:
        """Validate CSRF proof and revoke the current server-side session."""

        await self.authenticate_with_csrf(
            session_token=session_token,
            csrf_token=csrf_token,
        )

        revoked = await self._repository.revoke_session(
            token_hash=hash_session_token(session_token or ""),
            revoked_at=self._clock(),
        )
        if not revoked:
            raise AuthenticationRequiredError("Authentication is required.")
