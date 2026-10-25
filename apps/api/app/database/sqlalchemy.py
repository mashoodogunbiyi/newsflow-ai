"""SQLAlchemy session management for application persistence."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def sqlalchemy_database_url(database_url: SecretStr) -> str:
    """Return a Psycopg SQLAlchemy URL without exposing its credentials."""

    value = database_url.get_secret_value()
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql+psycopg://"):
        return value
    raise ValueError("SQLAlchemy requires a PostgreSQL Psycopg DATABASE_URL.")


class SqlAlchemyDatabase:
    """Own the async engine and create short-lived request sessions."""

    def __init__(
        self,
        database_url: SecretStr,
        connect_timeout_seconds: int = 5,
    ) -> None:
        self._engine: AsyncEngine = create_async_engine(
            sqlalchemy_database_url(database_url),
            pool_pre_ping=True,
            connect_args={"connect_timeout": connect_timeout_seconds},
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Provide one transactional SQLAlchemy session."""

        async with self._session_factory() as session:
            yield session

    async def close(self) -> None:
        """Release pooled database connections during application shutdown."""

        await self._engine.dispose()
