"""Add shared generation usage and operational controls.

Revision ID: 20261030_0009
Revises: 20261030_0008
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261030_0009"
down_revision: str | None = "20261030_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Create content-free generation attempt records and shared indexes."""

    op.create_table(
        "generation_usage_events",
        sa.Column(
            "id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("generation_run_id", UUID, nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("model_identifier", sa.String(length=200), nullable=True),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('started', 'succeeded', 'failed')",
            name="ck_generation_usage_events_status",
        ),
        sa.CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="ck_generation_usage_events_input_tokens",
        ),
        sa.CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="ck_generation_usage_events_output_tokens",
        ),
        sa.CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="ck_generation_usage_events_total_tokens",
        ),
        sa.CheckConstraint(
            "(status = 'started' AND completed_at IS NULL) OR "
            "(status IN ('succeeded', 'failed') AND completed_at IS NOT NULL)",
            name="ck_generation_usage_events_completion",
        ),
        sa.CheckConstraint(
            "(status = 'failed' AND error_category IS NOT NULL) OR "
            "(status != 'failed' AND error_category IS NULL)",
            name="ck_generation_usage_events_error_category",
        ),
        sa.CheckConstraint(
            "(status = 'succeeded' AND generation_run_id IS NOT NULL) OR "
            "status != 'succeeded'",
            name="ck_generation_usage_events_generation_run",
        ),
        sa.ForeignKeyConstraint(
            ["generation_run_id"],
            ["generation_runs.id"],
            name="fk_generation_usage_events_generation_run",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_generation_usage_events_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generation_usage_events_user_created",
        "generation_usage_events",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_generation_usage_events_user_status",
        "generation_usage_events",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_generation_usage_events_expires_at",
        "generation_usage_events",
        ["expires_at"],
    )
    op.create_index(
        "ix_generation_usage_events_error_category",
        "generation_usage_events",
        ["error_category"],
    )
    op.create_index(
        "uq_generation_usage_events_active_request",
        "generation_usage_events",
        ["user_id", "request_fingerprint"],
        unique=True,
        postgresql_where=sa.text("status = 'started'"),
    )


def downgrade() -> None:
    """Remove NFA-43 generation usage records and controls."""

    op.drop_index(
        "uq_generation_usage_events_active_request",
        table_name="generation_usage_events",
    )
    op.drop_index(
        "ix_generation_usage_events_error_category",
        table_name="generation_usage_events",
    )
    op.drop_index(
        "ix_generation_usage_events_expires_at",
        table_name="generation_usage_events",
    )
    op.drop_index(
        "ix_generation_usage_events_user_status",
        table_name="generation_usage_events",
    )
    op.drop_index(
        "ix_generation_usage_events_user_created",
        table_name="generation_usage_events",
    )
    op.drop_table("generation_usage_events")
