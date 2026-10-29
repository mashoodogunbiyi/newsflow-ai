"""Add versioned article rights and provenance retrieval events.

Revision ID: 20261029_0003
Revises: 20261025_0002
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261029_0003"
down_revision: str | None = "20261025_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TIMESTAMP = sa.DateTime(timezone=True)


def upgrade() -> None:
    """Create immutable provenance events and versioned rights decisions."""

    op.create_table(
        "article_provenance_events",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("article_id", UUID, nullable=False),
        sa.Column("source_profile_id", UUID, nullable=False),
        sa.Column("source_item_id", sa.String(200), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("publication_date", TIMESTAMP, nullable=False),
        sa.Column("retrieved_at", TIMESTAMP, nullable=False),
        sa.Column("source_integration_ref", sa.String(100), nullable=False),
        sa.Column("source_contract_version", sa.String(20), nullable=False),
        sa.Column("authorisation_reference", sa.String(100), nullable=False),
        sa.Column("ingestion_action", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "length(btrim(source_item_id)) BETWEEN 1 AND 200",
            name="ck_article_provenance_source_item_id",
        ),
        sa.CheckConstraint(
            "canonical_url ~ '^https://' AND length(canonical_url) <= 2048",
            name="ck_article_provenance_url",
        ),
        sa.CheckConstraint(
            "ingestion_action IN ('created', 'updated', 'skipped')",
            name="ck_article_provenance_action",
        ),
        sa.CheckConstraint(
            "retrieved_at >= publication_date",
            name="ck_article_provenance_retrieval_time",
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            name="fk_article_provenance_article",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_profile_id"],
            ["source_profiles.id"],
            name="fk_article_provenance_source_profile",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_article_provenance_article_retrieved",
        "article_provenance_events",
        ["article_id", sa.text("retrieved_at DESC")],
    )

    op.create_table(
        "article_rights_versions",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("article_id", UUID, nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False),
        sa.Column("storage_allowed", sa.Boolean(), nullable=False),
        sa.Column("display_allowed", sa.Boolean(), nullable=False),
        sa.Column("ai_processing_allowed", sa.Boolean(), nullable=False),
        sa.Column("derivative_output_allowed", sa.Boolean(), nullable=False),
        sa.Column("redistribution_allowed", sa.Boolean(), nullable=False),
        sa.Column("attribution_required", sa.Boolean(), nullable=False),
        sa.Column("attribution_text", sa.String(500), nullable=True),
        sa.Column("retention_rule", sa.String(200), nullable=False),
        sa.Column("retention_expires_at", TIMESTAMP, nullable=True),
        sa.Column("authorisation_reference", sa.String(100), nullable=False),
        sa.Column("source_contract_version", sa.String(20), nullable=False),
        sa.Column("rights_last_verified_at", TIMESTAMP, nullable=True),
        sa.Column("effective_from", TIMESTAMP, nullable=False),
        sa.Column("superseded_at", TIMESTAMP, nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name="ck_article_rights_version_number",
        ),
        sa.CheckConstraint(
            "verification_status IN ('verified', 'unverified', 'revoked')",
            name="ck_article_rights_verification_status",
        ),
        sa.CheckConstraint(
            "verification_status <> 'verified' OR rights_last_verified_at IS NOT NULL",
            name="ck_article_rights_verified_at",
        ),
        sa.CheckConstraint(
            "verification_status = 'verified' OR "
            "NOT (storage_allowed OR display_allowed OR ai_processing_allowed "
            "OR derivative_output_allowed OR redistribution_allowed)",
            name="ck_article_rights_fail_closed",
        ),
        sa.CheckConstraint(
            "NOT derivative_output_allowed OR ai_processing_allowed",
            name="ck_article_rights_derivative_permission",
        ),
        sa.CheckConstraint(
            "NOT attribution_required OR "
            "length(btrim(attribution_text)) BETWEEN 1 AND 500",
            name="ck_article_rights_attribution",
        ),
        sa.CheckConstraint(
            "retention_expires_at IS NULL OR retention_expires_at > effective_from",
            name="ck_article_rights_retention_expiry",
        ),
        sa.CheckConstraint(
            "superseded_at IS NULL OR superseded_at >= effective_from",
            name="ck_article_rights_superseded_at",
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            name="fk_article_rights_article",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "article_id",
            "version_number",
            name="uq_article_rights_version_number",
        ),
        sa.UniqueConstraint(
            "id",
            "article_id",
            name="uq_article_rights_id_article",
        ),
    )
    op.create_index(
        "ix_article_rights_article_effective",
        "article_rights_versions",
        ["article_id", sa.text("effective_from DESC")],
    )
    op.create_index(
        "uq_article_rights_current",
        "article_rights_versions",
        ["article_id"],
        unique=True,
        postgresql_where=sa.text("superseded_at IS NULL"),
    )

    op.add_column(
        "articles",
        sa.Column("current_rights_version_id", UUID, nullable=True),
    )

    op.execute(
        """
        INSERT INTO article_rights_versions (
            article_id,
            version_number,
            verification_status,
            storage_allowed,
            display_allowed,
            ai_processing_allowed,
            derivative_output_allowed,
            redistribution_allowed,
            attribution_required,
            attribution_text,
            retention_rule,
            retention_expires_at,
            authorisation_reference,
            source_contract_version,
            rights_last_verified_at,
            effective_from
        )
        SELECT
            articles.id,
            1,
            'verified',
            snapshots.storage_allowed,
            snapshots.display_allowed,
            snapshots.ai_processing_allowed,
            snapshots.derivative_output_allowed,
            false,
            true,
            snapshots.attribution_text,
            snapshots.retention_rule,
            snapshots.rights_expires_at,
            snapshots.rights_decision_ref,
            snapshots.contract_version,
            snapshots.retrieved_at,
            snapshots.retrieved_at
        FROM articles
        JOIN article_snapshots AS snapshots
          ON snapshots.id = articles.current_snapshot_id
        """
    )
    op.execute(
        """
        UPDATE articles
        SET current_rights_version_id = rights.id
        FROM article_rights_versions AS rights
        WHERE rights.article_id = articles.id
          AND rights.superseded_at IS NULL
        """
    )
    op.create_foreign_key(
        "fk_articles_current_rights",
        "articles",
        "article_rights_versions",
        ["current_rights_version_id", "id"],
        ["id", "article_id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    """Remove NFA-32 rights versions and provenance events."""

    op.drop_constraint(
        "fk_articles_current_rights",
        "articles",
        type_="foreignkey",
    )
    op.drop_column("articles", "current_rights_version_id")
    op.drop_index(
        "uq_article_rights_current",
        table_name="article_rights_versions",
    )
    op.drop_index(
        "ix_article_rights_article_effective",
        table_name="article_rights_versions",
    )
    op.drop_table("article_rights_versions")
    op.drop_index(
        "ix_article_provenance_article_retrieved",
        table_name="article_provenance_events",
    )
    op.drop_table("article_provenance_events")
