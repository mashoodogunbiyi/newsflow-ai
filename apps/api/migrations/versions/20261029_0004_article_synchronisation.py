"""Add durable article synchronisation jobs and checkpoints.

Revision ID: 20261029_0004
Revises: 20261029_0003
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261029_0004"
down_revision: str | None = "20261029_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TIMESTAMP = sa.DateTime(timezone=True)


def upgrade() -> None:
    """Create role, job, checkpoint, lease, and statistics storage."""

    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'user'"),
        ),
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('user', 'admin')",
    )

    op.create_table(
        "article_sync_checkpoints",
        sa.Column("provider_id", sa.String(100), primary_key=True),
        sa.Column("last_successful_publication_at", TIMESTAMP, nullable=True),
        sa.Column("last_successful_completed_at", TIMESTAMP, nullable=True),
        sa.Column("next_scheduled_at", TIMESTAMP, nullable=True),
        sa.Column(
            "updated_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "length(btrim(provider_id)) BETWEEN 1 AND 100",
            name="ck_article_sync_checkpoints_provider",
        ),
    )

    op.create_table(
        "article_sync_jobs",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider_id", sa.String(100), nullable=False),
        sa.Column("trigger_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("requested_by_user_id", UUID, nullable=True),
        sa.Column("checkpoint_from", TIMESTAMP, nullable=True),
        sa.Column("checkpoint_candidate", TIMESTAMP, nullable=True),
        sa.Column("scheduled_for", TIMESTAMP, nullable=True),
        sa.Column("started_at", TIMESTAMP, nullable=True),
        sa.Column("completed_at", TIMESTAMP, nullable=True),
        sa.Column("lease_expires_at", TIMESTAMP, nullable=True),
        sa.Column(
            "articles_retrieved",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "articles_created",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "articles_updated",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "articles_skipped",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "articles_rejected",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "provider_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("error_code", sa.String(60), nullable=True),
        sa.Column("error_summary", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "length(btrim(provider_id)) BETWEEN 1 AND 100",
            name="ck_article_sync_jobs_provider",
        ),
        sa.CheckConstraint(
            "trigger_type IN ('scheduled', 'manual')",
            name="ck_article_sync_jobs_trigger",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', "
            "'partially_completed', 'interrupted')",
            name="ck_article_sync_jobs_status",
        ),
        sa.CheckConstraint(
            "trigger_type <> 'manual' OR requested_by_user_id IS NOT NULL",
            name="ck_article_sync_jobs_manual_requester",
        ),
        sa.CheckConstraint(
            "articles_retrieved >= 0 AND articles_created >= 0 "
            "AND articles_updated >= 0 AND articles_skipped >= 0 "
            "AND articles_rejected >= 0 AND provider_attempts >= 0",
            name="ck_article_sync_jobs_counts",
        ),
        sa.CheckConstraint(
            "articles_created + articles_updated + articles_skipped "
            "+ articles_rejected <= articles_retrieved",
            name="ck_article_sync_jobs_processed_counts",
        ),
        sa.CheckConstraint(
            "status NOT IN ('completed', 'failed', 'partially_completed', "
            "'interrupted') OR completed_at IS NOT NULL",
            name="ck_article_sync_jobs_terminal_time",
        ),
        sa.CheckConstraint(
            "status NOT IN ('pending', 'running') OR lease_expires_at IS NOT NULL",
            name="ck_article_sync_jobs_active_lease",
        ),
        sa.CheckConstraint(
            "error_summary IS NULL OR length(error_summary) <= 500",
            name="ck_article_sync_jobs_error_summary",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name="fk_article_sync_jobs_requester",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_article_sync_jobs_provider_created",
        "article_sync_jobs",
        ["provider_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "uq_article_sync_jobs_active_provider",
        "article_sync_jobs",
        ["provider_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )
    op.create_index(
        "ix_article_sync_jobs_lease",
        "article_sync_jobs",
        ["lease_expires_at"],
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )


def downgrade() -> None:
    """Remove article synchronisation storage and account roles."""

    op.drop_index("ix_article_sync_jobs_lease", table_name="article_sync_jobs")
    op.drop_index(
        "uq_article_sync_jobs_active_provider",
        table_name="article_sync_jobs",
    )
    op.drop_index(
        "ix_article_sync_jobs_provider_created",
        table_name="article_sync_jobs",
    )
    op.drop_table("article_sync_jobs")
    op.drop_table("article_sync_checkpoints")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
