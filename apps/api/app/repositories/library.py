"""Owner-scoped PostgreSQL persistence for the private content library."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    GeneratedImageTable,
    GeneratedPostTable,
    PostVersionTable,
    SavedContentItemTable,
)


class SavedContentRepositoryError(RuntimeError):
    """Raised when private content persistence fails safely."""


class SavedContentConflictError(RuntimeError):
    """Raised when the same generated post is already saved by its owner."""


@dataclass(frozen=True)
class SavedContent:
    """Internal representation of one owner-scoped saved item."""

    id: UUID
    owner_id: UUID
    generated_post_id: UUID
    selected_post_version_id: UUID
    selected_image_id: UUID | None
    library_title: str | None
    rendered_text: str
    source_attribution: str
    saved_at: datetime
    updated_at: datetime


class SavedContentRepository(Protocol):
    """Persistence boundary whose methods always require an owner ID."""

    async def list_for_owner(self, *, owner_id: UUID) -> list[SavedContent]: ...

    async def get_for_owner(
        self, *, owner_id: UUID, item_id: UUID
    ) -> SavedContent | None: ...

    async def create_for_owner(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        selected_post_version_id: UUID,
        selected_image_id: UUID | None,
        library_title: str | None,
    ) -> SavedContent | None: ...

    async def update_title_for_owner(
        self,
        *,
        owner_id: UUID,
        item_id: UUID,
        library_title: str | None,
    ) -> SavedContent | None: ...

    async def delete_for_owner(self, *, owner_id: UUID, item_id: UUID) -> bool: ...


def _saved_content_select():
    return (
        select(
            SavedContentItemTable.id,
            SavedContentItemTable.user_id,
            SavedContentItemTable.generated_post_id,
            SavedContentItemTable.selected_post_version_id,
            SavedContentItemTable.selected_image_id,
            SavedContentItemTable.library_title,
            PostVersionTable.rendered_text,
            PostVersionTable.source_attribution,
            SavedContentItemTable.saved_at,
            SavedContentItemTable.updated_at,
        )
        .join(
            GeneratedPostTable,
            and_(
                GeneratedPostTable.id == SavedContentItemTable.generated_post_id,
                GeneratedPostTable.user_id == SavedContentItemTable.user_id,
            ),
        )
        .join(
            PostVersionTable,
            and_(
                PostVersionTable.id == SavedContentItemTable.selected_post_version_id,
                PostVersionTable.generated_post_id
                == SavedContentItemTable.generated_post_id,
            ),
        )
        .where(
            SavedContentItemTable.deleted_at.is_(None),
            GeneratedPostTable.deleted_at.is_(None),
            GeneratedPostTable.status != "deleted",
        )
    )


def _saved_content_from_row(row: object) -> SavedContent:
    return SavedContent(
        id=row.id,
        owner_id=row.user_id,
        generated_post_id=row.generated_post_id,
        selected_post_version_id=row.selected_post_version_id,
        selected_image_id=row.selected_image_id,
        library_title=row.library_title,
        rendered_text=row.rendered_text,
        source_attribution=row.source_attribution,
        saved_at=row.saved_at,
        updated_at=row.updated_at,
    )


class SqlAlchemySavedContentRepository:
    """Apply ownership in every saved-content read and write query."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def list_for_owner(self, *, owner_id: UUID) -> list[SavedContent]:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    _saved_content_select()
                    .where(
                        SavedContentItemTable.user_id == owner_id,
                        GeneratedPostTable.user_id == owner_id,
                    )
                    .order_by(SavedContentItemTable.updated_at.desc())
                )
                rows = result.all()
        except SQLAlchemyError as exc:
            raise SavedContentRepositoryError(
                "Saved content could not be listed."
            ) from exc
        return [_saved_content_from_row(row) for row in rows]

    async def get_for_owner(
        self,
        *,
        owner_id: UUID,
        item_id: UUID,
    ) -> SavedContent | None:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    _saved_content_select().where(
                        SavedContentItemTable.id == item_id,
                        SavedContentItemTable.user_id == owner_id,
                        GeneratedPostTable.user_id == owner_id,
                    )
                )
                row = result.one_or_none()
        except SQLAlchemyError as exc:
            raise SavedContentRepositoryError(
                "Saved content could not be read."
            ) from exc
        return None if row is None else _saved_content_from_row(row)

    async def _references_belong_to_owner(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        selected_post_version_id: UUID,
        selected_image_id: UUID | None,
    ) -> bool:
        statement = (
            select(GeneratedPostTable.id)
            .join(
                PostVersionTable,
                PostVersionTable.generated_post_id == GeneratedPostTable.id,
            )
            .where(
                GeneratedPostTable.id == generated_post_id,
                GeneratedPostTable.user_id == owner_id,
                GeneratedPostTable.deleted_at.is_(None),
                GeneratedPostTable.status != "deleted",
                PostVersionTable.id == selected_post_version_id,
            )
        )
        if selected_image_id is not None:
            statement = statement.join(
                GeneratedImageTable,
                GeneratedImageTable.generated_post_id == GeneratedPostTable.id,
            ).where(
                GeneratedImageTable.id == selected_image_id,
                GeneratedImageTable.deleted_at.is_(None),
                GeneratedImageTable.status == "available",
                GeneratedImageTable.safety_status == "approved",
            )

        try:
            async with self._database.session() as session:
                result = await session.execute(statement)
                return result.scalar_one_or_none() is not None
        except SQLAlchemyError as exc:
            raise SavedContentRepositoryError(
                "Saved-content references could not be checked."
            ) from exc

    async def create_for_owner(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        selected_post_version_id: UUID,
        selected_image_id: UUID | None,
        library_title: str | None,
    ) -> SavedContent | None:
        if not await self._references_belong_to_owner(
            owner_id=owner_id,
            generated_post_id=generated_post_id,
            selected_post_version_id=selected_post_version_id,
            selected_image_id=selected_image_id,
        ):
            return None

        item = SavedContentItemTable(
            user_id=owner_id,
            generated_post_id=generated_post_id,
            selected_post_version_id=selected_post_version_id,
            selected_image_id=selected_image_id,
            library_title=library_title,
        )
        try:
            async with self._database.session() as session:
                session.add(item)
                await session.commit()
                item_id = item.id
        except IntegrityError as exc:
            raise SavedContentConflictError(
                "The generated post is already saved."
            ) from exc
        except SQLAlchemyError as exc:
            raise SavedContentRepositoryError(
                "Saved content could not be created."
            ) from exc

        return await self.get_for_owner(owner_id=owner_id, item_id=item_id)

    async def update_title_for_owner(
        self,
        *,
        owner_id: UUID,
        item_id: UUID,
        library_title: str | None,
    ) -> SavedContent | None:
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    update(SavedContentItemTable)
                    .where(
                        SavedContentItemTable.id == item_id,
                        SavedContentItemTable.user_id == owner_id,
                        SavedContentItemTable.deleted_at.is_(None),
                    )
                    .values(
                        library_title=library_title,
                        updated_at=datetime.now(UTC),
                    )
                    .returning(SavedContentItemTable.id)
                )
                updated_id = result.scalar_one_or_none()
                await session.commit()
        except SQLAlchemyError as exc:
            raise SavedContentRepositoryError(
                "Saved content could not be updated."
            ) from exc

        if updated_id is None:
            return None
        return await self.get_for_owner(owner_id=owner_id, item_id=updated_id)

    async def delete_for_owner(self, *, owner_id: UUID, item_id: UUID) -> bool:
        now = datetime.now(UTC)
        try:
            async with self._database.session() as session:
                result = await session.execute(
                    update(SavedContentItemTable)
                    .where(
                        SavedContentItemTable.id == item_id,
                        SavedContentItemTable.user_id == owner_id,
                        SavedContentItemTable.deleted_at.is_(None),
                    )
                    .values(deleted_at=now, updated_at=now)
                    .returning(SavedContentItemTable.id)
                )
                deleted_id = result.scalar_one_or_none()
                await session.commit()
        except SQLAlchemyError as exc:
            raise SavedContentRepositoryError(
                "Saved content could not be deleted."
            ) from exc
        return deleted_id is not None
