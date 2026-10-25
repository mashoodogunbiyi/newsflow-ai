"""Add CSRF validation and lookup support to authenticated sessions.

Revision ID: 20261025_0002
Revises: 20261025_0001
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261025_0002"
down_revision: str | None = "20261025_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add server-validated CSRF hashes and session maintenance indexes."""

    op.add_column(
        "sessions",
        sa.Column("csrf_token_hash", sa.LargeBinary(), nullable=True),
    )

    # No released code creates sessions before this migration. Clearing any local
    # pre-release rows is safer than inventing CSRF credentials for them.
    op.execute("DELETE FROM sessions")

    op.alter_column("sessions", "csrf_token_hash", nullable=False)
    op.create_check_constraint(
        "ck_sessions_csrf_token_hash_length",
        "sessions",
        "octet_length(csrf_token_hash) = 32",
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])


def downgrade() -> None:
    """Remove NFA-23 session controls while retaining the original table."""

    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_constraint(
        "ck_sessions_csrf_token_hash_length",
        "sessions",
        type_="check",
    )
    op.drop_column("sessions", "csrf_token_hash")
