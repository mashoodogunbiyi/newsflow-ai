"""PostgreSQL persistence for credentials and server-managed sessions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import SessionTable, UserTable


class AuthenticationRepositoryError(RuntimeError):
    """Raised when authentication persistence cannot be accessed safely."""


@dataclass(frozen=True)
class AccountCredentials:
    """Internal account fields required to verify a login attempt."""

    id: UUID
    email: str
    password_hash: str
    status: str


@dataclass(frozen=True)
class AuthenticatedSession:
    """Safe user fields and server-side controls for an active session."""

    user_id: UUID
    email: str
    csrf_token_hash: bytes
    expires_at: datetime


class AuthenticationRepository(Protocol):
    """Persistence boundary for login and session management."""

    async def get_account_credentials(
        self,
        *,
        email: str,
    ) -> AccountCredentials | None:
        """Return credential fields for one normalised email, when present."""

    async def create_session(
        self,
        *,
        user_id: UUID,
        token_hash: bytes,
        csrf_token_hash: bytes,
        expires_at: datetime,
    ) -> None:
        """Persist only hashes of the random browser session tokens."""

    async def get_active_session(
        self,
        *,
        token_hash: bytes,
        checked_at: datetime,
    ) -> AuthenticatedSession | None:
        """Return a non-expired, non-revoked session for an active user."""

    async def revoke_session(
        self,
        *,
        token_hash: bytes,
        revoked_at: datetime,
    ) -> bool:
        """Invalidate an active session and report whether one was changed."""


class SqlAlchemyAuthenticationRepository:
    """Manage account lookups and sessions through SQLAlchemy."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def get_account_credentials(
        self,
        *,
        email: str,
    ) -> AccountCredentials | None:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(
                        UserTable.id,
                        UserTable.email,
                        UserTable.password_hash,
                        UserTable.status,
                    ).where(
                        UserTable.email == email,
                        UserTable.deleted_at.is_(None),
                    )
                )
                row = result.one_or_none()
        except SQLAlchemyError as exc:
            raise AuthenticationRepositoryError(
                "Account credentials could not be read."
            ) from exc

        if row is None:
            return None
        return AccountCredentials(
            id=row.id,
            email=row.email,
            password_hash=row.password_hash,
            status=row.status,
        )

    async def create_session(
        self,
        *,
        user_id: UUID,
        token_hash: bytes,
        csrf_token_hash: bytes,
        expires_at: datetime,
    ) -> None:
        session_record = SessionTable(
            user_id=user_id,
            token_hash=token_hash,
            csrf_token_hash=csrf_token_hash,
            expires_at=expires_at,
        )

        try:
            async with self._database.session() as session:
                session.add(session_record)
                await session.commit()
        except SQLAlchemyError as exc:
            raise AuthenticationRepositoryError(
                "The authenticated session could not be created."
            ) from exc

    async def get_active_session(
        self,
        *,
        token_hash: bytes,
        checked_at: datetime,
    ) -> AuthenticatedSession | None:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(
                        SessionTable.user_id,
                        UserTable.email,
                        SessionTable.csrf_token_hash,
                        SessionTable.expires_at,
                    )
                    .join(UserTable, UserTable.id == SessionTable.user_id)
                    .where(
                        SessionTable.token_hash == token_hash,
                        SessionTable.revoked_at.is_(None),
                        SessionTable.expires_at > checked_at,
                        UserTable.status == "active",
                        UserTable.deleted_at.is_(None),
                    )
                )
                row = result.one_or_none()
                if row is not None:
                    await session.execute(
                        update(SessionTable)
                        .where(SessionTable.token_hash == token_hash)
                        .values(last_seen_at=checked_at)
                    )
                    await session.commit()
        except SQLAlchemyError as exc:
            raise AuthenticationRepositoryError(
                "The authenticated session could not be read."
            ) from exc

        if row is None:
            return None
        return AuthenticatedSession(
            user_id=row.user_id,
            email=row.email,
            csrf_token_hash=row.csrf_token_hash,
            expires_at=row.expires_at,
        )

    async def revoke_session(
        self,
        *,
        token_hash: bytes,
        revoked_at: datetime,
    ) -> bool:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    update(SessionTable)
                    .where(
                        SessionTable.token_hash == token_hash,
                        SessionTable.revoked_at.is_(None),
                    )
                    .values(revoked_at=revoked_at)
                )
                await session.commit()
        except SQLAlchemyError as exc:
            raise AuthenticationRepositoryError(
                "The authenticated session could not be invalidated."
            ) from exc

        return bool(result.rowcount)
