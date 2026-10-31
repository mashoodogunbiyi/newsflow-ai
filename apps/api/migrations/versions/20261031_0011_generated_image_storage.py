"""Add secure generated-image ownership and provenance metadata.

Revision ID: 20261031_0011
Revises: 20261030_0010
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261031_0011"
down_revision: str | None = "20261030_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Persist validated ownership, integrity, safety, and model metadata."""

    op.create_unique_constraint(
        "uq_generated_posts_id_article_snapshot",
        "generated_posts",
        ["id", "article_snapshot_id"],
    )
    op.add_column("generated_images", sa.Column("request_id", UUID, nullable=True))
    op.add_column("generated_images", sa.Column("user_id", UUID, nullable=True))
    op.add_column("generated_images", sa.Column("article_id", UUID, nullable=True))
    op.add_column(
        "generated_images",
        sa.Column("article_snapshot_id", UUID, nullable=True),
    )
    op.add_column(
        "generated_images",
        sa.Column("content_sha256", sa.CHAR(length=64), nullable=True),
    )
    op.add_column(
        "generated_images",
        sa.Column("model_identifier", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "generated_images",
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "generated_images",
        sa.Column("safety_policy_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "generated_images",
        sa.Column(
            "validation_status",
            sa.String(length=20),
            server_default=sa.text("'passed'"),
            nullable=False,
        ),
    )
    op.add_column(
        "generated_images",
        sa.Column(
            "generation_status",
            sa.String(length=20),
            server_default=sa.text("'completed'"),
            nullable=False,
        ),
    )
    op.add_column(
        "generated_images",
        sa.Column(
            "ai_generated",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE generated_images AS image
        SET request_id = image.generation_run_id,
            user_id = post.user_id,
            article_snapshot_id = post.article_snapshot_id,
            article_id = snapshot.article_id,
            content_sha256 = encode(digest(image.storage_key, 'sha256'), 'hex'),
            model_identifier = run.model,
            prompt_version = run.prompt_template_version,
            safety_policy_version = 'legacy_unrecorded'
        FROM generated_posts AS post
        JOIN article_snapshots AS snapshot
          ON snapshot.id = post.article_snapshot_id
        JOIN generation_runs AS run
          ON run.generated_post_id = post.id
        WHERE image.generated_post_id = post.id
          AND image.generation_run_id = run.id
        """
    )
    for column_name in (
        "request_id",
        "user_id",
        "article_id",
        "article_snapshot_id",
        "content_sha256",
        "model_identifier",
        "prompt_version",
        "safety_policy_version",
    ):
        op.alter_column("generated_images", column_name, nullable=False)

    op.create_foreign_key(
        "fk_generated_images_user",
        "generated_images",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_generated_images_article",
        "generated_images",
        "articles",
        ["article_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_generated_images_owned_post",
        "generated_images",
        "generated_posts",
        ["generated_post_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_generated_images_post_snapshot",
        "generated_images",
        "generated_posts",
        ["generated_post_id", "article_snapshot_id"],
        ["id", "article_snapshot_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_generated_images_article_snapshot",
        "generated_images",
        "article_snapshots",
        ["article_snapshot_id", "article_id"],
        ["id", "article_id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_generated_images_request_id",
        "generated_images",
        ["request_id"],
    )
    op.create_check_constraint(
        "ck_generated_images_content_sha256",
        "generated_images",
        "content_sha256 ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_generated_images_validation_status",
        "generated_images",
        "validation_status = 'passed'",
    )
    op.create_check_constraint(
        "ck_generated_images_generation_status",
        "generated_images",
        "generation_status = 'completed'",
    )
    op.create_check_constraint(
        "ck_generated_images_ai_generated",
        "generated_images",
        "ai_generated AND ai_disclosure_required",
    )
    op.create_check_constraint(
        "ck_generated_images_provenance_values",
        "generated_images",
        "length(btrim(model_identifier)) > 0 "
        "AND length(btrim(prompt_version)) > 0 "
        "AND length(btrim(safety_policy_version)) > 0",
    )
    op.create_index(
        "ix_generated_images_owner_created",
        "generated_images",
        ["user_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_generated_images_article_created",
        "generated_images",
        ["article_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Remove NFA-51 generated-image metadata and integrity controls."""

    op.drop_index("ix_generated_images_article_created", table_name="generated_images")
    op.drop_index("ix_generated_images_owner_created", table_name="generated_images")
    op.drop_constraint(
        "ck_generated_images_provenance_values",
        "generated_images",
        type_="check",
    )
    op.drop_constraint(
        "ck_generated_images_ai_generated",
        "generated_images",
        type_="check",
    )
    op.drop_constraint(
        "ck_generated_images_generation_status",
        "generated_images",
        type_="check",
    )
    op.drop_constraint(
        "ck_generated_images_validation_status",
        "generated_images",
        type_="check",
    )
    op.drop_constraint(
        "ck_generated_images_content_sha256",
        "generated_images",
        type_="check",
    )
    op.drop_constraint(
        "uq_generated_images_request_id",
        "generated_images",
        type_="unique",
    )
    for constraint_name in (
        "fk_generated_images_article_snapshot",
        "fk_generated_images_post_snapshot",
        "fk_generated_images_owned_post",
        "fk_generated_images_article",
        "fk_generated_images_user",
    ):
        op.drop_constraint(
            constraint_name,
            "generated_images",
            type_="foreignkey",
        )
    for column_name in (
        "ai_generated",
        "generation_status",
        "validation_status",
        "safety_policy_version",
        "prompt_version",
        "model_identifier",
        "content_sha256",
        "article_snapshot_id",
        "article_id",
        "user_id",
        "request_id",
    ):
        op.drop_column("generated_images", column_name)
    op.drop_constraint(
        "uq_generated_posts_id_article_snapshot",
        "generated_posts",
        type_="unique",
    )
