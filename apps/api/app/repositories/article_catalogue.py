"""Rights-aware PostgreSQL reads for the authenticated article catalogue."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    ArticleRightsVersionTable,
    ArticleSnapshotTable,
    ArticleTable,
    SourceProfileTable,
)
from app.models.article_catalogue import ArticleCatalogueSort


class ArticleCatalogueRepositoryError(RuntimeError):
    """Raised when catalogue storage fails without exposing database details."""


@dataclass(frozen=True)
class ArticleCatalogueCursor:
    """Stable location immediately after one catalogue item."""

    published_at: datetime
    article_id: UUID


@dataclass(frozen=True)
class ArticleCatalogueFilters:
    """Repository-safe filters created from a validated API query."""

    search: str | None
    provider: str | None
    published_from: datetime | None
    published_to: datetime | None
    sort: ArticleCatalogueSort


@dataclass(frozen=True)
class ArticleCatalogueRecord:
    """Internal joined row containing public metadata and visibility evidence."""

    id: UUID
    article_status: str
    title: str
    description: str | None
    canonical_url: str
    provider: str
    source_name: str
    published_at: datetime
    category: str
    snapshot_display_allowed: bool
    attribution_display_name: str
    attribution_text: str
    byline: str | None
    copyright_notice: str | None
    source_status: str
    rights_verification_status: str
    rights_display_allowed: bool
    attribution_required: bool
    rights_attribution_text: str | None
    retention_expires_at: datetime | None
    rights_last_verified_at: datetime | None
    rights_effective_from: datetime


class ArticleCatalogueRepository(Protocol):
    """Read only rights-approved catalogue records from application storage."""

    async def list_visible(
        self,
        *,
        filters: ArticleCatalogueFilters,
        cursor: ArticleCatalogueCursor | None,
        checked_at: datetime,
        limit: int,
    ) -> list[ArticleCatalogueRecord]: ...

    async def get_visible(
        self,
        *,
        article_id: UUID,
        checked_at: datetime,
    ) -> ArticleCatalogueRecord | None: ...


class SqlAlchemyArticleCatalogueRepository:
    """Query current article snapshots with fail-closed rights predicates."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def list_visible(
        self,
        *,
        filters: ArticleCatalogueFilters,
        cursor: ArticleCatalogueCursor | None,
        checked_at: datetime,
        limit: int,
    ) -> list[ArticleCatalogueRecord]:
        statement = self._base_statement(checked_at)

        if filters.search is not None:
            statement = statement.where(
                or_(
                    ArticleSnapshotTable.title.icontains(
                        filters.search,
                        autoescape=True,
                    ),
                    ArticleSnapshotTable.description.icontains(
                        filters.search,
                        autoescape=True,
                    ),
                )
            )
        if filters.provider is not None:
            statement = statement.where(
                SourceProfileTable.profile_key == filters.provider
            )
        if filters.published_from is not None:
            statement = statement.where(
                ArticleSnapshotTable.publication_date >= filters.published_from
            )
        if filters.published_to is not None:
            statement = statement.where(
                ArticleSnapshotTable.publication_date <= filters.published_to
            )

        if cursor is not None:
            if filters.sort == ArticleCatalogueSort.NEWEST:
                statement = statement.where(
                    or_(
                        ArticleSnapshotTable.publication_date < cursor.published_at,
                        and_(
                            ArticleSnapshotTable.publication_date
                            == cursor.published_at,
                            ArticleTable.id < cursor.article_id,
                        ),
                    )
                )
            else:
                statement = statement.where(
                    or_(
                        ArticleSnapshotTable.publication_date > cursor.published_at,
                        and_(
                            ArticleSnapshotTable.publication_date
                            == cursor.published_at,
                            ArticleTable.id > cursor.article_id,
                        ),
                    )
                )

        if filters.sort == ArticleCatalogueSort.NEWEST:
            statement = statement.order_by(
                ArticleSnapshotTable.publication_date.desc(),
                ArticleTable.id.desc(),
            )
        else:
            statement = statement.order_by(
                ArticleSnapshotTable.publication_date.asc(),
                ArticleTable.id.asc(),
            )

        try:
            async with self._database.session() as session:
                result = await session.execute(statement.limit(limit))
                return [self._record(row) for row in result.mappings().all()]
        except SQLAlchemyError as exc:
            raise ArticleCatalogueRepositoryError(
                "The article catalogue could not be read."
            ) from exc

    async def get_visible(
        self,
        *,
        article_id: UUID,
        checked_at: datetime,
    ) -> ArticleCatalogueRecord | None:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    self._base_statement(checked_at).where(
                        ArticleTable.id == article_id
                    )
                )
                row = result.mappings().one_or_none()
        except SQLAlchemyError as exc:
            raise ArticleCatalogueRepositoryError(
                "The article catalogue could not be read."
            ) from exc
        return None if row is None else self._record(row)

    @staticmethod
    def _base_statement(checked_at: datetime):
        rights = ArticleRightsVersionTable
        snapshot = ArticleSnapshotTable
        return (
            select(
                ArticleTable.id.label("id"),
                ArticleTable.status.label("article_status"),
                snapshot.title.label("title"),
                snapshot.description.label("description"),
                snapshot.canonical_url.label("canonical_url"),
                snapshot.source_name.label("source_name"),
                snapshot.publication_date.label("published_at"),
                snapshot.category.label("category"),
                snapshot.display_allowed.label("snapshot_display_allowed"),
                snapshot.attribution_display_name.label("attribution_display_name"),
                snapshot.attribution_text.label("attribution_text"),
                snapshot.byline.label("byline"),
                snapshot.copyright_notice.label("copyright_notice"),
                SourceProfileTable.profile_key.label("provider"),
                SourceProfileTable.status.label("source_status"),
                rights.verification_status.label("rights_verification_status"),
                rights.display_allowed.label("rights_display_allowed"),
                rights.attribution_required.label("attribution_required"),
                rights.attribution_text.label("rights_attribution_text"),
                rights.retention_expires_at.label("retention_expires_at"),
                rights.rights_last_verified_at.label("rights_last_verified_at"),
                rights.effective_from.label("rights_effective_from"),
            )
            .join(
                snapshot,
                and_(
                    snapshot.id == ArticleTable.current_snapshot_id,
                    snapshot.article_id == ArticleTable.id,
                ),
            )
            .join(
                SourceProfileTable,
                SourceProfileTable.id == ArticleTable.source_profile_id,
            )
            .join(
                rights,
                and_(
                    rights.id == ArticleTable.current_rights_version_id,
                    rights.article_id == ArticleTable.id,
                ),
            )
            .where(
                ArticleTable.status == "active",
                SourceProfileTable.status == "enabled",
                snapshot.display_allowed.is_(True),
                rights.verification_status == "verified",
                rights.display_allowed.is_(True),
                rights.rights_last_verified_at.is_not(None),
                rights.rights_last_verified_at <= checked_at,
                rights.effective_from <= checked_at,
                or_(
                    rights.retention_expires_at.is_(None),
                    rights.retention_expires_at > checked_at,
                ),
                or_(
                    rights.attribution_required.is_(False),
                    and_(
                        rights.attribution_text.is_not(None),
                        func.length(func.trim(rights.attribution_text)) > 0,
                    ),
                ),
            )
        )

    @staticmethod
    def _record(row: object) -> ArticleCatalogueRecord:
        return ArticleCatalogueRecord(
            id=row.id,
            article_status=row.article_status,
            title=row.title,
            description=row.description,
            canonical_url=row.canonical_url,
            provider=row.provider,
            source_name=row.source_name,
            published_at=row.published_at,
            category=row.category,
            snapshot_display_allowed=row.snapshot_display_allowed,
            attribution_display_name=row.attribution_display_name,
            attribution_text=row.attribution_text,
            byline=row.byline,
            copyright_notice=row.copyright_notice,
            source_status=row.source_status,
            rights_verification_status=row.rights_verification_status,
            rights_display_allowed=row.rights_display_allowed,
            attribution_required=row.attribution_required,
            rights_attribution_text=row.rights_attribution_text,
            retention_expires_at=row.retention_expires_at,
            rights_last_verified_at=row.rights_last_verified_at,
            rights_effective_from=row.rights_effective_from,
        )
