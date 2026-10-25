"""Persistence repositories for NewsFlow AI."""

from app.repositories.authentication import (
    AccountCredentials,
    AuthenticatedSession,
    AuthenticationRepository,
    AuthenticationRepositoryError,
    SqlAlchemyAuthenticationRepository,
)
from app.repositories.users import (
    DuplicateUserEmailError,
    RegisteredUser,
    SqlAlchemyUserRepository,
    UserRepository,
    UserRepositoryError,
)

__all__ = [
    "AccountCredentials",
    "AuthenticatedSession",
    "AuthenticationRepository",
    "AuthenticationRepositoryError",
    "DuplicateUserEmailError",
    "RegisteredUser",
    "SqlAlchemyAuthenticationRepository",
    "SqlAlchemyUserRepository",
    "UserRepository",
    "UserRepositoryError",
]
