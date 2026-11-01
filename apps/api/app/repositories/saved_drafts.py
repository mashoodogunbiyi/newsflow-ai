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
class SavedDraft:
    """Private saved draft with source and original-generation lineage."""

    id: UUID
    owner_id: UUID
    generated_post_id: UUID
    source_generation_id: UUID
    original_post_version_id: UUID
    current_post_version_id: UUID
    selected_image_id: UUID | None
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


class SavedDraftRepository(Protocol):
    """Owner-scoped save and update persistence boundary."""

    async def get_for_owner(
        self, *, owner_id: UUID, saved_draft_id: UUID
    ) -> SavedDraft | None: ...

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


def _saved_draft_statement():
    selected_version = aliased(PostVersionTable, name="selected_version")
    original_version = aliased(PostVersionTable, name="original_version")
    return (
        select(
            SavedContentItemTable.id,
            SavedContentItemTable.user_id,
            SavedContentItemTable.generated_post_id,
            SavedContentItemTable.source_generation_id,
            original_version.id.label("original_post_version_id"),
            selected_version.id.label("current_post_version_id"),
            SavedContentItemTable.selected_image_id,
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
        .where(
            SavedContentItemTable.deleted_at.is_(None),
            GeneratedPostTable.deleted_at.is_(None),
            GeneratedPostTable.status != "deleted",
        )
    )


def _from_row(row: object) -> SavedDraft:
    return SavedDraft(
        id=row.id,
        owner_id=row.user_id,
        generated_post_id=row.generated_post_id,
        source_generation_id=row.source_generation_id,
        original_post_version_id=row.original_post_version_id,
        current_post_version_id=row.current_post_version_id,
        selected_image_id=row.selected_image_id,
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
                        session.add(
                            SavedContentItemTable(
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
                    if text_changed:
                        selected_version_id = await self._append_manual_version(
                            session,
                            context=context,
                            owner_id=owner_id,
                            edited_text=edited_text,
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
