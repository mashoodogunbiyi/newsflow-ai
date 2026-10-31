"""PostgreSQL persistence for private generated-image metadata."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    ArticleSnapshotTable,
    GeneratedImageTable,
    GeneratedPostTable,
    GenerationRunTable,
    PostVersionTable,
)
from app.models.generated_image import (
    GeneratedImagePersistenceResult,
    GeneratedImageWrite,
    StoredGeneratedImageRecord,
)


class GeneratedImageRepositoryError(RuntimeError):
    """Raised when image metadata cannot be persisted safely."""


class GeneratedImageContextNotFoundError(RuntimeError):
    """Raised when ownership or generation relationships do not match."""


class GeneratedImageIdempotencyConflict(RuntimeError):
    """Raised when one request ID is reused for different image content."""


class GeneratedImageRepository(Protocol):
    """Persistence operations used by the image-storage workflow."""

    async def get_by_request_id(
        self,
        *,
        request_id: UUID,
    ) -> StoredGeneratedImageRecord | None: ...

    async def save(
        self,
        image: GeneratedImageWrite,
    ) -> GeneratedImagePersistenceResult: ...


class SqlAlchemyGeneratedImageRepository:
    """Persist metadata after verifying ownership and relational context."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def get_by_request_id(
        self,
        *,
        request_id: UUID,
    ) -> StoredGeneratedImageRecord | None:
        try:
            async with self._database.session() as session:
                return await self._get_by_request_id(session, request_id=request_id)
        except SQLAlchemyError as exc:
            raise GeneratedImageRepositoryError(
                "Generated image metadata could not be read."
            ) from exc

    async def save(
        self,
        image: GeneratedImageWrite,
    ) -> GeneratedImagePersistenceResult:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    await session.execute(
                        select(
                            func.pg_advisory_xact_lock(
                                func.hashtextextended(str(image.request_id), 0)
                            )
                        )
                    )
                    existing = await self._get_by_request_id(
                        session,
                        request_id=image.request_id,
                    )
                    if existing is not None:
                        self._require_same_request(existing, image)
                        return GeneratedImagePersistenceResult(
                            record=existing,
                            created=False,
                        )

                    article_snapshot_id = await self._resolve_context(session, image)
                    row = GeneratedImageTable(
                        id=image.id,
                        request_id=image.request_id,
                        user_id=image.owner_id,
                        article_id=image.article_id,
                        article_snapshot_id=article_snapshot_id,
                        generated_post_id=image.generated_post_id,
                        source_post_version_id=image.source_post_version_id,
                        generation_run_id=image.generation_run_id,
                        storage_provider=image.storage_provider,
                        storage_key=image.storage_key.get_secret_value(),
                        mime_type=image.mime_type,
                        byte_size=image.file_size_bytes,
                        width_px=image.width,
                        height_px=image.height,
                        content_sha256=image.content_sha256,
                        model_identifier=image.model_identifier,
                        prompt_version=image.prompt_version,
                        safety_policy_version=image.safety_policy_version,
                        safety_status=image.safety_status.value,
                        validation_status=image.validation_status.value,
                        generation_status=image.generation_status,
                        ai_generated=image.ai_generated,
                        ai_disclosure_required=image.ai_disclosure_required,
                        status="available",
                        created_at=image.created_at,
                        deleted_at=None,
                    )
                    session.add(row)
                    await session.flush()
                    record = StoredGeneratedImageRecord(
                        **image.model_dump(),
                        article_snapshot_id=article_snapshot_id,
                    )
                    return GeneratedImagePersistenceResult(
                        record=record,
                        created=True,
                    )
        except (
            GeneratedImageContextNotFoundError,
            GeneratedImageIdempotencyConflict,
        ):
            raise
        except SQLAlchemyError as exc:
            raise GeneratedImageRepositoryError(
                "Generated image metadata could not be stored."
            ) from exc

    @staticmethod
    async def _resolve_context(
        session: AsyncSession,
        image: GeneratedImageWrite,
    ) -> UUID:
        statement = (
            select(GeneratedPostTable.article_snapshot_id)
            .join(
                ArticleSnapshotTable,
                ArticleSnapshotTable.id == GeneratedPostTable.article_snapshot_id,
            )
            .join(
                GenerationRunTable,
                and_(
                    GenerationRunTable.id == image.generation_run_id,
                    GenerationRunTable.generated_post_id == GeneratedPostTable.id,
                ),
            )
            .where(
                GeneratedPostTable.id == image.generated_post_id,
                GeneratedPostTable.user_id == image.owner_id,
                GeneratedPostTable.deleted_at.is_(None),
                GeneratedPostTable.status != "deleted",
                ArticleSnapshotTable.article_id == image.article_id,
                GenerationRunTable.generation_type == "image",
                GenerationRunTable.status == "succeeded",
            )
        )
        if image.source_post_version_id is not None:
            statement = statement.join(
                PostVersionTable,
                and_(
                    PostVersionTable.id == image.source_post_version_id,
                    PostVersionTable.generated_post_id == GeneratedPostTable.id,
                ),
            )
        article_snapshot_id = (await session.execute(statement)).scalar_one_or_none()
        if article_snapshot_id is None:
            raise GeneratedImageContextNotFoundError(
                "The image ownership or generation context is not valid."
            )
        return article_snapshot_id

    @staticmethod
    async def _get_by_request_id(
        session: AsyncSession,
        *,
        request_id: UUID,
    ) -> StoredGeneratedImageRecord | None:
        row = (
            await session.execute(
                SqlAlchemyGeneratedImageRepository._record_statement().where(
                    GeneratedImageTable.request_id == request_id,
                    GeneratedImageTable.deleted_at.is_(None),
                    GeneratedImageTable.status == "available",
                )
            )
        ).one_or_none()
        if row is None:
            return None
        return StoredGeneratedImageRecord.model_validate(
            {
                "id": row.id,
                "request_id": row.request_id,
                "owner_id": row.user_id,
                "article_id": row.article_id,
                "article_snapshot_id": row.article_snapshot_id,
                "generated_post_id": row.generated_post_id,
                "source_post_version_id": row.source_post_version_id,
                "generation_run_id": row.generation_run_id,
                "storage_provider": row.storage_provider,
                "storage_key": row.storage_key,
                "mime_type": row.mime_type,
                "file_size_bytes": row.byte_size,
                "width": row.width_px,
                "height": row.height_px,
                "content_sha256": row.content_sha256,
                "model_identifier": row.model_identifier,
                "prompt_version": row.prompt_version,
                "safety_policy_version": row.safety_policy_version,
                "safety_status": row.safety_status,
                "validation_status": row.validation_status,
                "generation_status": row.generation_status,
                "ai_generated": row.ai_generated,
                "ai_disclosure_required": row.ai_disclosure_required,
                "created_at": row.created_at,
            }
        )

    @staticmethod
    def _record_statement():
        return select(
            GeneratedImageTable.id,
            GeneratedImageTable.request_id,
            GeneratedImageTable.user_id,
            GeneratedImageTable.article_id,
            GeneratedImageTable.article_snapshot_id,
            GeneratedImageTable.generated_post_id,
            GeneratedImageTable.source_post_version_id,
            GeneratedImageTable.generation_run_id,
            GeneratedImageTable.storage_provider,
            GeneratedImageTable.storage_key,
            GeneratedImageTable.mime_type,
            GeneratedImageTable.byte_size,
            GeneratedImageTable.width_px,
            GeneratedImageTable.height_px,
            GeneratedImageTable.content_sha256,
            GeneratedImageTable.model_identifier,
            GeneratedImageTable.prompt_version,
            GeneratedImageTable.safety_policy_version,
            GeneratedImageTable.safety_status,
            GeneratedImageTable.validation_status,
            GeneratedImageTable.generation_status,
            GeneratedImageTable.ai_generated,
            GeneratedImageTable.ai_disclosure_required,
            GeneratedImageTable.created_at,
        )

    @staticmethod
    def _require_same_request(
        existing: StoredGeneratedImageRecord,
        image: GeneratedImageWrite,
    ) -> None:
        matching = (
            existing.owner_id == image.owner_id
            and existing.article_id == image.article_id
            and existing.generated_post_id == image.generated_post_id
            and existing.generation_run_id == image.generation_run_id
            and existing.source_post_version_id == image.source_post_version_id
            and existing.content_sha256 == image.content_sha256
        )
        if not matching:
            raise GeneratedImageIdempotencyConflict(
                "The image request identifier has already been used."
            )
