"""Transactional deletion, object-cleanup, and retention persistence."""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database.sqlalchemy import SqlAlchemyDatabase


class ContentDeletionRepositoryError(RuntimeError):
    """Raised without exposing database details or private content."""


@dataclass(frozen=True)
class ImageCleanupTask:
    """One private object that is no longer referenced by active content."""

    job_id: UUID
    image_id: UUID
    storage_key: str


@dataclass(frozen=True)
class DeletionRequest:
    """Successful owner-authorised soft deletion and queued object work."""

    draft_id: UUID
    cleanup_tasks: list[ImageCleanupTask]


class ContentDeletionRepository(Protocol):
    """Persistence boundary for deletion and retention operations."""

    async def request_for_owner(
        self,
        *,
        owner_id: UUID,
        draft_id: UUID,
        requested_at: datetime,
        purge_after: datetime,
    ) -> DeletionRequest | None: ...

    async def complete_image_cleanup(
        self, *, job_id: UUID, completed_at: datetime
    ) -> None: ...

    async def retry_image_cleanup(
        self, *, job_id: UUID, retry_at: datetime
    ) -> None: ...

    async def claim_due_image_cleanup(
        self, *, now: datetime, limit: int
    ) -> list[ImageCleanupTask]: ...

    async def purge_due_content(
        self,
        *,
        now: datetime,
        audit_expiry: datetime,
        limit: int,
    ) -> int: ...


class SqlAlchemyContentDeletionRepository:
    """PostgreSQL implementation with owner checks and content-free evidence."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def request_for_owner(
        self,
        *,
        owner_id: UUID,
        draft_id: UUID,
        requested_at: datetime,
        purge_after: datetime,
    ) -> DeletionRequest | None:
        try:
            async with self._database.session() as session, session.begin():
                row = (
                    (
                        await session.execute(
                            text(
                                """
                            SELECT id, generated_post_id
                            FROM saved_content_items
                            WHERE id = :draft_id
                              AND user_id = :owner_id
                              AND deleted_at IS NULL
                            FOR UPDATE
                            """
                            ),
                            {"draft_id": draft_id, "owner_id": owner_id},
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None:
                    return None

                image_rows = (
                    (
                        await session.execute(
                            text(
                                """
                            SELECT DISTINCT image.id, image.storage_key
                            FROM generated_images AS image
                            WHERE image.user_id = :owner_id
                              AND image.deleted_at IS NULL
                              AND image.id IN (
                                  SELECT selected_image_id
                                  FROM saved_content_items
                                  WHERE id = :draft_id
                                    AND selected_image_id IS NOT NULL
                                  UNION
                                  SELECT selected_image_id
                                  FROM saved_draft_versions
                                  WHERE saved_draft_id = :draft_id
                                    AND selected_image_id IS NOT NULL
                              )
                              AND NOT EXISTS (
                                  SELECT 1
                                  FROM saved_content_items AS active
                                  WHERE active.id <> :draft_id
                                    AND active.deleted_at IS NULL
                                    AND (
                                        active.selected_image_id = image.id
                                        OR EXISTS (
                                            SELECT 1
                                            FROM saved_draft_versions AS history
                                            WHERE history.saved_draft_id = active.id
                                              AND history.selected_image_id = image.id
                                        )
                                    )
                              )
                            """
                            ),
                            {"draft_id": draft_id, "owner_id": owner_id},
                        )
                    )
                    .mappings()
                    .all()
                )

                await session.execute(
                    text(
                        """
                        UPDATE saved_content_items
                        SET deleted_at = :requested_at,
                            deletion_due_at = :purge_after,
                            updated_at = :requested_at
                        WHERE id = :draft_id
                        """
                    ),
                    {
                        "draft_id": draft_id,
                        "requested_at": requested_at,
                        "purge_after": purge_after,
                    },
                )
                await session.execute(
                    text(
                        """
                        UPDATE generated_posts
                        SET status = 'deleted',
                            deleted_at = :requested_at,
                            updated_at = :requested_at
                        WHERE id = :post_id
                          AND NOT EXISTS (
                              SELECT 1 FROM saved_content_items
                              WHERE generated_post_id = :post_id
                                AND deleted_at IS NULL
                          )
                        """
                    ),
                    {"post_id": row["generated_post_id"], "requested_at": requested_at},
                )

                tasks: list[ImageCleanupTask] = []
                for image in image_rows:
                    await session.execute(
                        text(
                            """
                            UPDATE generated_images
                            SET status = 'deleted', deleted_at = :requested_at
                            WHERE id = :image_id
                            """
                        ),
                        {"image_id": image["id"], "requested_at": requested_at},
                    )
                    job = (
                        await session.execute(
                            text(
                                """
                                INSERT INTO image_cleanup_jobs (
                                    generated_image_id, user_id, storage_key,
                                    status, next_attempt_at
                                ) VALUES (
                                    :image_id, :owner_id, :storage_key,
                                    'pending', :requested_at
                                )
                                ON CONFLICT (generated_image_id) DO UPDATE
                                SET next_attempt_at = EXCLUDED.next_attempt_at
                                RETURNING id
                                """
                            ),
                            {
                                "image_id": image["id"],
                                "owner_id": owner_id,
                                "storage_key": image["storage_key"],
                                "requested_at": requested_at,
                            },
                        )
                    ).scalar_one()
                    tasks.append(
                        ImageCleanupTask(
                            job_id=job,
                            image_id=image["id"],
                            storage_key=image["storage_key"],
                        )
                    )

                await session.execute(
                    text(
                        """
                        INSERT INTO content_deletion_audits (
                            user_id, draft_id_hash, status,
                            requested_at, purge_after
                        ) VALUES (
                            :owner_id, :draft_hash, 'requested',
                            :requested_at, :purge_after
                        )
                        """
                    ),
                    {
                        "owner_id": owner_id,
                        "draft_hash": hashlib.sha256(
                            str(draft_id).encode()
                        ).hexdigest(),
                        "requested_at": requested_at,
                        "purge_after": purge_after,
                    },
                )
                return DeletionRequest(draft_id=draft_id, cleanup_tasks=tasks)
        except SQLAlchemyError as exc:
            raise ContentDeletionRepositoryError(
                "Content deletion could not be recorded."
            ) from exc

    async def complete_image_cleanup(
        self, *, job_id: UUID, completed_at: datetime
    ) -> None:
        await self._update_cleanup(
            job_id=job_id,
            status="completed",
            next_attempt_at=completed_at,
            completed_at=completed_at,
            error_code=None,
        )

    async def retry_image_cleanup(self, *, job_id: UUID, retry_at: datetime) -> None:
        await self._update_cleanup(
            job_id=job_id,
            status="retry",
            next_attempt_at=retry_at,
            completed_at=None,
            error_code="private_object_cleanup_failed",
        )

    async def _update_cleanup(
        self,
        *,
        job_id: UUID,
        status: str,
        next_attempt_at: datetime,
        completed_at: datetime | None,
        error_code: str | None,
    ) -> None:
        try:
            async with self._database.session() as session, session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE image_cleanup_jobs
                        SET status = :status,
                            attempts = attempts + 1,
                            next_attempt_at = :next_attempt_at,
                            completed_at = :completed_at,
                            safe_error_code = :error_code
                        WHERE id = :job_id
                        """
                    ),
                    {
                        "job_id": job_id,
                        "status": status,
                        "next_attempt_at": next_attempt_at,
                        "completed_at": completed_at,
                        "error_code": error_code,
                    },
                )
        except SQLAlchemyError as exc:
            raise ContentDeletionRepositoryError(
                "Image cleanup state could not be updated."
            ) from exc

    async def claim_due_image_cleanup(
        self, *, now: datetime, limit: int
    ) -> list[ImageCleanupTask]:
        try:
            async with self._database.session() as session, session.begin():
                rows = (
                    (
                        await session.execute(
                            text(
                                """
                            SELECT id, generated_image_id, storage_key
                            FROM image_cleanup_jobs
                            WHERE status IN ('pending', 'processing', 'retry')
                              AND next_attempt_at <= :now
                            ORDER BY next_attempt_at, id
                            LIMIT :limit
                            FOR UPDATE SKIP LOCKED
                            """
                            ),
                            {"now": now, "limit": limit},
                        )
                    )
                    .mappings()
                    .all()
                )
                if rows:
                    await session.execute(
                        text(
                            """
                            UPDATE image_cleanup_jobs
                            SET status = 'processing',
                                next_attempt_at = :lease_until
                            WHERE id = ANY(:job_ids)
                            """
                        ),
                        {
                            "job_ids": [row["id"] for row in rows],
                            "lease_until": now + timedelta(minutes=15),
                        },
                    )
                return [
                    ImageCleanupTask(
                        job_id=row["id"],
                        image_id=row["generated_image_id"],
                        storage_key=row["storage_key"],
                    )
                    for row in rows
                ]
        except SQLAlchemyError as exc:
            raise ContentDeletionRepositoryError(
                "Image cleanup work could not be claimed."
            ) from exc

    async def purge_due_content(
        self,
        *,
        now: datetime,
        audit_expiry: datetime,
        limit: int,
    ) -> int:
        try:
            async with self._database.session() as session, session.begin():
                drafts = (
                    (
                        await session.execute(
                            text(
                                """
                            SELECT item.id, item.generated_post_id
                            FROM saved_content_items AS item
                            WHERE item.deleted_at IS NOT NULL
                              AND item.deletion_due_at <= :now
                              AND NOT EXISTS (
                                  SELECT 1
                                  FROM image_cleanup_jobs AS job
                                  JOIN generated_images AS image
                                    ON image.id = job.generated_image_id
                                  WHERE image.generated_post_id = item.generated_post_id
                                    AND job.status <> 'completed'
                              )
                            ORDER BY item.deletion_due_at, item.id
                            LIMIT :limit
                            FOR UPDATE SKIP LOCKED
                            """
                            ),
                            {"now": now, "limit": limit},
                        )
                    )
                    .mappings()
                    .all()
                )
                for draft in drafts:
                    await session.execute(
                        text(
                            """
                            DELETE FROM post_claim_sources
                            WHERE post_claim_id IN (
                                SELECT claim.id
                                FROM post_claims AS claim
                                JOIN post_versions AS version
                                  ON version.id = claim.post_version_id
                                WHERE version.generated_post_id = :post_id
                            )
                            """
                        ),
                        {"post_id": draft["generated_post_id"]},
                    )
                    await session.execute(
                        text(
                            """
                            DELETE FROM post_claims
                            WHERE post_version_id IN (
                                SELECT id FROM post_versions
                                WHERE generated_post_id = :post_id
                            )
                            """
                        ),
                        {"post_id": draft["generated_post_id"]},
                    )
                    await session.execute(
                        text(
                            """
                            DELETE FROM generation_facts
                            WHERE generation_run_id IN (
                                SELECT id FROM generation_runs
                                WHERE generated_post_id = :post_id
                            )
                            """
                        ),
                        {"post_id": draft["generated_post_id"]},
                    )
                    await session.execute(
                        text(
                            "DELETE FROM saved_draft_versions "
                            "WHERE saved_draft_id = :draft_id"
                        ),
                        {"draft_id": draft["id"]},
                    )
                    await session.execute(
                        text(
                            """
                            DELETE FROM post_version_hashtags
                            WHERE post_version_id IN (
                                SELECT id FROM post_versions
                                WHERE generated_post_id = :post_id
                            )
                            """
                        ),
                        {"post_id": draft["generated_post_id"]},
                    )
                    await session.execute(
                        text(
                            """
                            UPDATE post_versions
                            SET hook = '[deleted]', summary = '[deleted]',
                                insight = NULL, call_to_action = NULL,
                                rendered_text = '[deleted]',
                                source_attribution = 'Deleted content',
                                word_count = 0
                            WHERE generated_post_id = :post_id
                            """
                        ),
                        {"post_id": draft["generated_post_id"]},
                    )
                    await session.execute(
                        text(
                            """
                            UPDATE generation_runs
                            SET prompt_text = '[deleted]'
                            WHERE generated_post_id = :post_id
                            """
                        ),
                        {"post_id": draft["generated_post_id"]},
                    )
                    await session.execute(
                        text(
                            """
                            UPDATE generated_images
                            SET alt_text = NULL,
                                storage_key = 'deleted/' || id::text,
                                content_sha256 = repeat('0', 64),
                                byte_size = 1
                            WHERE generated_post_id = :post_id
                              AND deleted_at IS NOT NULL
                            """
                        ),
                        {"post_id": draft["generated_post_id"]},
                    )
                    await session.execute(
                        text(
                            """
                            UPDATE image_cleanup_jobs AS job
                            SET storage_key = 'deleted/' || job.generated_image_id::text
                            FROM generated_images AS image
                            WHERE image.id = job.generated_image_id
                              AND image.generated_post_id = :post_id
                              AND job.status = 'completed'
                            """
                        ),
                        {"post_id": draft["generated_post_id"]},
                    )
                    await session.execute(
                        text(
                            """
                            DELETE FROM saved_content_items
                            WHERE id = :draft_id
                            """
                        ),
                        {"draft_id": draft["id"]},
                    )
                    await session.execute(
                        text(
                            """
                            UPDATE content_deletion_audits
                            SET status = 'completed', completed_at = :now
                            WHERE draft_id_hash = :draft_hash
                            """
                        ),
                        {
                            "draft_hash": hashlib.sha256(
                                str(draft["id"]).encode()
                            ).hexdigest(),
                            "now": now,
                        },
                    )
                await session.execute(
                    text(
                        """
                        DELETE FROM image_cleanup_jobs
                        WHERE status = 'completed' AND completed_at < :audit_expiry
                        """
                    ),
                    {"audit_expiry": audit_expiry},
                )
                await session.execute(
                    text(
                        """
                        DELETE FROM content_deletion_audits
                        WHERE status = 'completed' AND completed_at < :audit_expiry
                        """
                    ),
                    {"audit_expiry": audit_expiry},
                )
                return len(drafts)
        except SQLAlchemyError as exc:
            raise ContentDeletionRepositoryError(
                "Expired content could not be purged."
            ) from exc
