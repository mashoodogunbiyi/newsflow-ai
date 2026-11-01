"""Add versioned and idempotent saved-draft persistence.

Revision ID: 20261101_0013
Revises: 20261031_0012
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261101_0013"
down_revision: str | None = "20261031_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Preserve the source generation and protect draft saves from conflicts."""

    op.add_column(
        "saved_content_items",
        sa.Column("source_generation_id", UUID, nullable=True),
    )
    op.add_column(
        "saved_content_items",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "saved_content_items",
        sa.Column("save_key_hash", sa.CHAR(length=64), nullable=True),
    )
    op.add_column(
        "saved_content_items",
        sa.Column("save_payload_hash", sa.CHAR(length=64), nullable=True),
    )
    op.execute(
        """
        UPDATE saved_content_items AS item
        SET source_generation_id = COALESCE(
            selected_version.generation_run_id,
            (
                SELECT run.id
                FROM generation_runs AS run
                WHERE run.generated_post_id = item.generated_post_id
                  AND run.generation_type = 'post'
                  AND run.status = 'succeeded'
                ORDER BY run.created_at, run.id
                LIMIT 1
            )
        )
        FROM post_versions AS selected_version
        WHERE selected_version.id = item.selected_post_version_id
        """
    )
    op.alter_column(
        "saved_content_items",
        "source_generation_id",
        nullable=False,
    )
    op.create_foreign_key(
        "fk_saved_content_source_generation",
        "saved_content_items",
        "generation_runs",
        ["source_generation_id", "generated_post_id"],
        ["id", "generated_post_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_saved_content_version",
        "saved_content_items",
        "version > 0",
    )
    op.create_check_constraint(
        "ck_saved_content_save_hashes",
        "saved_content_items",
        "(save_key_hash IS NULL AND save_payload_hash IS NULL) OR "
        "(save_key_hash ~ '^[0-9a-f]{64}$' AND "
        "save_payload_hash ~ '^[0-9a-f]{64}$')",
    )
    op.create_index(
        "uq_saved_content_owner_save_key",
        "saved_content_items",
        ["user_id", "save_key_hash"],
        unique=True,
        postgresql_where=sa.text("save_key_hash IS NOT NULL"),
    )
    op.create_index(
        "ix_saved_content_source_generation",
        "saved_content_items",
        ["source_generation_id"],
    )


def downgrade() -> None:
    """Remove NFA-67 saved-draft concurrency and idempotency evidence."""

    op.drop_index(
        "ix_saved_content_source_generation",
        table_name="saved_content_items",
    )
    op.drop_index(
        "uq_saved_content_owner_save_key",
        table_name="saved_content_items",
    )
    op.drop_constraint(
        "ck_saved_content_save_hashes",
        "saved_content_items",
        type_="check",
    )
    op.drop_constraint(
        "ck_saved_content_version",
        "saved_content_items",
        type_="check",
    )
    op.drop_constraint(
        "fk_saved_content_source_generation",
        "saved_content_items",
        type_="foreignkey",
    )
    for column_name in (
        "save_payload_hash",
        "save_key_hash",
        "version",
        "source_generation_id",
    ):
        op.drop_column("saved_content_items", column_name)
