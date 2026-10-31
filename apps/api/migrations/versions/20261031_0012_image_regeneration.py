"""Add generated-image version relationships for regeneration.

Revision ID: 20261031_0012
Revises: 20261031_0011
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261031_0012"
down_revision: str | None = "20261031_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Record an immutable parent and ordered version for every image."""

    op.add_column(
        "generated_images",
        sa.Column("parent_image_id", UUID, nullable=True),
    )
    op.add_column(
        "generated_images",
        sa.Column("regeneration_sequence", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        WITH numbered AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY generated_post_id
                       ORDER BY created_at, id
                   ) - 1 AS sequence_number
            FROM generated_images
        )
        UPDATE generated_images AS image
        SET regeneration_sequence = numbered.sequence_number
        FROM numbered
        WHERE numbered.id = image.id
        """
    )
    op.alter_column(
        "generated_images",
        "regeneration_sequence",
        nullable=False,
    )
    op.create_foreign_key(
        "fk_generated_images_parent_version",
        "generated_images",
        "generated_images",
        ["parent_image_id", "generated_post_id"],
        ["id", "generated_post_id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_generated_images_post_sequence",
        "generated_images",
        ["generated_post_id", "regeneration_sequence"],
    )
    op.create_check_constraint(
        "ck_generated_images_regeneration_sequence",
        "generated_images",
        "regeneration_sequence >= 0",
    )
    op.create_check_constraint(
        "ck_generated_images_parent_not_self",
        "generated_images",
        "parent_image_id IS NULL OR parent_image_id <> id",
    )
    op.create_index(
        "ix_generated_images_parent_created",
        "generated_images",
        ["parent_image_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("parent_image_id IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Remove NFA-52 generated-image version relationships."""

    op.drop_index(
        "ix_generated_images_parent_created",
        table_name="generated_images",
    )
    op.drop_constraint(
        "ck_generated_images_parent_not_self",
        "generated_images",
        type_="check",
    )
    op.drop_constraint(
        "ck_generated_images_regeneration_sequence",
        "generated_images",
        type_="check",
    )
    op.drop_constraint(
        "uq_generated_images_post_sequence",
        "generated_images",
        type_="unique",
    )
    op.drop_constraint(
        "fk_generated_images_parent_version",
        "generated_images",
        type_="foreignkey",
    )
    op.drop_column("generated_images", "regeneration_sequence")
    op.drop_column("generated_images", "parent_image_id")
