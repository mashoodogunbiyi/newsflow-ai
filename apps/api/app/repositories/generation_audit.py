"""PostgreSQL persistence for content-free generation audit events."""

from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import GenerationAuditEventTable, GenerationUsageEventTable
from app.models.generation_audit import (
    GenerationAuditEvent,
    GenerationAuditEventCreate,
    GenerationAuditEventType,
    GenerationUsageSummary,
)


class GenerationAuditRepositoryError(RuntimeError):
    """Raised when audit data cannot be stored or inspected safely."""


class GenerationAuditRepository(Protocol):
    """Persistence operations required by audit and monitoring services."""

    async def record_event(
        self,
        event: GenerationAuditEventCreate,
    ) -> GenerationAuditEvent: ...

    async def delete_before(self, cutoff: datetime) -> int: ...

    async def list_events(
        self,
        *,
        limit: int,
        generation_request_id: UUID | None = None,
        event_type: GenerationAuditEventType | None = None,
    ) -> list[GenerationAuditEvent]: ...

    async def list_events_since(
        self,
        *,
        since: datetime,
        limit: int,
    ) -> list[GenerationAuditEvent]: ...

    async def usage_summary(self, *, since: datetime) -> GenerationUsageSummary: ...


class SqlAlchemyGenerationAuditRepository:
    """Store and read audit metadata without prompts, article text, or drafts."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def record_event(
        self,
        event: GenerationAuditEventCreate,
    ) -> GenerationAuditEvent:
        event_id = uuid4()
        try:
            async with self._database.session() as session:
                async with session.begin():
                    session.add(
                        GenerationAuditEventTable(
                            id=event_id,
                            generation_request_id=event.generation_request_id,
                            user_id=event.user_id,
                            article_id=event.article_id,
                            generation_run_id=event.generation_run_id,
                            usage_event_id=event.usage_event_id,
                            event_type=event.event_type.value,
                            status=event.status.value,
                            occurred_at=event.occurred_at,
                            duration_ms=event.duration_ms,
                            model_identifier=event.model_identifier,
                            prompt_version=event.prompt_version,
                            error_category=(
                                event.error_category.value
                                if event.error_category is not None
                                else None
                            ),
                            rights_decision=event.rights_decision,
                            validation_status=event.validation_status,
                        )
                    )
        except SQLAlchemyError as exc:
            raise GenerationAuditRepositoryError(
                "Generation audit data is temporarily unavailable."
            ) from exc
        return GenerationAuditEvent(id=event_id, **event.model_dump())

    async def delete_before(self, cutoff: datetime) -> int:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    result = await session.execute(
                        delete(GenerationAuditEventTable).where(
                            GenerationAuditEventTable.occurred_at < cutoff
                        )
                    )
                    return int(result.rowcount or 0)
        except SQLAlchemyError as exc:
            raise GenerationAuditRepositoryError(
                "Generation audit retention could not be applied."
            ) from exc

    async def list_events(
        self,
        *,
        limit: int,
        generation_request_id: UUID | None = None,
        event_type: GenerationAuditEventType | None = None,
    ) -> list[GenerationAuditEvent]:
        statement = select(GenerationAuditEventTable)
        if generation_request_id is not None:
            statement = statement.where(
                GenerationAuditEventTable.generation_request_id == generation_request_id
            )
        if event_type is not None:
            statement = statement.where(
                GenerationAuditEventTable.event_type == event_type.value
            )
        statement = statement.order_by(
            GenerationAuditEventTable.occurred_at.desc(),
            GenerationAuditEventTable.id.desc(),
        ).limit(limit)
        return await self._events(statement)

    async def list_events_since(
        self,
        *,
        since: datetime,
        limit: int,
    ) -> list[GenerationAuditEvent]:
        statement = (
            select(GenerationAuditEventTable)
            .where(GenerationAuditEventTable.occurred_at >= since)
            .order_by(
                GenerationAuditEventTable.occurred_at,
                GenerationAuditEventTable.id,
            )
            .limit(limit)
        )
        return await self._events(statement)

    async def usage_summary(self, *, since: datetime) -> GenerationUsageSummary:
        statement = select(
            func.count(GenerationUsageEventTable.id),
            func.coalesce(func.sum(GenerationUsageEventTable.input_tokens), 0),
            func.coalesce(func.sum(GenerationUsageEventTable.output_tokens), 0),
            func.coalesce(func.sum(GenerationUsageEventTable.total_tokens), 0),
        ).where(GenerationUsageEventTable.created_at >= since)
        try:
            async with self._database.session() as session:
                row = (await session.execute(statement)).one()
        except SQLAlchemyError as exc:
            raise GenerationAuditRepositoryError(
                "Generation usage metrics are temporarily unavailable."
            ) from exc
        return GenerationUsageSummary(
            provider_attempts=int(row[0] or 0),
            input_tokens=int(row[1] or 0),
            output_tokens=int(row[2] or 0),
            total_tokens=int(row[3] or 0),
        )

    async def _events(self, statement: object) -> list[GenerationAuditEvent]:
        try:
            async with self._database.session() as session:
                rows = (await session.scalars(statement)).all()
        except SQLAlchemyError as exc:
            raise GenerationAuditRepositoryError(
                "Generation audit data is temporarily unavailable."
            ) from exc
        return [self._event(row) for row in rows]

    @staticmethod
    def _event(row: GenerationAuditEventTable) -> GenerationAuditEvent:
        return GenerationAuditEvent(
            id=row.id,
            generation_request_id=row.generation_request_id,
            user_id=row.user_id,
            article_id=row.article_id,
            generation_run_id=row.generation_run_id,
            usage_event_id=row.usage_event_id,
            event_type=row.event_type,
            status=row.status,
            occurred_at=row.occurred_at,
            duration_ms=row.duration_ms,
            model_identifier=row.model_identifier,
            prompt_version=row.prompt_version,
            error_category=row.error_category,
            rights_decision=row.rights_decision,
            validation_status=row.validation_status,
        )
