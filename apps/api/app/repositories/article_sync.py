"""PostgreSQL persistence for synchronisation jobs, leases, and checkpoints."""

from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    ArticleSyncCheckpointTable,
    ArticleSyncJobTable,
    SourceProfileTable,
    UserTable,
)
from app.models.article_sync import (
    SyncCheckpoint,
    SyncJobRecord,
    SyncJobStatus,
    SyncStatistics,
    SyncTriggerType,
)


class ArticleSyncRepositoryError(RuntimeError):
    """Raised when job persistence fails without exposing database details."""


class ActiveSyncJobError(RuntimeError):
    """Raised when a provider already has a pending or running job."""


class ArticleSyncRepository(Protocol):
    """Persistence boundary used by manual and scheduled synchronisation."""

    async def source_profile_enabled(self, profile_key: str) -> bool: ...

    async def user_is_admin(self, user_id: UUID) -> bool: ...

    async def recover_stale_jobs(self, *, checked_at: datetime) -> int: ...

    async def create_job(
        self,
        *,
        provider_id: str,
        trigger_type: SyncTriggerType,
        requested_by_user_id: UUID | None,
        scheduled_for: datetime | None,
        created_at: datetime,
        lease_duration: timedelta,
    ) -> SyncJobRecord: ...

    async def claim_job(
        self,
        *,
        job_id: UUID,
        started_at: datetime,
        lease_duration: timedelta,
    ) -> SyncJobRecord | None: ...

    async def renew_lease(
        self,
        *,
        job_id: UUID,
        checked_at: datetime,
        lease_duration: timedelta,
    ) -> bool: ...

    async def finish_job(
        self,
        *,
        job_id: UUID,
        status: SyncJobStatus,
        statistics: SyncStatistics,
        checkpoint_from: datetime | None,
        checkpoint_candidate: datetime | None,
        completed_at: datetime,
        error_code: str | None,
        error_summary: str | None,
    ) -> SyncJobRecord | None: ...

    async def get_job(self, job_id: UUID) -> SyncJobRecord | None: ...

    async def get_checkpoint(self, provider_id: str) -> SyncCheckpoint | None: ...

    async def advance_checkpoint(
        self,
        *,
        provider_id: str,
        publication_at: datetime | None,
        completed_at: datetime,
    ) -> None: ...

    async def reserve_scheduled_run(
        self,
        *,
        provider_id: str,
        checked_at: datetime,
        interval: timedelta,
    ) -> bool: ...


def _job_record(row: ArticleSyncJobTable) -> SyncJobRecord:
    return SyncJobRecord(
        id=row.id,
        provider_id=row.provider_id,
        trigger_type=SyncTriggerType(row.trigger_type),
        status=SyncJobStatus(row.status),
        requested_by_user_id=row.requested_by_user_id,
        checkpoint_from=row.checkpoint_from,
        checkpoint_candidate=row.checkpoint_candidate,
        scheduled_for=row.scheduled_for,
        started_at=row.started_at,
        completed_at=row.completed_at,
        lease_expires_at=row.lease_expires_at,
        statistics=SyncStatistics(
            retrieved=row.articles_retrieved,
            created=row.articles_created,
            updated=row.articles_updated,
            skipped=row.articles_skipped,
            rejected=row.articles_rejected,
            provider_attempts=row.provider_attempts,
        ),
        error_code=row.error_code,
        error_summary=row.error_summary,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyArticleSyncRepository:
    """Store sync state in PostgreSQL so it survives process restarts."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def source_profile_enabled(self, profile_key: str) -> bool:
        try:
            async with self._database.session() as session:
                result = await session.scalar(
                    select(SourceProfileTable.id).where(
                        SourceProfileTable.profile_key == profile_key,
                        SourceProfileTable.status == "enabled",
                        SourceProfileTable.approved_at.is_not(None),
                    )
                )
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "The source authorisation state could not be checked."
            ) from exc
        return result is not None

    async def user_is_admin(self, user_id: UUID) -> bool:
        try:
            async with self._database.session() as session:
                result = await session.scalar(
                    select(UserTable.id).where(
                        UserTable.id == user_id,
                        UserTable.role == "admin",
                        UserTable.status == "active",
                        UserTable.deleted_at.is_(None),
                    )
                )
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "Administrator authorisation could not be checked."
            ) from exc
        return result is not None

    async def recover_stale_jobs(self, *, checked_at: datetime) -> int:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    result = await session.execute(
                        update(ArticleSyncJobTable)
                        .where(
                            ArticleSyncJobTable.status.in_(("pending", "running")),
                            ArticleSyncJobTable.lease_expires_at <= checked_at,
                        )
                        .values(
                            status=SyncJobStatus.INTERRUPTED.value,
                            completed_at=checked_at,
                            lease_expires_at=None,
                            error_code="SYNC_INTERRUPTED",
                            error_summary=(
                                "The previous worker stopped before completing."
                            ),
                            updated_at=checked_at,
                        )
                    )
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "Stale synchronisation jobs could not be recovered."
            ) from exc
        return int(result.rowcount or 0)

    async def create_job(
        self,
        *,
        provider_id: str,
        trigger_type: SyncTriggerType,
        requested_by_user_id: UUID | None,
        scheduled_for: datetime | None,
        created_at: datetime,
        lease_duration: timedelta,
    ) -> SyncJobRecord:
        job = ArticleSyncJobTable(
            provider_id=provider_id,
            trigger_type=trigger_type.value,
            status=SyncJobStatus.PENDING.value,
            requested_by_user_id=requested_by_user_id,
            scheduled_for=scheduled_for,
            lease_expires_at=created_at + lease_duration,
            created_at=created_at,
            updated_at=created_at,
        )
        try:
            async with self._database.session() as session:
                session.add(job)
                await session.commit()
                await session.refresh(job)
        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            )
            if constraint_name == "uq_article_sync_jobs_active_provider":
                raise ActiveSyncJobError(
                    "A synchronisation job is already active for this provider."
                ) from exc
            raise ArticleSyncRepositoryError(
                "The synchronisation job could not be created."
            ) from exc
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "The synchronisation job could not be created."
            ) from exc
        return _job_record(job)

    async def claim_job(
        self,
        *,
        job_id: UUID,
        started_at: datetime,
        lease_duration: timedelta,
    ) -> SyncJobRecord | None:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    result = await session.execute(
                        update(ArticleSyncJobTable)
                        .where(
                            ArticleSyncJobTable.id == job_id,
                            ArticleSyncJobTable.status == SyncJobStatus.PENDING.value,
                            ArticleSyncJobTable.lease_expires_at > started_at,
                        )
                        .values(
                            status=SyncJobStatus.RUNNING.value,
                            started_at=started_at,
                            lease_expires_at=started_at + lease_duration,
                            updated_at=started_at,
                        )
                        .returning(ArticleSyncJobTable)
                    )
                    row = result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "The synchronisation job could not be claimed."
            ) from exc
        return None if row is None else _job_record(row)

    async def renew_lease(
        self,
        *,
        job_id: UUID,
        checked_at: datetime,
        lease_duration: timedelta,
    ) -> bool:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    result = await session.execute(
                        update(ArticleSyncJobTable)
                        .where(
                            ArticleSyncJobTable.id == job_id,
                            ArticleSyncJobTable.status == SyncJobStatus.RUNNING.value,
                            ArticleSyncJobTable.lease_expires_at > checked_at,
                        )
                        .values(
                            lease_expires_at=checked_at + lease_duration,
                            updated_at=checked_at,
                        )
                    )
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "The synchronisation job lease could not be renewed."
            ) from exc
        return bool(result.rowcount)

    async def finish_job(
        self,
        *,
        job_id: UUID,
        status: SyncJobStatus,
        statistics: SyncStatistics,
        checkpoint_from: datetime | None,
        checkpoint_candidate: datetime | None,
        completed_at: datetime,
        error_code: str | None,
        error_summary: str | None,
    ) -> SyncJobRecord | None:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    result = await session.execute(
                        update(ArticleSyncJobTable)
                        .where(
                            ArticleSyncJobTable.id == job_id,
                            ArticleSyncJobTable.status == SyncJobStatus.RUNNING.value,
                        )
                        .values(
                            status=status.value,
                            checkpoint_from=checkpoint_from,
                            checkpoint_candidate=checkpoint_candidate,
                            completed_at=completed_at,
                            lease_expires_at=None,
                            articles_retrieved=statistics.retrieved,
                            articles_created=statistics.created,
                            articles_updated=statistics.updated,
                            articles_skipped=statistics.skipped,
                            articles_rejected=statistics.rejected,
                            provider_attempts=statistics.provider_attempts,
                            error_code=error_code,
                            error_summary=error_summary,
                            updated_at=completed_at,
                        )
                        .returning(ArticleSyncJobTable)
                    )
                    row = result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "The synchronisation result could not be stored."
            ) from exc
        return None if row is None else _job_record(row)

    async def get_job(self, job_id: UUID) -> SyncJobRecord | None:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(ArticleSyncJobTable).where(ArticleSyncJobTable.id == job_id)
                )
                row = result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "The synchronisation job could not be read."
            ) from exc
        return None if row is None else _job_record(row)

    async def get_checkpoint(self, provider_id: str) -> SyncCheckpoint | None:
        try:
            async with self._database.session() as session:
                result = await session.get(ArticleSyncCheckpointTable, provider_id)
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "The synchronisation checkpoint could not be read."
            ) from exc
        if result is None:
            return None
        return SyncCheckpoint(
            provider_id=result.provider_id,
            last_successful_publication_at=result.last_successful_publication_at,
            last_successful_completed_at=result.last_successful_completed_at,
            next_scheduled_at=result.next_scheduled_at,
        )

    async def advance_checkpoint(
        self,
        *,
        provider_id: str,
        publication_at: datetime | None,
        completed_at: datetime,
    ) -> None:
        statement = postgresql_insert(ArticleSyncCheckpointTable).values(
            provider_id=provider_id,
            last_successful_publication_at=publication_at,
            last_successful_completed_at=completed_at,
            updated_at=completed_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[ArticleSyncCheckpointTable.provider_id],
            set_={
                "last_successful_publication_at": publication_at,
                "last_successful_completed_at": completed_at,
                "updated_at": completed_at,
            },
        )
        try:
            async with self._database.session() as session:
                async with session.begin():
                    await session.execute(statement)
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "The synchronisation checkpoint could not be advanced."
            ) from exc

    async def reserve_scheduled_run(
        self,
        *,
        provider_id: str,
        checked_at: datetime,
        interval: timedelta,
    ) -> bool:
        next_scheduled_at = checked_at + interval
        statement = postgresql_insert(ArticleSyncCheckpointTable).values(
            provider_id=provider_id,
            next_scheduled_at=next_scheduled_at,
            updated_at=checked_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[ArticleSyncCheckpointTable.provider_id],
            set_={
                "next_scheduled_at": next_scheduled_at,
                "updated_at": checked_at,
            },
            where=or_(
                ArticleSyncCheckpointTable.next_scheduled_at.is_(None),
                ArticleSyncCheckpointTable.next_scheduled_at <= checked_at,
            ),
        ).returning(ArticleSyncCheckpointTable.provider_id)
        try:
            async with self._database.session() as session:
                async with session.begin():
                    result = await session.execute(statement)
                    reserved = result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise ArticleSyncRepositoryError(
                "The scheduled synchronisation slot could not be reserved."
            ) from exc
        return reserved is not None
