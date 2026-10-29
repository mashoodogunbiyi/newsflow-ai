"""PostgreSQL persistence for versioned rights and provenance evidence."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    ArticleProvenanceEventTable,
    ArticleRightsVersionTable,
    ArticleTable,
    SourceProfileTable,
)
from app.models.article_rights import (
    ArticleProvenanceRecord,
    ArticleRightsPolicy,
    ArticleRightsRecord,
    RightsVerificationStatus,
)


class ArticleRightsRepositoryError(RuntimeError):
    """Raised when rights persistence fails without exposing protected data."""


class ArticleRightsVersionConflictError(RuntimeError):
    """Raised when a rights update attempts to rewrite history."""


@dataclass(frozen=True)
class CurrentArticleRights:
    """Current rights record plus the source-profile safety state."""

    record: ArticleRightsRecord
    source_enabled: bool


class ArticleRightsRepository(Protocol):
    """Persistence operations required by the rights-verification service."""

    async def get_current(self, article_id: UUID) -> CurrentArticleRights | None: ...

    async def update_rights(
        self,
        *,
        article_id: UUID,
        policy: ArticleRightsPolicy,
    ) -> ArticleRightsRecord | None: ...

    async def list_provenance(
        self,
        article_id: UUID,
    ) -> tuple[ArticleProvenanceRecord, ...]: ...


def _rights_record(row: ArticleRightsVersionTable) -> ArticleRightsRecord:
    return ArticleRightsRecord(
        id=row.id,
        article_id=row.article_id,
        version_number=row.version_number,
        verification_status=RightsVerificationStatus(row.verification_status),
        storage_allowed=row.storage_allowed,
        display_allowed=row.display_allowed,
        ai_processing_allowed=row.ai_processing_allowed,
        derivative_output_allowed=row.derivative_output_allowed,
        redistribution_allowed=row.redistribution_allowed,
        attribution_required=row.attribution_required,
        attribution_text=row.attribution_text,
        retention_rule=row.retention_rule,
        retention_expires_at=row.retention_expires_at,
        authorisation_reference=row.authorisation_reference,
        source_contract_version=row.source_contract_version,
        rights_last_verified_at=row.rights_last_verified_at,
        effective_from=row.effective_from,
        superseded_at=row.superseded_at,
    )


class SqlAlchemyArticleRightsRepository:
    """Read current rights and append reviewed rights versions."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def get_current(self, article_id: UUID) -> CurrentArticleRights | None:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(
                        ArticleRightsVersionTable,
                        SourceProfileTable.status.label("source_status"),
                    )
                    .join(
                        ArticleTable,
                        ArticleTable.current_rights_version_id
                        == ArticleRightsVersionTable.id,
                    )
                    .join(
                        SourceProfileTable,
                        SourceProfileTable.id == ArticleTable.source_profile_id,
                    )
                    .where(
                        ArticleTable.id == article_id,
                        ArticleRightsVersionTable.article_id == ArticleTable.id,
                    )
                )
                row = result.one_or_none()
        except SQLAlchemyError as exc:
            raise ArticleRightsRepositoryError(
                "Article rights could not be read."
            ) from exc
        if row is None:
            return None
        return CurrentArticleRights(
            record=_rights_record(row[0]),
            source_enabled=row.source_status == "enabled",
        )

    async def update_rights(
        self,
        *,
        article_id: UUID,
        policy: ArticleRightsPolicy,
    ) -> ArticleRightsRecord | None:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    result = await session.execute(
                        select(ArticleTable)
                        .where(ArticleTable.id == article_id)
                        .with_for_update()
                    )
                    article = result.scalar_one_or_none()
                    if article is None:
                        return None

                    current = None
                    if article.current_rights_version_id is not None:
                        result = await session.execute(
                            select(ArticleRightsVersionTable).where(
                                ArticleRightsVersionTable.id
                                == article.current_rights_version_id,
                                ArticleRightsVersionTable.article_id == article_id,
                            )
                        )
                        current = result.scalar_one_or_none()
                    if current is not None:
                        if policy.effective_from < current.effective_from:
                            raise ArticleRightsVersionConflictError(
                                "A rights update cannot rewrite earlier history."
                            )
                        await session.execute(
                            update(ArticleRightsVersionTable)
                            .where(ArticleRightsVersionTable.id == current.id)
                            .values(superseded_at=policy.effective_from)
                        )

                    result = await session.execute(
                        select(
                            func.coalesce(
                                func.max(ArticleRightsVersionTable.version_number),
                                0,
                            )
                        ).where(ArticleRightsVersionTable.article_id == article_id)
                    )
                    version_number = int(result.scalar_one()) + 1
                    rights_id = await self._insert_policy(
                        session,
                        article_id=article_id,
                        version_number=version_number,
                        policy=policy,
                    )
                    await session.execute(
                        update(ArticleTable)
                        .where(ArticleTable.id == article_id)
                        .values(current_rights_version_id=rights_id)
                    )
        except ArticleRightsVersionConflictError:
            raise
        except SQLAlchemyError as exc:
            raise ArticleRightsRepositoryError(
                "Article rights could not be updated."
            ) from exc

        current = await self.get_current(article_id)
        return None if current is None else current.record

    @staticmethod
    async def _insert_policy(
        session: AsyncSession,
        *,
        article_id: UUID,
        version_number: int,
        policy: ArticleRightsPolicy,
    ) -> UUID:
        result = await session.execute(
            postgresql_insert(ArticleRightsVersionTable)
            .values(
                article_id=article_id,
                version_number=version_number,
                verification_status=policy.verification_status.value,
                storage_allowed=policy.storage_allowed,
                display_allowed=policy.display_allowed,
                ai_processing_allowed=policy.ai_processing_allowed,
                derivative_output_allowed=policy.derivative_output_allowed,
                redistribution_allowed=policy.redistribution_allowed,
                attribution_required=policy.attribution_required,
                attribution_text=policy.attribution_text,
                retention_rule=policy.retention_rule,
                retention_expires_at=policy.retention_expires_at,
                authorisation_reference=policy.authorisation_reference,
                source_contract_version=policy.source_contract_version,
                rights_last_verified_at=policy.rights_last_verified_at,
                effective_from=policy.effective_from,
            )
            .returning(ArticleRightsVersionTable.id)
        )
        return result.scalar_one()

    async def list_provenance(
        self,
        article_id: UUID,
    ) -> tuple[ArticleProvenanceRecord, ...]:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    select(
                        ArticleProvenanceEventTable,
                        SourceProfileTable.profile_key.label("provider_id"),
                    )
                    .join(
                        SourceProfileTable,
                        SourceProfileTable.id
                        == ArticleProvenanceEventTable.source_profile_id,
                    )
                    .where(ArticleProvenanceEventTable.article_id == article_id)
                    .order_by(
                        ArticleProvenanceEventTable.created_at,
                        ArticleProvenanceEventTable.id,
                    )
                )
                rows = result.all()
        except SQLAlchemyError as exc:
            raise ArticleRightsRepositoryError(
                "Article provenance could not be read."
            ) from exc
        return tuple(
            ArticleProvenanceRecord(
                id=row[0].id,
                article_id=row[0].article_id,
                source_profile_id=row[0].source_profile_id,
                provider_id=row.provider_id,
                external_article_id=row[0].source_item_id,
                canonical_url=row[0].canonical_url,
                published_at=row[0].publication_date,
                retrieved_at=row[0].retrieved_at,
                source_integration_id=row[0].source_integration_ref,
                source_contract_version=row[0].source_contract_version,
                authorisation_reference=row[0].authorisation_reference,
                ingestion_action=row[0].ingestion_action,
            )
            for row in rows
        )
