"""Add secure saved-content deletion and retention lifecycle.

Revision ID: 20261102_0015
Revises: 20261102_0014
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261102_0015"
down_revision: str | None = "20261102_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TIMESTAMP = sa.DateTime(timezone=True)


def upgrade() -> None:
    """Create deletion staging, audit, and retryable object cleanup state."""

    op.add_column(
        "saved_content_items",
        sa.Column("deletion_due_at", TIMESTAMP, nullable=True),
    )
    # Existing soft-deleted rows enter the cleanup queue immediately instead of
    # blocking this migration or becoming permanently retained legacy data.
    op.execute(
        """
        UPDATE saved_content_items
        SET deletion_due_at = now()
        WHERE deleted_at IS NOT NULL AND deletion_due_at IS NULL
        """
    )
    op.create_check_constraint(
        "ck_saved_content_deletion_lifecycle",
        "saved_content_items",
        "(deleted_at IS NULL AND deletion_due_at IS NULL) OR "
        "(deleted_at IS NOT NULL AND deletion_due_at IS NOT NULL)",
    )
    op.create_index(
        "ix_saved_content_deletion_due",
        "saved_content_items",
        ["deletion_due_at"],
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )

    op.create_table(
        "content_deletion_audits",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("draft_id_hash", sa.CHAR(64), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("requested_at", TIMESTAMP, nullable=False),
        sa.Column("purge_after", TIMESTAMP, nullable=False),
        sa.Column("completed_at", TIMESTAMP, nullable=True),
        sa.CheckConstraint(
            "status IN ('requested', 'completed')",
            name="ck_content_deletion_audits_status",
        ),
        sa.CheckConstraint(
            "draft_id_hash ~ '^[0-9a-f]{64}$'",
            name="ck_content_deletion_audits_hash",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_content_deletion_audits_purge",
        "content_deletion_audits",
        ["status", "purge_after"],
    )

    op.create_table(
        "image_cleanup_jobs",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("generated_image_id", UUID, nullable=False, unique=True),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", TIMESTAMP, nullable=False),
        sa.Column("safe_error_code", sa.String(60), nullable=True),
        sa.Column(
            "created_at", TIMESTAMP, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("completed_at", TIMESTAMP, nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'retry', 'completed')",
            name="ck_image_cleanup_jobs_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_image_cleanup_jobs_attempts"),
        sa.ForeignKeyConstraint(
            ["generated_image_id"], ["generated_images.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_image_cleanup_jobs_due",
        "image_cleanup_jobs",
        ["status", "next_attempt_at"],
    )
    op.execute(
        """
        INSERT INTO content_deletion_audits (
            user_id, draft_id_hash, status, requested_at, purge_after
        )
        SELECT
            item.user_id,
            encode(digest(CAST(item.id AS text), 'sha256'), 'hex'),
            'requested', item.deleted_at, item.deletion_due_at
        FROM saved_content_items AS item
        WHERE item.deleted_at IS NOT NULL
        ON CONFLICT (draft_id_hash) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE generated_posts AS post
        SET status = 'deleted', deleted_at = COALESCE(post.deleted_at, now())
        WHERE EXISTS (
            SELECT 1 FROM saved_content_items AS item
            WHERE item.generated_post_id = post.id AND item.deleted_at IS NOT NULL
        )
          AND NOT EXISTS (
            SELECT 1 FROM saved_content_items AS active
            WHERE active.generated_post_id = post.id AND active.deleted_at IS NULL
        )
        """
    )
    op.execute(
        """
        WITH legacy_images AS (
            SELECT item.id AS draft_id, item.user_id, item.selected_image_id AS image_id
            FROM saved_content_items AS item
            WHERE item.deleted_at IS NOT NULL AND item.selected_image_id IS NOT NULL
            UNION
            SELECT item.id, item.user_id, history.selected_image_id
            FROM saved_content_items AS item
            JOIN saved_draft_versions AS history
              ON history.saved_draft_id = item.id
            WHERE item.deleted_at IS NOT NULL
              AND history.selected_image_id IS NOT NULL
        )
        UPDATE generated_images AS image
        SET status = 'deleted', deleted_at = COALESCE(image.deleted_at, now())
        WHERE image.id IN (SELECT image_id FROM legacy_images)
          AND NOT EXISTS (
              SELECT 1
              FROM saved_content_items AS active
              WHERE active.deleted_at IS NULL
                AND (
                    active.selected_image_id = image.id
                    OR EXISTS (
                        SELECT 1 FROM saved_draft_versions AS history
                        WHERE history.saved_draft_id = active.id
                          AND history.selected_image_id = image.id
                    )
                )
          )
        """
    )
    op.execute(
        """
        WITH legacy_images AS (
            SELECT item.user_id, item.selected_image_id AS image_id
            FROM saved_content_items AS item
            WHERE item.deleted_at IS NOT NULL AND item.selected_image_id IS NOT NULL
            UNION
            SELECT item.user_id, history.selected_image_id
            FROM saved_content_items AS item
            JOIN saved_draft_versions AS history
              ON history.saved_draft_id = item.id
            WHERE item.deleted_at IS NOT NULL
              AND history.selected_image_id IS NOT NULL
        )
        INSERT INTO image_cleanup_jobs (
            generated_image_id, user_id, storage_key, status, next_attempt_at
        )
        SELECT image.id, legacy.user_id, image.storage_key, 'pending', now()
        FROM legacy_images AS legacy
        JOIN generated_images AS image ON image.id = legacy.image_id
        WHERE image.deleted_at IS NOT NULL
        ON CONFLICT (generated_image_id) DO NOTHING
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION validate_saved_content()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            post_status varchar(20);
            image_status varchar(20);
            image_safety varchar(20);
        BEGIN
            -- Lifecycle-only updates to an already deleted item must remain
            -- possible while active saves continue to use strict validation.
            IF NEW.deleted_at IS NOT NULL THEN
                RETURN NEW;
            END IF;

            SELECT status INTO post_status
            FROM generated_posts
            WHERE id = NEW.generated_post_id;

            IF post_status = 'deleted' THEN
                RAISE EXCEPTION 'Deleted posts cannot be saved.';
            END IF;

            IF NEW.selected_image_id IS NOT NULL THEN
                SELECT status, safety_status
                INTO image_status, image_safety
                FROM generated_images
                WHERE id = NEW.selected_image_id;

                IF image_status <> 'available'
                   OR image_safety <> 'approved' THEN
                    RAISE EXCEPTION
                        'Only available and approved images can be saved.';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION validate_changed_post_hashtags()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            target_version_id uuid;
            hashtag_count integer;
            parent_status varchar(20);
        BEGIN
            target_version_id = COALESCE(NEW.post_version_id, OLD.post_version_id);

            SELECT post.status INTO parent_status
            FROM post_versions AS version
            JOIN generated_posts AS post ON post.id = version.generated_post_id
            WHERE version.id = target_version_id;

            IF parent_status IS NULL OR parent_status = 'deleted' THEN
                RETURN NULL;
            END IF;

            SELECT count(*) INTO hashtag_count
            FROM post_version_hashtags
            WHERE post_version_id = target_version_id;

            IF hashtag_count < 3 OR hashtag_count > 5 THEN
                RAISE EXCEPTION
                    'A post version must contain between three and five hashtags.';
            END IF;
            RETURN NULL;
        END;
        $function$
        """
    )


def downgrade() -> None:
    """Remove NFA-72 deletion lifecycle storage."""

    op.execute(
        """
        CREATE OR REPLACE FUNCTION validate_changed_post_hashtags()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            target_version_id uuid;
            hashtag_count integer;
        BEGIN
            target_version_id = COALESCE(NEW.post_version_id, OLD.post_version_id);

            IF NOT EXISTS (
                SELECT 1 FROM post_versions WHERE id = target_version_id
            ) THEN
                RETURN NULL;
            END IF;

            SELECT count(*) INTO hashtag_count
            FROM post_version_hashtags
            WHERE post_version_id = target_version_id;

            IF hashtag_count < 3 OR hashtag_count > 5 THEN
                RAISE EXCEPTION
                    'A post version must contain between three and five hashtags.';
            END IF;
            RETURN NULL;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION validate_saved_content()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            post_status varchar(20);
            image_status varchar(20);
            image_safety varchar(20);
        BEGIN
            SELECT status INTO post_status
            FROM generated_posts
            WHERE id = NEW.generated_post_id;

            IF post_status = 'deleted' THEN
                RAISE EXCEPTION 'Deleted posts cannot be saved.';
            END IF;

            IF NEW.selected_image_id IS NOT NULL THEN
                SELECT status, safety_status
                INTO image_status, image_safety
                FROM generated_images
                WHERE id = NEW.selected_image_id;

                IF image_status <> 'available'
                   OR image_safety <> 'approved' THEN
                    RAISE EXCEPTION
                        'Only available and approved images can be saved.';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.drop_index("ix_image_cleanup_jobs_due", table_name="image_cleanup_jobs")
    op.drop_table("image_cleanup_jobs")
    op.drop_index(
        "ix_content_deletion_audits_purge",
        table_name="content_deletion_audits",
    )
    op.drop_table("content_deletion_audits")
    op.drop_index(
        "ix_saved_content_deletion_due",
        table_name="saved_content_items",
    )
    op.drop_constraint(
        "ck_saved_content_deletion_lifecycle",
        "saved_content_items",
        type_="check",
    )
    op.drop_column("saved_content_items", "deletion_due_at")
