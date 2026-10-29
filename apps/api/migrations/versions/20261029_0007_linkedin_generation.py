"""Preserve the rights version used for generated LinkedIn drafts.

Revision ID: 20261029_0007
Revises: 20261029_0006
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261029_0007"
down_revision: str | None = "20261029_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Record the immutable rights decision used by each new AI run."""

    op.add_column(
        "generation_runs",
        sa.Column("article_rights_version_id", UUID, nullable=True),
    )
    op.create_foreign_key(
        "fk_generation_runs_article_rights_version",
        "generation_runs",
        "article_rights_versions",
        ["article_rights_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_generation_runs_article_rights_version",
        "generation_runs",
        ["article_rights_version_id"],
    )


def downgrade() -> None:
    """Remove NFA-40 rights-version generation evidence."""

    op.drop_index(
        "ix_generation_runs_article_rights_version",
        table_name="generation_runs",
    )
    op.drop_constraint(
        "fk_generation_runs_article_rights_version",
        "generation_runs",
        type_="foreignkey",
    )
    op.drop_column("generation_runs", "article_rights_version_id")
