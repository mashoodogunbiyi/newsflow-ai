"""PostgreSQL enforcement and persistence for AI generation usage controls."""

from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import GenerationUsageEventTable
from app.models.ai import AITokenUsage
from app.models.generation_usage import (
    GenerationErrorCategory,
    GenerationUsageAttempt,
    GenerationUsageStatus,
)


class GenerationUsageRepositoryError(RuntimeError):
    """Raised when usage controls cannot be enforced safely."""


class GenerationDailyLimitReached(RuntimeError):
    """Raised before provider access when the daily allowance is exhausted."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("The daily generation allowance has been reached.")


class GenerationConcurrencyLimitReached(RuntimeError):
    """Raised when the user already has the maximum active attempts."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("The concurrent generation allowance has been reached.")


class DuplicateGenerationInProgress(RuntimeError):
    """Raised when the same idempotent request is already being processed."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("The generation request is already in progress.")


class GenerationUsageRepository(Protocol):
    """Shared persistence operations required by the usage service."""

    async def reserve_attempt(
        self,
        *,
        owner_id: UUID,
        request_fingerprint: str,
        now: datetime,
        day_started_at: datetime,
        day_ends_at: datetime,
        expires_at: datetime,
        retention_started_at: datetime,
        daily_limit: int,
        concurrent_limit: int,
    ) -> GenerationUsageAttempt: ...

    async def complete_attempt(
        self,
        *,
        attempt: GenerationUsageAttempt,
        generation_run_id: UUID,
        model_identifier: str,
        token_usage: AITokenUsage,
        completed_at: datetime,
    ) -> None: ...

    async def fail_attempt(
        self,
        *,
        attempt: GenerationUsageAttempt,
        category: GenerationErrorCategory,
        completed_at: datetime,
    ) -> None: ...


class SqlAlchemyGenerationUsageRepository:
    """Use PostgreSQL transactions and advisory locks across API instances."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def reserve_attempt(
        self,
        *,
        owner_id: UUID,
        request_fingerprint: str,
        now: datetime,
        day_started_at: datetime,
        day_ends_at: datetime,
        expires_at: datetime,
        retention_started_at: datetime,
        daily_limit: int,
        concurrent_limit: int,
    ) -> GenerationUsageAttempt:
        attempt_id = uuid4()
        try:
            async with self._database.session() as session:
                async with session.begin():
                    await session.execute(
                        select(
                            func.pg_advisory_xact_lock(
                                func.hashtextextended(str(owner_id), 0)
                            )
                        )
                    )
                    await session.execute(
                        update(GenerationUsageEventTable)
                        .where(
                            GenerationUsageEventTable.user_id == owner_id,
                            GenerationUsageEventTable.status
                            == GenerationUsageStatus.STARTED.value,
                            GenerationUsageEventTable.expires_at <= now,
                        )
                        .values(
                            status=GenerationUsageStatus.FAILED.value,
                            error_category=(
                                GenerationErrorCategory.GENERATION_ABANDONED.value
                            ),
                            completed_at=now,
                        )
                    )
                    await session.execute(
                        delete(GenerationUsageEventTable).where(
                            GenerationUsageEventTable.user_id == owner_id,
                            GenerationUsageEventTable.status
                            != GenerationUsageStatus.STARTED.value,
                            GenerationUsageEventTable.completed_at
                            < retention_started_at,
                        )
                    )

                    duplicate_expiry = await session.scalar(
                        select(GenerationUsageEventTable.expires_at).where(
                            GenerationUsageEventTable.user_id == owner_id,
                            GenerationUsageEventTable.request_fingerprint
                            == request_fingerprint,
                            GenerationUsageEventTable.status
                            == GenerationUsageStatus.STARTED.value,
                            GenerationUsageEventTable.expires_at > now,
                        )
                    )
                    if duplicate_expiry is not None:
                        raise DuplicateGenerationInProgress(
                            self._retry_after(duplicate_expiry, now)
                        )

                    attempts_today = await session.scalar(
                        select(func.count(GenerationUsageEventTable.id)).where(
                            GenerationUsageEventTable.user_id == owner_id,
                            GenerationUsageEventTable.created_at >= day_started_at,
                            GenerationUsageEventTable.created_at < day_ends_at,
                        )
                    )
                    if int(attempts_today or 0) >= daily_limit:
                        raise GenerationDailyLimitReached(
                            self._retry_after(day_ends_at, now)
                        )

                    active_expiries = list(
                        (
                            await session.scalars(
                                select(GenerationUsageEventTable.expires_at)
                                .where(
                                    GenerationUsageEventTable.user_id == owner_id,
                                    GenerationUsageEventTable.status
                                    == GenerationUsageStatus.STARTED.value,
                                    GenerationUsageEventTable.expires_at > now,
                                )
                                .order_by(GenerationUsageEventTable.expires_at)
                            )
                        ).all()
                    )
                    if len(active_expiries) >= concurrent_limit:
                        raise GenerationConcurrencyLimitReached(
                            self._retry_after(active_expiries[0], now)
                        )

                    session.add(
                        GenerationUsageEventTable(
                            id=attempt_id,
                            user_id=owner_id,
                            request_fingerprint=request_fingerprint,
                            status=GenerationUsageStatus.STARTED.value,
                            created_at=now,
                            expires_at=expires_at,
                        )
                    )
        except (
            DuplicateGenerationInProgress,
            GenerationDailyLimitReached,
            GenerationConcurrencyLimitReached,
        ):
            raise
        except SQLAlchemyError as exc:
            raise GenerationUsageRepositoryError(
                "Generation usage controls are temporarily unavailable."
            ) from exc
        return GenerationUsageAttempt(
            id=attempt_id,
            owner_id=owner_id,
            request_fingerprint=request_fingerprint,
            created_at=now,
            expires_at=expires_at,
        )

    async def complete_attempt(
        self,
        *,
        attempt: GenerationUsageAttempt,
        generation_run_id: UUID,
        model_identifier: str,
        token_usage: AITokenUsage,
        completed_at: datetime,
    ) -> None:
        await self._finish(
            attempt=attempt,
            values={
                "status": GenerationUsageStatus.SUCCEEDED.value,
                "generation_run_id": generation_run_id,
                "model_identifier": model_identifier,
                "input_tokens": token_usage.input_tokens,
                "output_tokens": token_usage.output_tokens,
                "total_tokens": token_usage.total_tokens,
                "error_category": None,
                "completed_at": completed_at,
            },
        )

    async def fail_attempt(
        self,
        *,
        attempt: GenerationUsageAttempt,
        category: GenerationErrorCategory,
        completed_at: datetime,
    ) -> None:
        await self._finish(
            attempt=attempt,
            values={
                "status": GenerationUsageStatus.FAILED.value,
                "error_category": category.value,
                "completed_at": completed_at,
            },
        )

    async def _finish(
        self,
        *,
        attempt: GenerationUsageAttempt,
        values: dict[str, object],
    ) -> None:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    result = await session.execute(
                        update(GenerationUsageEventTable)
                        .where(
                            GenerationUsageEventTable.id == attempt.id,
                            GenerationUsageEventTable.user_id == attempt.owner_id,
                            GenerationUsageEventTable.status
                            == GenerationUsageStatus.STARTED.value,
                        )
                        .values(**values)
                    )
                    if result.rowcount != 1:
                        raise GenerationUsageRepositoryError(
                            "The generation usage attempt could not be updated."
                        )
        except GenerationUsageRepositoryError:
            raise
        except SQLAlchemyError as exc:
            raise GenerationUsageRepositoryError(
                "The generation usage attempt could not be updated."
            ) from exc

    @staticmethod
    def _retry_after(target: datetime, now: datetime) -> int:
        return max(1, int((target - now).total_seconds()) + 1)
