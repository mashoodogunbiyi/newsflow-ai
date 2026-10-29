"""Add stable article catalogue ordering support.

Revision ID: 20261029_0005
Revises: 20261029_0004
Create Date: 2026-10-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261029_0005"
down_revision: str | None = "20261029_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Index the stable publication-time and article-ID catalogue order."""

    op.create_index(
        "ix_article_snapshots_publication_article",
        "article_snapshots",
        ["publication_date", "article_id"],
    )


def downgrade() -> None:
    """Remove the catalogue ordering index."""

    op.drop_index(
        "ix_article_snapshots_publication_article",
        table_name="article_snapshots",
    )
