"""Add article-ingestion observability fields and indexes.

Revision ID: 20261029_0006
Revises: 20261029_0005
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261029_0006"
down_revision: str | None = "20261029_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store safe duration and failure dimensions for monitoring."""

    op.add_column(
        "article_sync_jobs",
        sa.Column(
            "provider_failures",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "article_sync_jobs",
        sa.Column(
            "provider_duration_ms",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "article_sync_jobs",
        sa.Column("error_category", sa.String(60), nullable=True),
    )
    op.add_column(
        "article_sync_jobs",
        sa.Column("failed_stage", sa.String(40), nullable=True),
    )
    op.create_check_constraint(
        "ck_article_sync_jobs_provider_duration",
        "article_sync_jobs",
        "provider_failures >= 0 AND provider_duration_ms >= 0",
    )
    op.create_check_constraint(
        "ck_article_sync_jobs_error_category",
        "article_sync_jobs",
        "error_category IS NULL OR error_category IN ("
        "'provider_connection_error', 'provider_timeout', "
        "'provider_authentication_error', 'provider_rate_limit_error', "
        "'article_validation_error', 'database_error', "
        "'synchronisation_conflict', 'source_authorisation_error', "
        "'internal_pipeline_error')",
    )
    op.create_index(
        "ix_article_sync_jobs_created_at",
        "article_sync_jobs",
        [sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_article_sync_jobs_status_created",
        "article_sync_jobs",
        ["status", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    """Remove ingestion-observability storage."""

    op.drop_index("ix_article_sync_jobs_status_created", table_name="article_sync_jobs")
    op.drop_index("ix_article_sync_jobs_created_at", table_name="article_sync_jobs")
    op.drop_constraint(
        "ck_article_sync_jobs_error_category",
        "article_sync_jobs",
        type_="check",
    )
    op.drop_constraint(
        "ck_article_sync_jobs_provider_duration",
        "article_sync_jobs",
        type_="check",
    )
    op.drop_column("article_sync_jobs", "failed_stage")
    op.drop_column("article_sync_jobs", "error_category")
    op.drop_column("article_sync_jobs", "provider_duration_ms")
    op.drop_column("article_sync_jobs", "provider_failures")
