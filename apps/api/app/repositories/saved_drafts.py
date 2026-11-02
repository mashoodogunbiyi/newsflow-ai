"""Transactional PostgreSQL persistence for versioned saved drafts."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    ArticleSnapshotTable,
    ArticleTable,
    GeneratedImageTable,
    GeneratedPostTable,
    GenerationRunTable,
    PostVersionHashtagTable,
    PostVersionTable,
    SavedContentItemTable,
    SavedDraftVersionTable,
)

WORD_PATTERN = re.compile(r"\b[\w'-]+\b", re.UNICODE)


class SavedDraftRepositoryError(RuntimeError):
    """Raised when draft persistence fails without exposing database details."""


class SavedDraftDuplicateError(RuntimeError):
    """Raised when a generated post already has a saved-draft record."""


class SavedDraftIdempotencyConflict(RuntimeError):
    """Raised when one save key is reused for different content."""


class SavedDraftVersionConflict(RuntimeError):
    """Raised when an update is based on a stale saved-draft version."""


@dataclass(frozen=True)
class SavedDraftImage:
    """Permitted selected-image metadata safe for private API responses."""

    id: UUID
    alt_text: str | None
    mime_type: str
    width_px: int
    height_px: int
    ai_generated: bool
    ai_disclosure_required: bool


@dataclass(frozen=True)
class SavedDraft:
    """Private saved draft with source and original-generation lineage."""

    id: UUID
    owner_id: UUID
    generated_post_id: UUID
    source_generation_id: UUID
    original_post_version_id: UUID
    current_post_version_id: UUID
    selected_image_id: UUID | None
    selected_image: SavedDraftImage | None
    title: str | None
    edited_text: str
    tone: str
    length_option: str
    status: str
    version: int
    article_id: UUID
    source_title: str
    source_url: str
    source_attribution: str
    model_identifier: str
    prompt_version: str
    generation_created_at: datetime
    saved_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class SavedDraftPage:
    """One bounded owner-scoped page in stable newest-first order."""

    items: list[SavedDraft]
    page: int
    page_size: int
    total_items: int


@dataclass(frozen=True)
class SavedDraftVersion:
    """One immutable owner-scoped saved-draft history entry."""

    id: UUID
    saved_draft_id: UUID
    owner_id: UUID
    generated_post_id: UUID
    post_version_id: UUID
    selected_image_id: UUID | None
    selected_image: SavedDraftImage | None
    generation_run_id: UUID | None
    restored_from_version_id: UUID | None
    version_number: int
    change_type: str
    title: str | None
    edited_text: str
    tone: str
    length_option: str
    article_id: UUID
    source_title: str
    source_url: str
    source_attribution: str
    created_at: datetime


@dataclass(frozen=True)
class SavedDraftVersionPage:
    """One bounded newest-first history page."""

    items: list[SavedDraftVersion]
    page: int
    page_size: int
    total_items: int


class SavedDraftRepository(Protocol):
    """Owner-scoped save and update persistence boundary."""

    async def get_for_owner(
        self, *, owner_id: UUID, saved_draft_id: UUID
    ) -> SavedDraft | None: ...

    async def list_for_owner(
        self,
        *,
        owner_id: UUID,
        page: int,
        page_size: int,
    ) -> SavedDraftPage: ...

    async def create_for_owner(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        title: str | None,
        edited_text: str,
        selected_image_id: UUID | None,
        save_key_hash: str,
        payload_hash: str,
    ) -> SavedDraft | None: ...

    async def update_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        expected_version: int,
        title: str | None,
        edited_text: str,
        selected_image_id: UUID | None,
    ) -> SavedDraft | None: ...

    async def list_versions_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        page: int,
        page_size: int,
    ) -> SavedDraftVersionPage | None: ...

    async def get_version_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        version_id: UUID,
    ) -> SavedDraftVersion | None: ...

    async def restore_version_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        version_id: UUID,
        expected_version: int,
    ) -> SavedDraft | None: ...


def _saved_draft_statement():
    selected_version = aliased(PostVersionTable, name="selected_version")
    original_version = aliased(PostVersionTable, name="original_version")
    permitted_image = aliased(GeneratedImageTable, name="permitted_image")
    return (
        select(
            SavedContentItemTable.id,
            SavedContentItemTable.user_id,
            SavedContentItemTable.generated_post_id,
            SavedContentItemTable.source_generation_id,
            original_version.id.label("original_post_version_id"),
            selected_version.id.label("current_post_version_id"),
            SavedContentItemTable.selected_image_id,
            permitted_image.id.label("permitted_image_id"),
            permitted_image.alt_text.label("image_alt_text"),
            permitted_image.mime_type.label("image_mime_type"),
            permitted_image.width_px.label("image_width_px"),
            permitted_image.height_px.label("image_height_px"),
            permitted_image.ai_generated.label("image_ai_generated"),
            permitted_image.ai_disclosure_required.label(
                "image_ai_disclosure_required"
            ),
            SavedContentItemTable.library_title,
            selected_version.rendered_text,
            selected_version.tone,
            selected_version.length_option,
            GeneratedPostTable.status,
            SavedContentItemTable.version,
            ArticleTable.id.label("article_id"),
            ArticleSnapshotTable.title.label("source_title"),
            ArticleSnapshotTable.canonical_url.label("source_url"),
            selected_version.source_attribution,
            GenerationRunTable.model.label("model_identifier"),
            GenerationRunTable.prompt_template_version.label("prompt_version"),
            GenerationRunTable.created_at.label("generation_created_at"),
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
            selected_version,
            and_(
                selected_version.id == SavedContentItemTable.selected_post_version_id,
                selected_version.generated_post_id
                == SavedContentItemTable.generated_post_id,
            ),
        )
        .join(
            GenerationRunTable,
            and_(
                GenerationRunTable.id == SavedContentItemTable.source_generation_id,
                GenerationRunTable.generated_post_id
                == SavedContentItemTable.generated_post_id,
            ),
        )
        .join(
            original_version,
            and_(
                original_version.generation_run_id == GenerationRunTable.id,
                original_version.generated_post_id
                == SavedContentItemTable.generated_post_id,
            ),
        )
        .join(
            ArticleSnapshotTable,
            ArticleSnapshotTable.id == GeneratedPostTable.article_snapshot_id,
        )
        .join(ArticleTable, ArticleTable.id == ArticleSnapshotTable.article_id)
        .outerjoin(
            permitted_image,
            and_(
                permitted_image.id == SavedContentItemTable.selected_image_id,
                permitted_image.user_id == SavedContentItemTable.user_id,
                permitted_image.generated_post_id
                == SavedContentItemTable.generated_post_id,
                permitted_image.status == "available",
                permitted_image.safety_status == "approved",
                permitted_image.validation_status == "passed",
                permitted_image.generation_status == "completed",
                permitted_image.deleted_at.is_(None),
            ),
        )
        .where(
            SavedContentItemTable.deleted_at.is_(None),
            GeneratedPostTable.deleted_at.is_(None),
            GeneratedPostTable.status != "deleted",
        )
    )


def _from_row(row: object) -> SavedDraft:
    selected_image = None
    if row.permitted_image_id is not None:
        selected_image = SavedDraftImage(
            id=row.permitted_image_id,
            alt_text=row.image_alt_text,
            mime_type=row.image_mime_type,
            width_px=row.image_width_px,
            height_px=row.image_height_px,
            ai_generated=row.image_ai_generated,
            ai_disclosure_required=row.image_ai_disclosure_required,
        )
    return SavedDraft(
        id=row.id,
        owner_id=row.user_id,
        generated_post_id=row.generated_post_id,
        source_generation_id=row.source_generation_id,
        original_post_version_id=row.original_post_version_id,
        current_post_version_id=row.current_post_version_id,
        selected_image_id=row.selected_image_id,
        selected_image=selected_image,
        title=row.library_title,
        edited_text=row.rendered_text,
        tone=row.tone,
        length_option=row.length_option,
        status=row.status,
        version=row.version,
        article_id=row.article_id,
        source_title=row.source_title,
        source_url=row.source_url,
        source_attribution=row.source_attribution,
        model_identifier=row.model_identifier,
        prompt_version=row.prompt_version,
        generation_created_at=row.generation_created_at,
        saved_at=row.saved_at,
        updated_at=row.updated_at,
    )


def _saved_draft_version_statement():
    permitted_image = aliased(GeneratedImageTable, name="history_image")
    return (
        select(
            SavedDraftVersionTable.id,
            SavedDraftVersionTable.saved_draft_id,
            SavedDraftVersionTable.user_id,
            SavedDraftVersionTable.generated_post_id,
            SavedDraftVersionTable.post_version_id,
            SavedDraftVersionTable.selected_image_id,
            SavedDraftVersionTable.generation_run_id,
            SavedDraftVersionTable.restored_from_version_id,
            SavedDraftVersionTable.version_number,
            SavedDraftVersionTable.change_type,
            SavedDraftVersionTable.library_title,
            SavedDraftVersionTable.created_at,
            PostVersionTable.rendered_text,
            PostVersionTable.tone,
            PostVersionTable.length_option,
            PostVersionTable.source_attribution,
            ArticleTable.id.label("article_id"),
            ArticleSnapshotTable.title.label("source_title"),
            ArticleSnapshotTable.canonical_url.label("source_url"),
            permitted_image.id.label("permitted_image_id"),
            permitted_image.alt_text.label("image_alt_text"),
            permitted_image.mime_type.label("image_mime_type"),
            permitted_image.width_px.label("image_width_px"),
            permitted_image.height_px.label("image_height_px"),
            permitted_image.ai_generated.label("image_ai_generated"),
            permitted_image.ai_disclosure_required.label(
                "image_ai_disclosure_required"
            ),
        )
        .join(
            SavedContentItemTable,
            and_(
                SavedContentItemTable.id == SavedDraftVersionTable.saved_draft_id,
                SavedContentItemTable.user_id == SavedDraftVersionTable.user_id,
                SavedContentItemTable.generated_post_id
                == SavedDraftVersionTable.generated_post_id,
            ),
        )
        .join(
            GeneratedPostTable,
            and_(
                GeneratedPostTable.id == SavedDraftVersionTable.generated_post_id,
                GeneratedPostTable.user_id == SavedDraftVersionTable.user_id,
            ),
        )
        .join(
            PostVersionTable,
            and_(
                PostVersionTable.id == SavedDraftVersionTable.post_version_id,
                PostVersionTable.generated_post_id
                == SavedDraftVersionTable.generated_post_id,
            ),
        )
        .join(
            ArticleSnapshotTable,
            ArticleSnapshotTable.id == GeneratedPostTable.article_snapshot_id,
        )
        .join(ArticleTable, ArticleTable.id == ArticleSnapshotTable.article_id)
        .outerjoin(
            permitted_image,
            and_(
                permitted_image.id == SavedDraftVersionTable.selected_image_id,
                permitted_image.user_id == SavedDraftVersionTable.user_id,
                permitted_image.generated_post_id
                == SavedDraftVersionTable.generated_post_id,
                permitted_image.status == "available",
                permitted_image.safety_status == "approved",
                permitted_image.validation_status == "passed",
                permitted_image.generation_status == "completed",
                permitted_image.deleted_at.is_(None),
            ),
        )
        .where(
            SavedContentItemTable.deleted_at.is_(None),
            GeneratedPostTable.deleted_at.is_(None),
            GeneratedPostTable.status != "deleted",
        )
    )


def _version_from_row(row: object) -> SavedDraftVersion:
    selected_image = None
    if row.permitted_image_id is not None:
        selected_image = SavedDraftImage(
            id=row.permitted_image_id,
            alt_text=row.image_alt_text,
            mime_type=row.image_mime_type,
            width_px=row.image_width_px,
            height_px=row.image_height_px,
            ai_generated=row.image_ai_generated,
            ai_disclosure_required=row.image_ai_disclosure_required,
        )
    return SavedDraftVersion(
        id=row.id,
        saved_draft_id=row.saved_draft_id,
        owner_id=row.user_id,
        generated_post_id=row.generated_post_id,
        post_version_id=row.post_version_id,
        selected_image_id=row.selected_image_id,
        selected_image=selected_image,
        generation_run_id=row.generation_run_id,
        restored_from_version_id=row.restored_from_version_id,
        version_number=row.version_number,
        change_type=row.change_type,
        title=row.library_title,
        edited_text=row.rendered_text,
        tone=row.tone,
        length_option=row.length_option,
        article_id=row.article_id,
        source_title=row.source_title,
        source_url=row.source_url,
        source_attribution=row.source_attribution,
        created_at=row.created_at,
    )


class SqlAlchemySavedDraftRepository:
    """Save immutable manual versions and update the selected library version."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def get_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
    ) -> SavedDraft | None:
        try:
            async with self._database.session() as session:
                row = (
                    await session.execute(
                        _saved_draft_statement().where(
                            SavedContentItemTable.id == saved_draft_id,
                            SavedContentItemTable.user_id == owner_id,
                            GeneratedPostTable.user_id == owner_id,
                        )
                    )
                ).one_or_none()
        except SQLAlchemyError as exc:
            raise SavedDraftRepositoryError(
                "The saved draft could not be read."
            ) from exc
        return None if row is None else _from_row(row)

    async def list_for_owner(
        self,
        *,
        owner_id: UUID,
        page: int,
        page_size: int,
    ) -> SavedDraftPage:
        offset = (page - 1) * page_size
        count_statement = (
            select(func.count())
            .select_from(SavedContentItemTable)
            .join(
                GeneratedPostTable,
                and_(
                    GeneratedPostTable.id == SavedContentItemTable.generated_post_id,
                    GeneratedPostTable.user_id == SavedContentItemTable.user_id,
                ),
            )
            .where(
                SavedContentItemTable.user_id == owner_id,
                SavedContentItemTable.deleted_at.is_(None),
                GeneratedPostTable.user_id == owner_id,
                GeneratedPostTable.deleted_at.is_(None),
                GeneratedPostTable.status != "deleted",
            )
        )
        try:
            async with self._database.session() as session:
                total_items = int((await session.execute(count_statement)).scalar_one())
                rows = (
                    await session.execute(
                        _saved_draft_statement()
                        .where(
                            SavedContentItemTable.user_id == owner_id,
                            GeneratedPostTable.user_id == owner_id,
                        )
                        .order_by(
                            SavedContentItemTable.updated_at.desc(),
                            SavedContentItemTable.id.desc(),
                        )
                        .offset(offset)
                        .limit(page_size)
                    )
                ).all()
        except SQLAlchemyError as exc:
            raise SavedDraftRepositoryError(
                "Saved drafts could not be listed."
            ) from exc
        return SavedDraftPage(
            items=[_from_row(row) for row in rows],
            page=page,
            page_size=page_size,
            total_items=total_items,
        )

    async def create_for_owner(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        title: str | None,
        edited_text: str,
        selected_image_id: UUID | None,
        save_key_hash: str,
        payload_hash: str,
    ) -> SavedDraft | None:
        saved_draft_id: UUID | None = None
        try:
            async with self._database.session() as session:
                async with session.begin():
                    await session.execute(
                        select(
                            func.pg_advisory_xact_lock(
                                func.hashtextextended(f"{owner_id}:{save_key_hash}", 0)
                            )
                        )
                    )
                    existing = (
                        await session.execute(
                            select(
                                SavedContentItemTable.id,
                                SavedContentItemTable.save_payload_hash,
                                SavedContentItemTable.deleted_at,
                            ).where(
                                SavedContentItemTable.user_id == owner_id,
                                SavedContentItemTable.save_key_hash == save_key_hash,
                            )
                        )
                    ).one_or_none()
                    if existing is not None:
                        if existing.save_payload_hash != payload_hash:
                            raise SavedDraftIdempotencyConflict(
                                "The save key has already been used for different content."
                            )
                        if existing.deleted_at is not None:
                            raise SavedDraftDuplicateError(
                                "The saved draft already exists."
                            )
                        saved_draft_id = existing.id
                    else:
                        context = await self._generation_context(
                            session,
                            owner_id=owner_id,
                            generation_id=generation_id,
                        )
                        if context is None or not await self._image_is_valid(
                            session,
                            owner_id=owner_id,
                            generated_post_id=context.generated_post_id,
                            selected_image_id=selected_image_id,
                        ):
                            return None
                        saved_draft_id = uuid4()
                        version_id = await self._append_manual_version(
                            session,
                            context=context,
                            owner_id=owner_id,
                            edited_text=edited_text,
                        )
                        now = datetime.now(UTC)
                        saved_item = SavedContentItemTable(
                            id=saved_draft_id,
                            user_id=owner_id,
                            generated_post_id=context.generated_post_id,
                            source_generation_id=generation_id,
                            selected_post_version_id=version_id,
                            selected_image_id=selected_image_id,
                            library_title=title,
                            version=1,
                            save_key_hash=save_key_hash,
                            save_payload_hash=payload_hash,
                            saved_at=now,
                            updated_at=now,
                        )
                        session.add(saved_item)
                        await session.flush()
                        session.add(
                            SavedDraftVersionTable(
                                id=uuid4(),
                                saved_draft_id=saved_draft_id,
                                user_id=owner_id,
                                generated_post_id=context.generated_post_id,
                                post_version_id=version_id,
                                selected_image_id=selected_image_id,
                                generation_run_id=generation_id,
                                restored_from_version_id=None,
                                version_number=1,
                                change_type="initial_save",
                                library_title=title,
                                created_at=now,
                            )
                        )
                        await session.execute(
                            update(GeneratedPostTable)
                            .where(
                                GeneratedPostTable.id == context.generated_post_id,
                                GeneratedPostTable.user_id == owner_id,
                            )
                            .values(status="saved", updated_at=now)
                        )
        except (SavedDraftDuplicateError, SavedDraftIdempotencyConflict):
            raise
        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            )
            if constraint_name in {
                "uq_saved_content_post",
                "uq_saved_content_owner_save_key",
                "uq_post_current_version",
                "uq_post_version_number",
            }:
                raise SavedDraftDuplicateError(
                    "The generated post is already saved."
                ) from exc
            raise SavedDraftRepositoryError("The draft could not be saved.") from exc
        except SQLAlchemyError as exc:
            raise SavedDraftRepositoryError("The draft could not be saved.") from exc

        if saved_draft_id is None:
            return None
        return await self.get_for_owner(
            owner_id=owner_id,
            saved_draft_id=saved_draft_id,
        )

    async def update_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        expected_version: int,
        title: str | None,
        edited_text: str,
        selected_image_id: UUID | None,
    ) -> SavedDraft | None:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    context = await self._saved_context_for_update(
                        session,
                        owner_id=owner_id,
                        saved_draft_id=saved_draft_id,
                    )
                    if context is None:
                        return None
                    if context.version != expected_version:
                        raise SavedDraftVersionConflict(
                            "The saved draft has changed since it was loaded."
                        )
                    if not await self._image_is_valid(
                        session,
                        owner_id=owner_id,
                        generated_post_id=context.generated_post_id,
                        selected_image_id=selected_image_id,
                    ):
                        return None

                    text_changed = context.rendered_text != edited_text
                    state_changed = (
                        text_changed
                        or context.library_title != title
                        or context.selected_image_id != selected_image_id
                    )
                    if not state_changed:
                        return await self._get_in_session(
                            session,
                            owner_id=owner_id,
                            saved_draft_id=saved_draft_id,
                        )

                    selected_version_id = context.current_post_version_id
                    history_change_type = "metadata_update"
                    history_generation_run_id = None
                    if text_changed:
                        regenerated = await self._matching_ai_version(
                            session,
                            generated_post_id=context.generated_post_id,
                            edited_text=edited_text,
                        )
                        if regenerated is None:
                            selected_version_id = await self._append_manual_version(
                                session,
                                context=context,
                                owner_id=owner_id,
                                edited_text=edited_text,
                            )
                            history_change_type = "manual_edit"
                        else:
                            selected_version_id = await self._append_restored_version(
                                session,
                                context=context,
                                historical_post_version_id=regenerated.id,
                                owner_id=owner_id,
                            )
                            history_change_type = "text_regeneration"
                            history_generation_run_id = regenerated.generation_run_id
                    now = datetime.now(UTC)
                    result = await session.execute(
                        update(SavedContentItemTable)
                        .where(
                            SavedContentItemTable.id == saved_draft_id,
                            SavedContentItemTable.user_id == owner_id,
                            SavedContentItemTable.version == expected_version,
                            SavedContentItemTable.deleted_at.is_(None),
                        )
                        .values(
                            selected_post_version_id=selected_version_id,
                            selected_image_id=selected_image_id,
                            library_title=title,
                            version=expected_version + 1,
                            updated_at=now,
                        )
                        .returning(SavedContentItemTable.id)
                    )
                    if result.scalar_one_or_none() is None:
                        raise SavedDraftVersionConflict(
                            "The saved draft has changed since it was loaded."
                        )
                    change_type = history_change_type
                    generation_run_id = history_generation_run_id
                    if (
                        not text_changed
                        and context.selected_image_id != selected_image_id
                    ):
                        change_type = "image_selection"
                        image_context = await self._image_history_context(
                            session,
                            owner_id=owner_id,
                            generated_post_id=context.generated_post_id,
                            selected_image_id=selected_image_id,
                        )
                        if image_context is not None:
                            generation_run_id = image_context.generation_run_id
                            change_type = (
                                "image_regeneration"
                                if image_context.parent_image_id is not None
                                else "image_selection"
                            )
                    session.add(
                        SavedDraftVersionTable(
                            id=uuid4(),
                            saved_draft_id=saved_draft_id,
                            user_id=owner_id,
                            generated_post_id=context.generated_post_id,
                            post_version_id=selected_version_id,
                            selected_image_id=selected_image_id,
                            generation_run_id=generation_run_id,
                            restored_from_version_id=None,
                            version_number=expected_version + 1,
                            change_type=change_type,
                            library_title=title,
                            created_at=now,
                        )
                    )
                    await session.execute(
                        update(GeneratedPostTable)
                        .where(
                            GeneratedPostTable.id == context.generated_post_id,
                            GeneratedPostTable.user_id == owner_id,
                        )
                        .values(status="saved", updated_at=now)
                    )
        except SavedDraftVersionConflict:
            raise
        except IntegrityError as exc:
            raise SavedDraftRepositoryError(
                "The draft update could not be stored."
            ) from exc
        except SQLAlchemyError as exc:
            raise SavedDraftRepositoryError("The draft could not be updated.") from exc

        return await self.get_for_owner(
            owner_id=owner_id,
            saved_draft_id=saved_draft_id,
        )

    async def list_versions_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        page: int,
        page_size: int,
    ) -> SavedDraftVersionPage | None:
        offset = (page - 1) * page_size
        owned_draft = and_(
            SavedContentItemTable.id == saved_draft_id,
            SavedContentItemTable.user_id == owner_id,
            SavedContentItemTable.deleted_at.is_(None),
        )
        try:
            async with self._database.session() as session:
                exists = (
                    await session.execute(
                        select(SavedContentItemTable.id).where(owned_draft)
                    )
                ).scalar_one_or_none()
                if exists is None:
                    return None
                total_items = int(
                    (
                        await session.execute(
                            select(func.count())
                            .select_from(SavedDraftVersionTable)
                            .where(
                                SavedDraftVersionTable.saved_draft_id == saved_draft_id,
                                SavedDraftVersionTable.user_id == owner_id,
                            )
                        )
                    ).scalar_one()
                )
                rows = (
                    await session.execute(
                        _saved_draft_version_statement()
                        .where(
                            SavedDraftVersionTable.saved_draft_id == saved_draft_id,
                            SavedDraftVersionTable.user_id == owner_id,
                        )
                        .order_by(
                            SavedDraftVersionTable.version_number.desc(),
                            SavedDraftVersionTable.id.desc(),
                        )
                        .offset(offset)
                        .limit(page_size)
                    )
                ).all()
        except SQLAlchemyError as exc:
            raise SavedDraftRepositoryError(
                "Draft version history could not be listed."
            ) from exc
        return SavedDraftVersionPage(
            items=[_version_from_row(row) for row in rows],
            page=page,
            page_size=page_size,
            total_items=total_items,
        )

    async def get_version_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        version_id: UUID,
    ) -> SavedDraftVersion | None:
        try:
            async with self._database.session() as session:
                row = (
                    await session.execute(
                        _saved_draft_version_statement().where(
                            SavedDraftVersionTable.id == version_id,
                            SavedDraftVersionTable.saved_draft_id == saved_draft_id,
                            SavedDraftVersionTable.user_id == owner_id,
                        )
                    )
                ).one_or_none()
        except SQLAlchemyError as exc:
            raise SavedDraftRepositoryError(
                "The draft version could not be read."
            ) from exc
        return None if row is None else _version_from_row(row)

    async def restore_version_for_owner(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        version_id: UUID,
        expected_version: int,
    ) -> SavedDraft | None:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    context = await self._saved_context_for_update(
                        session,
                        owner_id=owner_id,
                        saved_draft_id=saved_draft_id,
                    )
                    historical = (
                        await session.execute(
                            _saved_draft_version_statement().where(
                                SavedDraftVersionTable.id == version_id,
                                SavedDraftVersionTable.saved_draft_id == saved_draft_id,
                                SavedDraftVersionTable.user_id == owner_id,
                            )
                        )
                    ).one_or_none()
                    if context is None or historical is None:
                        return None
                    if context.version != expected_version:
                        raise SavedDraftVersionConflict(
                            "The saved draft has changed since it was loaded."
                        )
                    if not await self._image_is_valid(
                        session,
                        owner_id=owner_id,
                        generated_post_id=context.generated_post_id,
                        selected_image_id=historical.selected_image_id,
                    ):
                        return None

                    restored_post_version_id = await self._append_restored_version(
                        session,
                        context=context,
                        historical_post_version_id=historical.post_version_id,
                        owner_id=owner_id,
                    )
                    now = datetime.now(UTC)
                    result = await session.execute(
                        update(SavedContentItemTable)
                        .where(
                            SavedContentItemTable.id == saved_draft_id,
                            SavedContentItemTable.user_id == owner_id,
                            SavedContentItemTable.version == expected_version,
                            SavedContentItemTable.deleted_at.is_(None),
                        )
                        .values(
                            selected_post_version_id=restored_post_version_id,
                            selected_image_id=historical.selected_image_id,
                            library_title=historical.library_title,
                            version=expected_version + 1,
                            updated_at=now,
                        )
                        .returning(SavedContentItemTable.id)
                    )
                    if result.scalar_one_or_none() is None:
                        raise SavedDraftVersionConflict(
                            "The saved draft has changed since it was loaded."
                        )
                    session.add(
                        SavedDraftVersionTable(
                            id=uuid4(),
                            saved_draft_id=saved_draft_id,
                            user_id=owner_id,
                            generated_post_id=context.generated_post_id,
                            post_version_id=restored_post_version_id,
                            selected_image_id=historical.selected_image_id,
                            generation_run_id=None,
                            restored_from_version_id=version_id,
                            version_number=expected_version + 1,
                            change_type="version_restoration",
                            library_title=historical.library_title,
                            created_at=now,
                        )
                    )
        except SavedDraftVersionConflict:
            raise
        except SQLAlchemyError as exc:
            raise SavedDraftRepositoryError(
                "The draft version could not be restored."
            ) from exc
        return await self.get_for_owner(
            owner_id=owner_id,
            saved_draft_id=saved_draft_id,
        )

    async def _get_in_session(
        self,
        session: AsyncSession,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
    ) -> SavedDraft | None:
        row = (
            await session.execute(
                _saved_draft_statement().where(
                    SavedContentItemTable.id == saved_draft_id,
                    SavedContentItemTable.user_id == owner_id,
                    GeneratedPostTable.user_id == owner_id,
                )
            )
        ).one_or_none()
        return None if row is None else _from_row(row)

    @staticmethod
    async def _generation_context(
        session: AsyncSession,
        *,
        owner_id: UUID,
        generation_id: UUID,
    ):
        current_version = aliased(PostVersionTable, name="current_version")
        original_version = aliased(PostVersionTable, name="source_ai_version")
        return (
            await session.execute(
                select(
                    GeneratedPostTable.id.label("generated_post_id"),
                    current_version.id.label("current_post_version_id"),
                    current_version.version_number,
                    current_version.rendered_text,
                    current_version.tone,
                    current_version.length_option,
                    current_version.audience,
                    current_version.source_attribution,
                )
                .join(
                    GenerationRunTable,
                    GenerationRunTable.generated_post_id == GeneratedPostTable.id,
                )
                .join(
                    original_version,
                    and_(
                        original_version.generated_post_id == GeneratedPostTable.id,
                        original_version.generation_run_id == GenerationRunTable.id,
                        original_version.origin == "ai",
                    ),
                )
                .join(
                    current_version,
                    and_(
                        current_version.generated_post_id == GeneratedPostTable.id,
                        current_version.is_current.is_(True),
                    ),
                )
                .where(
                    GenerationRunTable.id == generation_id,
                    GenerationRunTable.generation_type == "post",
                    GenerationRunTable.status == "succeeded",
                    GeneratedPostTable.user_id == owner_id,
                    GeneratedPostTable.deleted_at.is_(None),
                    GeneratedPostTable.status != "deleted",
                )
                .with_for_update()
            )
        ).one_or_none()

    @staticmethod
    async def _saved_context_for_update(
        session: AsyncSession,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
    ):
        return (
            await session.execute(
                select(
                    SavedContentItemTable.id,
                    SavedContentItemTable.generated_post_id,
                    SavedContentItemTable.selected_post_version_id.label(
                        "current_post_version_id"
                    ),
                    SavedContentItemTable.selected_image_id,
                    SavedContentItemTable.library_title,
                    SavedContentItemTable.version,
                    PostVersionTable.version_number,
                    PostVersionTable.rendered_text,
                    PostVersionTable.tone,
                    PostVersionTable.length_option,
                    PostVersionTable.audience,
                    PostVersionTable.source_attribution,
                )
                .join(
                    GeneratedPostTable,
                    and_(
                        GeneratedPostTable.id
                        == SavedContentItemTable.generated_post_id,
                        GeneratedPostTable.user_id == SavedContentItemTable.user_id,
                    ),
                )
                .join(
                    PostVersionTable,
                    and_(
                        PostVersionTable.id
                        == SavedContentItemTable.selected_post_version_id,
                        PostVersionTable.generated_post_id
                        == SavedContentItemTable.generated_post_id,
                        PostVersionTable.is_current.is_(True),
                    ),
                )
                .where(
                    SavedContentItemTable.id == saved_draft_id,
                    SavedContentItemTable.user_id == owner_id,
                    SavedContentItemTable.deleted_at.is_(None),
                    GeneratedPostTable.user_id == owner_id,
                    GeneratedPostTable.deleted_at.is_(None),
                    GeneratedPostTable.status != "deleted",
                )
                .with_for_update()
            )
        ).one_or_none()

    @staticmethod
    async def _image_is_valid(
        session: AsyncSession,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        selected_image_id: UUID | None,
    ) -> bool:
        if selected_image_id is None:
            return True
        image_id = (
            await session.execute(
                select(GeneratedImageTable.id).where(
                    GeneratedImageTable.id == selected_image_id,
                    GeneratedImageTable.user_id == owner_id,
                    GeneratedImageTable.generated_post_id == generated_post_id,
                    GeneratedImageTable.status == "available",
                    GeneratedImageTable.safety_status == "approved",
                    GeneratedImageTable.validation_status == "passed",
                    GeneratedImageTable.generation_status == "completed",
                    GeneratedImageTable.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        return image_id is not None

    @staticmethod
    async def _image_history_context(
        session: AsyncSession,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        selected_image_id: UUID | None,
    ):
        if selected_image_id is None:
            return None
        return (
            await session.execute(
                select(
                    GeneratedImageTable.generation_run_id,
                    GeneratedImageTable.parent_image_id,
                ).where(
                    GeneratedImageTable.id == selected_image_id,
                    GeneratedImageTable.user_id == owner_id,
                    GeneratedImageTable.generated_post_id == generated_post_id,
                    GeneratedImageTable.status == "available",
                    GeneratedImageTable.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    @staticmethod
    async def _matching_ai_version(
        session: AsyncSession,
        *,
        generated_post_id: UUID,
        edited_text: str,
    ):
        return (
            await session.execute(
                select(
                    PostVersionTable.id,
                    PostVersionTable.generation_run_id,
                )
                .where(
                    PostVersionTable.generated_post_id == generated_post_id,
                    PostVersionTable.origin == "ai",
                    PostVersionTable.generation_run_id.is_not(None),
                    PostVersionTable.rendered_text == edited_text,
                )
                .order_by(PostVersionTable.version_number.desc())
                .limit(1)
            )
        ).one_or_none()

    @staticmethod
    async def _append_restored_version(
        session: AsyncSession,
        *,
        context: object,
        historical_post_version_id: UUID,
        owner_id: UUID,
    ) -> UUID:
        historical = (
            await session.execute(
                select(PostVersionTable).where(
                    PostVersionTable.id == historical_post_version_id,
                    PostVersionTable.generated_post_id == context.generated_post_id,
                )
            )
        ).scalar_one_or_none()
        if historical is None:
            raise SavedDraftRepositoryError(
                "The historical draft text is no longer available."
            )
        hashtags = (
            await session.execute(
                select(
                    PostVersionHashtagTable.position,
                    PostVersionHashtagTable.hashtag,
                )
                .where(
                    PostVersionHashtagTable.post_version_id
                    == historical_post_version_id
                )
                .order_by(PostVersionHashtagTable.position)
            )
        ).all()
        if not 3 <= len(hashtags) <= 5:
            raise SavedDraftRepositoryError(
                "The historical draft metadata is incomplete."
            )

        await session.execute(
            update(PostVersionTable)
            .where(
                PostVersionTable.id == context.current_post_version_id,
                PostVersionTable.generated_post_id == context.generated_post_id,
                PostVersionTable.is_current.is_(True),
            )
            .values(is_current=False)
        )
        restored_id = uuid4()
        session.add(
            PostVersionTable(
                id=restored_id,
                generated_post_id=context.generated_post_id,
                generation_run_id=None,
                previous_version_id=context.current_post_version_id,
                version_number=context.version_number + 1,
                origin="manual",
                tone=historical.tone,
                length_option=historical.length_option,
                audience=historical.audience,
                hook=historical.hook,
                summary=historical.summary,
                insight=historical.insight,
                call_to_action=historical.call_to_action,
                rendered_text=historical.rendered_text,
                source_attribution=historical.source_attribution,
                word_count=historical.word_count,
                is_current=True,
                created_by_user_id=owner_id,
                created_at=datetime.now(UTC),
            )
        )
        await session.flush()
        for position, hashtag in hashtags:
            session.add(
                PostVersionHashtagTable(
                    post_version_id=restored_id,
                    position=position,
                    hashtag=hashtag,
                )
            )
        return restored_id

    @staticmethod
    async def _append_manual_version(
        session: AsyncSession,
        *,
        context: object,
        owner_id: UUID,
        edited_text: str,
    ) -> UUID:
        current_version_id = context.current_post_version_id
        hashtags = (
            await session.execute(
                select(
                    PostVersionHashtagTable.position,
                    PostVersionHashtagTable.hashtag,
                )
                .where(PostVersionHashtagTable.post_version_id == current_version_id)
                .order_by(PostVersionHashtagTable.position)
            )
        ).all()
        if not 3 <= len(hashtags) <= 5:
            raise SavedDraftRepositoryError(
                "The existing draft metadata is incomplete."
            )

        await session.execute(
            update(PostVersionTable)
            .where(
                PostVersionTable.id == current_version_id,
                PostVersionTable.generated_post_id == context.generated_post_id,
                PostVersionTable.is_current.is_(True),
            )
            .values(is_current=False)
        )
        version_id = uuid4()
        manual_version = PostVersionTable(
            id=version_id,
            generated_post_id=context.generated_post_id,
            generation_run_id=None,
            previous_version_id=current_version_id,
            version_number=context.version_number + 1,
            origin="manual",
            tone=context.tone,
            length_option=context.length_option,
            audience=context.audience,
            hook=SqlAlchemySavedDraftRepository._hook(edited_text),
            summary=edited_text,
            insight=None,
            call_to_action=None,
            rendered_text=edited_text,
            source_attribution=context.source_attribution,
            word_count=len(WORD_PATTERN.findall(edited_text)),
            is_current=True,
            created_by_user_id=owner_id,
            created_at=datetime.now(UTC),
        )
        session.add(manual_version)
        await session.flush()
        for position, hashtag in hashtags:
            session.add(
                PostVersionHashtagTable(
                    post_version_id=version_id,
                    position=position,
                    hashtag=hashtag,
                )
            )
        return version_id

    @staticmethod
    def _hook(text: str) -> str:
        for line in text.splitlines():
            if line.strip():
                return line.strip()
        return text.strip()
