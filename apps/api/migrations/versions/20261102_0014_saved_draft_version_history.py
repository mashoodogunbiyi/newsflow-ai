"""Add immutable saved-draft version history.

Revision ID: 20261102_0014
Revises: 20261101_0013
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261102_0014"
down_revision: str | None = "20261101_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TIMESTAMP = sa.DateTime(timezone=True)


def upgrade() -> None:
    """Create the owner-bound, append-only version ledger."""

    op.create_unique_constraint(
        "uq_saved_content_id_owner_post",
        "saved_content_items",
        ["id", "user_id", "generated_post_id"],
    )
    op.create_table(
        "saved_draft_versions",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("saved_draft_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("generated_post_id", UUID, nullable=False),
        sa.Column("post_version_id", UUID, nullable=False),
        sa.Column("selected_image_id", UUID, nullable=True),
        sa.Column("generation_run_id", UUID, nullable=True),
        sa.Column("restored_from_version_id", UUID, nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(40), nullable=False),
        sa.Column("library_title", sa.String(200), nullable=True),
        sa.Column(
            "created_at", TIMESTAMP, nullable=False, server_default=sa.text("now()")
        ),
        sa.CheckConstraint("version_number > 0", name="ck_saved_draft_versions_number"),
        sa.CheckConstraint(
            "change_type IN ('initial_save', 'manual_edit', "
            "'text_regeneration', 'image_selection', 'image_regeneration', "
            "'metadata_update', 'version_restoration')",
            name="ck_saved_draft_versions_change_type",
        ),
        sa.CheckConstraint(
            "(change_type = 'version_restoration') = "
            "(restored_from_version_id IS NOT NULL)",
            name="ck_saved_draft_versions_restore_reference",
        ),
        sa.ForeignKeyConstraint(
            ["saved_draft_id", "user_id", "generated_post_id"],
            [
                "saved_content_items.id",
                "saved_content_items.user_id",
                "saved_content_items.generated_post_id",
            ],
            name="fk_saved_draft_versions_owned_draft",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["post_version_id", "generated_post_id"],
            ["post_versions.id", "post_versions.generated_post_id"],
            name="fk_saved_draft_versions_post_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["selected_image_id", "generated_post_id"],
            ["generated_images.id", "generated_images.generated_post_id"],
            name="fk_saved_draft_versions_image",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["generation_run_id", "generated_post_id"],
            ["generation_runs.id", "generation_runs.generated_post_id"],
            name="fk_saved_draft_versions_generation_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["restored_from_version_id"],
            ["saved_draft_versions.id"],
            name="fk_saved_draft_versions_restored_from",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "saved_draft_id",
            "version_number",
            name="uq_saved_draft_versions_number",
        ),
    )
    op.create_index(
        "ix_saved_draft_versions_owner_draft_created",
        "saved_draft_versions",
        ["user_id", "saved_draft_id", "created_at"],
    )

    # Preserve existing private saved drafts as the first known baseline.
    op.execute(
        """
        INSERT INTO saved_draft_versions (
            saved_draft_id, user_id, generated_post_id, post_version_id,
            selected_image_id, generation_run_id, version_number, change_type,
            library_title, created_at
        )
        SELECT
            item.id, item.user_id, item.generated_post_id,
            item.selected_post_version_id, item.selected_image_id,
            item.source_generation_id, item.version, 'initial_save',
            item.library_title, item.updated_at
        FROM saved_content_items AS item
        WHERE item.deleted_at IS NULL
        """
    )


def downgrade() -> None:
    """Remove NFA-70 version-history storage."""

    op.drop_index(
        "ix_saved_draft_versions_owner_draft_created",
        table_name="saved_draft_versions",
    )
    op.drop_table("saved_draft_versions")
    op.drop_constraint(
        "uq_saved_content_id_owner_post",
        "saved_content_items",
        type_="unique",
    )
