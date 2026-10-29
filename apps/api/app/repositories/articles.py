"""Atomic PostgreSQL article identity and snapshot persistence."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    ArticleProvenanceEventTable,
    ArticleRightsVersionTable,
    ArticleSnapshotTable,
    ArticleTable,
    SourceProfileTable,
)
from app.models.article_rights import ArticleRightsPolicy, RightsVerificationStatus
from app.providers.models import ArticleCategory, NewsArticle


class ArticleIngestionAction(str, Enum):
    """Observable result of one article ingestion attempt."""

    CREATED = "created"
    UPDATED = "updated"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ArticleIngestionResult:
    """Stable identity and action returned without article source content."""

    article_id: UUID
    snapshot_id: UUID
    action: ArticleIngestionAction


class ArticleIdentityConflictError(RuntimeError):
    """Raised when source identity and canonical URL point to different rows."""


class ArticleRepositoryError(RuntimeError):
    """Raised when article persistence fails without exposing source content."""


class ArticleRepository(Protocol):
    """Persistence boundary for one already-normalised article."""

    async def ingest(self, article: NewsArticle) -> ArticleIngestionResult: ...


CATEGORY_DATABASE_VALUES = {
    ArticleCategory.TECHNOLOGY: "technology",
    ArticleCategory.BUSINESS: "business",
    ArticleCategory.WORLD_NEWS: "world_news",
    ArticleCategory.SCIENCE: "science",
    ArticleCategory.OTHER: "other",
}


def article_content_fingerprint(article: NewsArticle) -> str:
    """Hash permitted normalised fields while ignoring retrieval time alone."""

    permitted_payload = article.model_dump(mode="json", exclude={"retrieved_at"})
    serialised = json.dumps(
        permitted_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


class SqlAlchemyArticleRepository:
    """Deduplicate and version articles in one PostgreSQL transaction."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def ingest(self, article: NewsArticle) -> ArticleIngestionResult:
        canonical_url = str(article.url)
        fingerprint = article_content_fingerprint(article)

        try:
            async with self._database.session() as session:
                async with session.begin():
                    profile = await self._enabled_profile(
                        session,
                        profile_key=article.source_profile,
                    )
                    matches = await self._locked_matches(
                        session,
                        profile_id=profile.id,
                        source_item_id=article.source_item_id,
                        canonical_url=canonical_url,
                    )
                    if not matches:
                        inserted_id = await self._insert_identity_if_absent(
                            session,
                            profile_id=profile.id,
                            source_item_id=article.source_item_id,
                            canonical_url=canonical_url,
                        )
                        if inserted_id is not None:
                            snapshot_id = await self._insert_snapshot(
                                session,
                                article=article,
                                article_id=inserted_id,
                                snapshot_number=1,
                                fingerprint=fingerprint,
                            )
                            await self._select_current_snapshot(
                                session,
                                article_id=inserted_id,
                                snapshot_id=snapshot_id,
                                canonical_url=canonical_url,
                            )
                            await self._synchronise_rights(
                                session,
                                article_id=inserted_id,
                                current_rights_version_id=None,
                                article=article,
                                source_approved_at=profile.approved_at,
                            )
                            await self._record_provenance(
                                session,
                                article_id=inserted_id,
                                profile_id=profile.id,
                                article=article,
                                action=ArticleIngestionAction.CREATED,
                            )
                            return ArticleIngestionResult(
                                article_id=inserted_id,
                                snapshot_id=snapshot_id,
                                action=ArticleIngestionAction.CREATED,
                            )

                        matches = await self._locked_matches(
                            session,
                            profile_id=profile.id,
                            source_item_id=article.source_item_id,
                            canonical_url=canonical_url,
                        )

                    existing = self._resolve_existing_identity(
                        matches,
                        profile_id=profile.id,
                        source_item_id=article.source_item_id,
                        canonical_url=canonical_url,
                    )
                    return await self._update_or_skip(
                        session,
                        existing=existing,
                        article=article,
                        fingerprint=fingerprint,
                        canonical_url=canonical_url,
                        profile_id=profile.id,
                        source_approved_at=profile.approved_at,
                    )
        except ArticleIdentityConflictError:
            raise
        except SQLAlchemyError as exc:
            raise ArticleRepositoryError(
                "The article could not be stored safely."
            ) from exc

    @staticmethod
    async def _enabled_profile(
        session: AsyncSession,
        *,
        profile_key: str,
    ) -> SourceProfileTable:
        result = await session.execute(
            select(SourceProfileTable).where(
                SourceProfileTable.profile_key == profile_key,
                SourceProfileTable.status == "enabled",
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise ArticleRepositoryError(
                "The article source profile is unavailable or disabled."
            )
        return profile

    @staticmethod
    async def _locked_matches(
        session: AsyncSession,
        *,
        profile_id: UUID,
        source_item_id: str,
        canonical_url: str,
    ) -> list[ArticleTable]:
        result = await session.execute(
            select(ArticleTable)
            .where(
                or_(
                    (
                        (ArticleTable.source_profile_id == profile_id)
                        & (ArticleTable.source_item_id == source_item_id)
                    ),
                    ArticleTable.canonical_url == canonical_url,
                )
            )
            .with_for_update()
        )
        return list(result.scalars().all())

    @staticmethod
    async def _insert_identity_if_absent(
        session: AsyncSession,
        *,
        profile_id: UUID,
        source_item_id: str,
        canonical_url: str,
    ) -> UUID | None:
        result = await session.execute(
            postgresql_insert(ArticleTable)
            .values(
                source_profile_id=profile_id,
                source_item_id=source_item_id,
                canonical_url=canonical_url,
                status="active",
            )
            .on_conflict_do_nothing()
            .returning(ArticleTable.id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _resolve_existing_identity(
        matches: list[ArticleTable],
        *,
        profile_id: UUID,
        source_item_id: str,
        canonical_url: str,
    ) -> ArticleTable:
        source_match = next(
            (
                row
                for row in matches
                if row.source_profile_id == profile_id
                and row.source_item_id == source_item_id
            ),
            None,
        )
        url_match = next(
            (row for row in matches if row.canonical_url == canonical_url),
            None,
        )
        if source_match is None:
            raise ArticleIdentityConflictError(
                "The canonical URL belongs to a different article identity."
            )
        if url_match is not None and url_match.id != source_match.id:
            raise ArticleIdentityConflictError(
                "The source identifier and canonical URL identify different articles."
            )
        return source_match

    async def _update_or_skip(
        self,
        session: AsyncSession,
        *,
        existing: ArticleTable,
        article: NewsArticle,
        fingerprint: str,
        canonical_url: str,
        profile_id: UUID,
        source_approved_at: datetime | None,
    ) -> ArticleIngestionResult:
        current_snapshot_id = existing.current_snapshot_id
        if current_snapshot_id is not None:
            result = await session.execute(
                select(ArticleSnapshotTable.content_fingerprint).where(
                    ArticleSnapshotTable.id == current_snapshot_id,
                    ArticleSnapshotTable.article_id == existing.id,
                )
            )
            current_fingerprint = result.scalar_one_or_none()
            if current_fingerprint == fingerprint:
                await self._synchronise_rights(
                    session,
                    article_id=existing.id,
                    current_rights_version_id=existing.current_rights_version_id,
                    article=article,
                    source_approved_at=source_approved_at,
                )
                await self._record_provenance(
                    session,
                    article_id=existing.id,
                    profile_id=profile_id,
                    article=article,
                    action=ArticleIngestionAction.SKIPPED,
                )
                return ArticleIngestionResult(
                    article_id=existing.id,
                    snapshot_id=current_snapshot_id,
                    action=ArticleIngestionAction.SKIPPED,
                )

        result = await session.execute(
            select(
                func.coalesce(func.max(ArticleSnapshotTable.snapshot_number), 0)
            ).where(ArticleSnapshotTable.article_id == existing.id)
        )
        snapshot_number = int(result.scalar_one()) + 1
        snapshot_id = await self._insert_snapshot(
            session,
            article=article,
            article_id=existing.id,
            snapshot_number=snapshot_number,
            fingerprint=fingerprint,
        )
        await self._select_current_snapshot(
            session,
            article_id=existing.id,
            snapshot_id=snapshot_id,
            canonical_url=canonical_url,
        )
        await self._synchronise_rights(
            session,
            article_id=existing.id,
            current_rights_version_id=existing.current_rights_version_id,
            article=article,
            source_approved_at=source_approved_at,
        )
        await self._record_provenance(
            session,
            article_id=existing.id,
            profile_id=profile_id,
            article=article,
            action=ArticleIngestionAction.UPDATED,
        )
        return ArticleIngestionResult(
            article_id=existing.id,
            snapshot_id=snapshot_id,
            action=ArticleIngestionAction.UPDATED,
        )

    @staticmethod
    async def _insert_snapshot(
        session: AsyncSession,
        *,
        article: NewsArticle,
        article_id: UUID,
        snapshot_number: int,
        fingerprint: str,
    ) -> UUID:
        result = await session.execute(
            postgresql_insert(ArticleSnapshotTable)
            .values(
                article_id=article_id,
                snapshot_number=snapshot_number,
                contract_version=article.contract_version,
                source_name=article.source_name,
                title=article.title,
                publication_date=article.publication_date,
                category=CATEGORY_DATABASE_VALUES[article.category],
                description=article.description,
                canonical_url=str(article.url),
                permitted_content_status=article.permitted_content.status.value,
                permitted_content_type=article.permitted_content.content_type.value,
                permitted_content_text=article.permitted_content.text,
                storage_allowed=article.rights.storage_allowed,
                display_allowed=article.rights.display_allowed,
                ai_processing_allowed=(article.permitted_content.ai_processing_allowed),
                derivative_output_allowed=(
                    article.permitted_content.derivative_output_allowed
                ),
                rights_decision_ref=article.rights.decision_id,
                access_method=article.rights.access_method.value,
                retention_rule=article.rights.retention_rule,
                rights_expires_at=article.rights.expires_at,
                attribution_display_name=article.attribution.display_name,
                attribution_text=article.attribution.attribution_text,
                byline=article.attribution.byline,
                copyright_notice=article.attribution.copyright_notice,
                retrieved_at=article.retrieved_at,
                source_modified_at=article.modified_at,
                content_fingerprint=fingerprint,
            )
            .returning(ArticleSnapshotTable.id)
        )
        return result.scalar_one()

    @staticmethod
    async def _select_current_snapshot(
        session: AsyncSession,
        *,
        article_id: UUID,
        snapshot_id: UUID,
        canonical_url: str,
    ) -> None:
        await session.execute(
            update(ArticleTable)
            .where(ArticleTable.id == article_id)
            .values(
                canonical_url=canonical_url,
                current_snapshot_id=snapshot_id,
                updated_at=func.now(),
            )
        )

    @staticmethod
    def _policy_from_article(
        article: NewsArticle,
        *,
        source_approved_at: datetime | None,
    ) -> ArticleRightsPolicy:
        verified = source_approved_at is not None
        effective_from = (
            max(article.retrieved_at, source_approved_at)
            if source_approved_at is not None
            else article.retrieved_at
        )
        return ArticleRightsPolicy(
            verification_status=(
                RightsVerificationStatus.VERIFIED
                if verified
                else RightsVerificationStatus.UNVERIFIED
            ),
            storage_allowed=article.rights.storage_allowed if verified else False,
            display_allowed=article.rights.display_allowed if verified else False,
            ai_processing_allowed=(
                article.permitted_content.ai_processing_allowed if verified else False
            ),
            derivative_output_allowed=(
                article.permitted_content.derivative_output_allowed
                if verified
                else False
            ),
            redistribution_allowed=False,
            attribution_required=True,
            attribution_text=article.attribution.attribution_text,
            retention_rule=article.rights.retention_rule,
            retention_expires_at=article.rights.expires_at,
            authorisation_reference=article.rights.decision_id,
            source_contract_version=article.contract_version,
            rights_last_verified_at=source_approved_at,
            effective_from=effective_from,
        )

    async def _synchronise_rights(
        self,
        session: AsyncSession,
        *,
        article_id: UUID,
        current_rights_version_id: UUID | None,
        article: NewsArticle,
        source_approved_at: datetime | None,
    ) -> UUID:
        policy = self._policy_from_article(
            article,
            source_approved_at=source_approved_at,
        )
        current = None
        if current_rights_version_id is not None:
            result = await session.execute(
                select(ArticleRightsVersionTable).where(
                    ArticleRightsVersionTable.id == current_rights_version_id,
                    ArticleRightsVersionTable.article_id == article_id,
                )
            )
            current = result.scalar_one_or_none()
        if current is not None and self._rights_match(current, policy):
            return current.id
        if current is not None:
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
        rights_id = result.scalar_one()
        await session.execute(
            update(ArticleTable)
            .where(ArticleTable.id == article_id)
            .values(current_rights_version_id=rights_id)
        )
        return rights_id

    @staticmethod
    def _rights_match(
        current: ArticleRightsVersionTable,
        policy: ArticleRightsPolicy,
    ) -> bool:
        return (
            current.verification_status == policy.verification_status.value
            and current.storage_allowed == policy.storage_allowed
            and current.display_allowed == policy.display_allowed
            and current.ai_processing_allowed == policy.ai_processing_allowed
            and current.derivative_output_allowed == policy.derivative_output_allowed
            and current.redistribution_allowed == policy.redistribution_allowed
            and current.attribution_required == policy.attribution_required
            and current.attribution_text == policy.attribution_text
            and current.retention_rule == policy.retention_rule
            and current.retention_expires_at == policy.retention_expires_at
            and current.authorisation_reference == policy.authorisation_reference
            and current.source_contract_version == policy.source_contract_version
            and current.rights_last_verified_at == policy.rights_last_verified_at
        )

    @staticmethod
    async def _record_provenance(
        session: AsyncSession,
        *,
        article_id: UUID,
        profile_id: UUID,
        article: NewsArticle,
        action: ArticleIngestionAction,
    ) -> None:
        await session.execute(
            postgresql_insert(ArticleProvenanceEventTable).values(
                article_id=article_id,
                source_profile_id=profile_id,
                source_item_id=article.source_item_id,
                canonical_url=str(article.url),
                publication_date=article.publication_date,
                retrieved_at=article.retrieved_at,
                source_integration_ref=article.source_profile,
                source_contract_version=article.contract_version,
                authorisation_reference=article.rights.decision_id,
                ingestion_action=action.value,
            )
        )
