"""Persistence repositories for NewsFlow AI."""

from app.repositories.authentication import (
    AccountCredentials,
    AuthenticatedSession,
    AuthenticationRepository,
    AuthenticationRepositoryError,
    SqlAlchemyAuthenticationRepository,
)
from app.repositories.content_deletion import (
    ContentDeletionRepository,
    ContentDeletionRepositoryError,
    SqlAlchemyContentDeletionRepository,
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
    SavedDraftImage,
    SavedDraftPage,
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
    "ContentDeletionRepository",
    "ContentDeletionRepositoryError",
    "DuplicateUserEmailError",
    "RegisteredUser",
    "SavedContent",
    "SavedContentConflictError",
    "SavedContentRepository",
    "SavedContentRepositoryError",
    "SavedDraft",
    "SavedDraftDuplicateError",
    "SavedDraftImage",
    "SavedDraftIdempotencyConflict",
    "SavedDraftPage",
    "SavedDraftRepository",
    "SavedDraftRepositoryError",
    "SavedDraftVersionConflict",
    "SqlAlchemyAuthenticationRepository",
    "SqlAlchemyContentDeletionRepository",
    "SqlAlchemySavedContentRepository",
    "SqlAlchemySavedDraftRepository",
    "SqlAlchemyUserRepository",
    "UserRepository",
    "UserRepositoryError",
]
