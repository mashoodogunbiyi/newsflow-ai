"""Persistence repositories for NewsFlow AI."""

from app.repositories.authentication import (
    AccountCredentials,
    AuthenticatedSession,
    AuthenticationRepository,
    AuthenticationRepositoryError,
    SqlAlchemyAuthenticationRepository,
)
from app.repositories.library import (
    SavedContent,
    SavedContentConflictError,
    SavedContentRepository,
    SavedContentRepositoryError,
    SqlAlchemySavedContentRepository,
)
from app.repositories.saved_drafts import (
    SavedDraft,
    SavedDraftDuplicateError,
    SavedDraftIdempotencyConflict,
    SavedDraftRepository,
    SavedDraftRepositoryError,
    SavedDraftVersionConflict,
    SqlAlchemySavedDraftRepository,
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
    "SavedContent",
    "SavedContentConflictError",
    "SavedContentRepository",
    "SavedContentRepositoryError",
    "SavedDraft",
    "SavedDraftDuplicateError",
    "SavedDraftIdempotencyConflict",
    "SavedDraftRepository",
    "SavedDraftRepositoryError",
    "SavedDraftVersionConflict",
    "SqlAlchemyAuthenticationRepository",
    "SqlAlchemySavedContentRepository",
    "SqlAlchemySavedDraftRepository",
    "SqlAlchemyUserRepository",
    "UserRepository",
    "UserRepositoryError",
]
