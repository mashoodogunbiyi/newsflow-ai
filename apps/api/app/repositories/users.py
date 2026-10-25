"""User account persistence with duplicate-email handling."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from psycopg import errors as psycopg_errors
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import UserTable


class DuplicateUserEmailError(RuntimeError):
    """Raised when the database rejects an existing email address."""


class UserRepositoryError(RuntimeError):
    """Raised when an account cannot be persisted safely."""


@dataclass(frozen=True)
class RegisteredUser:
    """Non-sensitive user fields returned after persistence."""

    id: UUID
    email: str


class UserRepository(Protocol):
    """Persistence boundary used by the registration service."""

    async def create_user(self, *, email: str, password_hash: str) -> RegisteredUser:
        """Create one active account or report a duplicate email."""


class SqlAlchemyUserRepository:
    """Store registered users through SQLAlchemy and PostgreSQL."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def create_user(self, *, email: str, password_hash: str) -> RegisteredUser:
        user = UserTable(email=email, password_hash=password_hash, status="active")

        async with self._database.session() as session:
            session.add(user)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                if self._is_email_conflict(exc):
                    raise DuplicateUserEmailError(
                        "An account already uses this email address."
                    ) from exc
                raise UserRepositoryError(
                    "The user account could not be stored."
                ) from exc
            except SQLAlchemyError as exc:
                await session.rollback()
                raise UserRepositoryError(
                    "The user account could not be stored."
                ) from exc

        return RegisteredUser(id=user.id, email=user.email)

    @staticmethod
    def _is_email_conflict(exc: IntegrityError) -> bool:
        original = exc.orig
        if not isinstance(original, psycopg_errors.UniqueViolation):
            return False
        return original.diag.constraint_name == "uq_users_email"
