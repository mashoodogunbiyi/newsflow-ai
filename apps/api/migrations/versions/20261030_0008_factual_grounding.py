"""Persist safe factual-grounding decisions for generated drafts.

Revision ID: 20261030_0008
Revises: 20261029_0007
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261030_0008"
down_revision: str | None = "20261029_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add content-free grounding status, warnings, policy, and claim counts."""

    op.add_column(
        "generation_runs",
        sa.Column("grounding_status", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "generation_runs",
        sa.Column("grounding_policy_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "generation_runs",
        sa.Column("grounding_warnings", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "generation_runs",
        sa.Column("grounding_checked_claims", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_generation_runs_grounding_status",
        "generation_runs",
        "grounding_status IS NULL OR grounding_status IN "
        "('passed_automated_checks', 'review_required', 'rejected')",
    )
    op.create_check_constraint(
        "ck_generation_runs_grounding_checked_claims",
        "generation_runs",
        "grounding_checked_claims IS NULL OR grounding_checked_claims >= 0",
    )
    op.create_check_constraint(
        "ck_generation_runs_grounding_warnings_array",
        "generation_runs",
        "grounding_warnings IS NULL OR jsonb_typeof(grounding_warnings) = 'array'",
    )
    op.create_index(
        "ix_generation_runs_grounding_status",
        "generation_runs",
        ["grounding_status"],
    )


def downgrade() -> None:
    """Remove NFA-42 factual-grounding evidence fields."""

    op.drop_index("ix_generation_runs_grounding_status", table_name="generation_runs")
    op.drop_constraint(
        "ck_generation_runs_grounding_warnings_array",
        "generation_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_generation_runs_grounding_checked_claims",
        "generation_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_generation_runs_grounding_status",
        "generation_runs",
        type_="check",
    )
    op.drop_column("generation_runs", "grounding_checked_claims")
    op.drop_column("generation_runs", "grounding_warnings")
    op.drop_column("generation_runs", "grounding_policy_version")
    op.drop_column("generation_runs", "grounding_status")
