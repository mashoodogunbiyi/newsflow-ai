"""Small PostgreSQL connection boundary used by startup and readiness checks."""

from typing import Protocol

from psycopg import AsyncConnection, Error
from pydantic import SecretStr


class DatabaseConnectionError(RuntimeError):
    """Raised when PostgreSQL cannot be reached or does not answer correctly."""


class DatabaseConnection(Protocol):
    """Interface used by the API so database checks can be tested safely."""

    async def check_connection(self) -> None:
        """Confirm that the database accepts a connection and a simple query."""


class PostgresDatabase:
    """Open a short-lived PostgreSQL connection for availability checks."""

    def __init__(
        self, database_url: SecretStr, connect_timeout_seconds: int = 5
    ) -> None:
        self._database_url = database_url
        self._connect_timeout_seconds = connect_timeout_seconds

    async def check_connection(self) -> None:
        """Run SELECT 1 and hide driver details if the check fails."""

        try:
            async with await AsyncConnection.connect(
                self._database_url.get_secret_value(),
                connect_timeout=self._connect_timeout_seconds,
            ) as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
        except (Error, OSError, TimeoutError) as exc:
            raise DatabaseConnectionError(
                "PostgreSQL is unavailable. Check the server and DATABASE_URL."
            ) from exc

        if result != (1,):
            raise DatabaseConnectionError(
                "PostgreSQL did not return the expected connection-check result."
            )
