"""Secure account-registration workflow."""

from pydantic import SecretStr
from starlette.concurrency import run_in_threadpool

from app.repositories import RegisteredUser, UserRepository
from app.security import PasswordHasher


class RegistrationService:
    """Hash credentials and persist only the resulting password hash."""

    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher

    async def register(self, *, email: str, password: SecretStr) -> RegisteredUser:
        """Create a user without returning or retaining the plaintext password."""

        password_hash = await run_in_threadpool(
            self._password_hasher.hash,
            password.get_secret_value(),
        )
        return await self._users.create_user(
            email=email,
            password_hash=password_hash,
        )
