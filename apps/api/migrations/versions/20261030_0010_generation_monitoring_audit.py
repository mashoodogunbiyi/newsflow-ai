"""Add content-free generation monitoring and audit events.

Revision ID: 20261030_0010
Revises: 20261030_0009
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261030_0010"
down_revision: str | None = "20261030_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Create safe lifecycle events linked to existing usage and run records."""

    op.create_table(
        "generation_audit_events",
        sa.Column(
            "id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("generation_request_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("article_id", UUID, nullable=False),
        sa.Column("generation_run_id", UUID, nullable=True),
        sa.Column("usage_event_id", UUID, nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("model_identifier", sa.String(length=200), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.Column("rights_decision", sa.String(length=100), nullable=True),
        sa.Column("validation_status", sa.String(length=50), nullable=True),
        sa.CheckConstraint(
            "event_type IN ("
            "'generation_started', 'generation_rights_verified', "
            "'generation_rights_denied', 'generation_usage_rejected', "
            "'generation_validation_passed', 'generation_validation_failed', "
            "'generation_completed', 'generation_failed')",
            name="ck_generation_audit_events_type",
        ),
        sa.CheckConstraint(
            "status IN ('started', 'passed', 'succeeded', 'rejected', 'failed')",
            name="ck_generation_audit_events_status",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_generation_audit_events_duration",
        ),
        sa.ForeignKeyConstraint(
            ["generation_run_id"],
            ["generation_runs.id"],
            name="fk_generation_audit_events_generation_run",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["usage_event_id"],
            ["generation_usage_events.id"],
            name="fk_generation_audit_events_usage_event",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_generation_audit_events_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generation_audit_events_request_time",
        "generation_audit_events",
        ["generation_request_id", "occurred_at"],
    )
    op.create_index(
        "ix_generation_audit_events_user_time",
        "generation_audit_events",
        ["user_id", "occurred_at"],
    )
    op.create_index(
        "ix_generation_audit_events_type_time",
        "generation_audit_events",
        ["event_type", "occurred_at"],
    )
    op.create_index(
        "ix_generation_audit_events_error_time",
        "generation_audit_events",
        ["error_category", "occurred_at"],
    )
    op.create_index(
        "ix_generation_audit_events_occurred_at",
        "generation_audit_events",
        ["occurred_at"],
    )


def downgrade() -> None:
    """Remove NFA-45 generation monitoring and audit data."""

    op.drop_index(
        "ix_generation_audit_events_occurred_at",
        table_name="generation_audit_events",
    )
    op.drop_index(
        "ix_generation_audit_events_error_time",
        table_name="generation_audit_events",
    )
    op.drop_index(
        "ix_generation_audit_events_type_time",
        table_name="generation_audit_events",
    )
    op.drop_index(
        "ix_generation_audit_events_user_time",
        table_name="generation_audit_events",
    )
    op.drop_index(
        "ix_generation_audit_events_request_time",
        table_name="generation_audit_events",
    )
    op.drop_table("generation_audit_events")
