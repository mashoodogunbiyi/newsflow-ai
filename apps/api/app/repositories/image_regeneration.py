"""PostgreSQL generation-run persistence for image regeneration."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import and_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    GeneratedImageTable,
    GeneratedPostTable,
    GenerationRunTable,
)
from app.models.image_generation import OpenAIImageGenerationResult


class ImageRegenerationRepositoryError(RuntimeError):
    """Raised when regeneration metadata cannot be stored safely."""


class ImageRegenerationIdempotencyConflict(RuntimeError):
    """Raised when an idempotency key is reused or left incomplete."""


@dataclass(frozen=True)
class CompletedImageRegeneration:
    """Reference to a completed image found through a persistent request key."""

    image_id: UUID
    generation_run_id: UUID


class ImageRegenerationRepository(Protocol):
    """Persistence operations required by the regeneration workflow."""

    async def get_completed_by_request_key(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        request_key: str,
        request_marker: str,
    ) -> CompletedImageRegeneration | None: ...

    async def create_succeeded_run(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        request_key: str,
        request_marker: str,
        generated: OpenAIImageGenerationResult,
    ) -> UUID: ...

    async def mark_run_failed(
        self,
        *,
        generation_run_id: UUID,
        generated_post_id: UUID,
        safe_error_code: str,
    ) -> None: ...


class SqlAlchemyImageRegenerationRepository:
    """Create image generation runs and resolve durable idempotent replays."""

    def __init__(
        self,
        database: SqlAlchemyDatabase,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._database = database
        self._clock = clock or (lambda: datetime.now(UTC))

    async def get_completed_by_request_key(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        request_key: str,
        request_marker: str,
    ) -> CompletedImageRegeneration | None:
        statement = (
            select(
                GenerationRunTable.id.label("generation_run_id"),
                GenerationRunTable.status,
                GenerationRunTable.prompt_text,
                GeneratedImageTable.id.label("image_id"),
            )
            .join(
                GeneratedPostTable,
                GeneratedPostTable.id == GenerationRunTable.generated_post_id,
            )
            .outerjoin(
                GeneratedImageTable,
                and_(
                    GeneratedImageTable.generation_run_id == GenerationRunTable.id,
                    GeneratedImageTable.deleted_at.is_(None),
                    GeneratedImageTable.status == "available",
                ),
            )
            .where(
                GenerationRunTable.generated_post_id == generated_post_id,
                GenerationRunTable.generation_type == "image",
                GenerationRunTable.idempotency_key == request_key,
                GeneratedPostTable.user_id == owner_id,
                GeneratedPostTable.deleted_at.is_(None),
                GeneratedPostTable.status != "deleted",
            )
        )
        try:
            async with self._database.session() as session:
                row = (await session.execute(statement)).one_or_none()
        except SQLAlchemyError as exc:
            raise ImageRegenerationRepositoryError(
                "The image regeneration request could not be checked."
            ) from exc
        if row is None:
            return None
        if row.prompt_text != request_marker:
            raise ImageRegenerationIdempotencyConflict(
                "The idempotency key has already been used for another request."
            )
        if row.status != "succeeded" or row.image_id is None:
            raise ImageRegenerationIdempotencyConflict(
                "The idempotency key belongs to an incomplete request."
            )
        return CompletedImageRegeneration(
            image_id=row.image_id,
            generation_run_id=row.generation_run_id,
        )

    async def create_succeeded_run(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        request_key: str,
        request_marker: str,
        generated: OpenAIImageGenerationResult,
    ) -> UUID:
        generation_run_id = uuid4()
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Regeneration timestamps must include a timezone.")
        try:
            async with self._database.session() as session:
                async with session.begin():
                    owned_post = (
                        await session.execute(
                            select(GeneratedPostTable.id).where(
                                GeneratedPostTable.id == generated_post_id,
                                GeneratedPostTable.user_id == owner_id,
                                GeneratedPostTable.deleted_at.is_(None),
                                GeneratedPostTable.status != "deleted",
                            )
                        )
                    ).scalar_one_or_none()
                    if owned_post is None:
                        raise ImageRegenerationRepositoryError(
                            "The image regeneration context is unavailable."
                        )
                    session.add(
                        GenerationRunTable(
                            id=generation_run_id,
                            generated_post_id=generated_post_id,
                            article_rights_version_id=generated.rights_version_id,
                            generation_type="image",
                            status="succeeded",
                            idempotency_key=request_key,
                            provider=generated.provider,
                            model=generated.model_identifier,
                            prompt_template_version=generated.prompt_version,
                            prompt_text=request_marker,
                            provider_request_id=generated.provider_request_id,
                            attempt_count=1,
                            input_tokens=generated.usage_metadata.input_tokens,
                            output_tokens=generated.usage_metadata.output_tokens,
                            started_at=now,
                            completed_at=now,
                        )
                    )
        except ImageRegenerationRepositoryError:
            raise
        except IntegrityError as exc:
            raise ImageRegenerationIdempotencyConflict(
                "The idempotency key has already been used."
            ) from exc
        except SQLAlchemyError as exc:
            raise ImageRegenerationRepositoryError(
                "The image generation attempt could not be stored."
            ) from exc
        return generation_run_id

    async def mark_run_failed(
        self,
        *,
        generation_run_id: UUID,
        generated_post_id: UUID,
        safe_error_code: str,
    ) -> None:
        """Prevent a storage failure from leaving a false successful run."""

        try:
            async with self._database.session() as session:
                async with session.begin():
                    await session.execute(
                        update(GenerationRunTable)
                        .where(
                            GenerationRunTable.id == generation_run_id,
                            GenerationRunTable.generated_post_id == generated_post_id,
                        )
                        .values(
                            status="failed",
                            safe_error_code=safe_error_code[:100],
                            completed_at=self._clock(),
                        )
                    )
        except SQLAlchemyError as exc:
            raise ImageRegenerationRepositoryError(
                "The failed image generation attempt could not be recorded."
            ) from exc
