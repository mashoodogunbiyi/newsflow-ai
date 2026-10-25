"""Argon2id password hashing boundary."""

from typing import Protocol

from argon2 import PasswordHasher as Argon2LibraryHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type


class PasswordHasher(Protocol):
    """One-way password hashing required by account services."""

    def hash(self, password: str) -> str:
        """Return a salted one-way password hash."""

    def verify(self, password_hash: str, password: str) -> bool:
        """Verify a password without recovering the original value."""


class Argon2PasswordHasher:
    """Hash passwords with OWASP's minimum recommended Argon2id settings."""

    def __init__(self) -> None:
        self._hasher = Argon2LibraryHasher(
            time_cost=2,
            memory_cost=19_456,
            parallelism=1,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )

    def hash(self, password: str) -> str:
        """Create a uniquely salted Argon2id hash."""

        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        """Return whether the plaintext password matches the stored hash."""

        try:
            return self._hasher.verify(password_hash, password)
        except (InvalidHashError, VerificationError):
            return False
