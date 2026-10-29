"""Atomic PostgreSQL article identity and snapshot persistence."""

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    ArticleSnapshotTable,
    ArticleTable,
    SourceProfileTable,
)
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
                    profile_id = await self._enabled_profile_id(
                        session,
                        profile_key=article.source_profile,
                    )
                    matches = await self._locked_matches(
                        session,
                        profile_id=profile_id,
                        source_item_id=article.source_item_id,
                        canonical_url=canonical_url,
                    )
                    if not matches:
                        inserted_id = await self._insert_identity_if_absent(
                            session,
                            profile_id=profile_id,
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
                            return ArticleIngestionResult(
                                article_id=inserted_id,
                                snapshot_id=snapshot_id,
                                action=ArticleIngestionAction.CREATED,
                            )

                        matches = await self._locked_matches(
                            session,
                            profile_id=profile_id,
                            source_item_id=article.source_item_id,
                            canonical_url=canonical_url,
                        )

                    existing = self._resolve_existing_identity(
                        matches,
                        profile_id=profile_id,
                        source_item_id=article.source_item_id,
                        canonical_url=canonical_url,
                    )
                    return await self._update_or_skip(
                        session,
                        existing=existing,
                        article=article,
                        fingerprint=fingerprint,
                        canonical_url=canonical_url,
                    )
        except ArticleIdentityConflictError:
            raise
        except SQLAlchemyError as exc:
            raise ArticleRepositoryError(
                "The article could not be stored safely."
            ) from exc

    @staticmethod
    async def _enabled_profile_id(
        session: AsyncSession,
        *,
        profile_key: str,
    ) -> UUID:
        result = await session.execute(
            select(SourceProfileTable.id).where(
                SourceProfileTable.profile_key == profile_key,
                SourceProfileTable.status == "enabled",
            )
        )
        profile_id = result.scalar_one_or_none()
        if profile_id is None:
            raise ArticleRepositoryError(
                "The article source profile is unavailable or disabled."
            )
        return profile_id

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
