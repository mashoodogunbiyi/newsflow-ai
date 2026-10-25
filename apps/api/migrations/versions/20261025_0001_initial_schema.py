"""Create the initial NewsFlow AI schema.

Revision ID: 20261025_0001
Revises:
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261025_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TIMESTAMP = sa.DateTime(timezone=True)


def upgrade() -> None:
    """Create the NFA-20 MVP schema and integrity controls."""

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("email_verified_at", TIMESTAMP, nullable=True),
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
        sa.Column("deleted_at", TIMESTAMP, nullable=True),
        sa.CheckConstraint(
            "email = lower(btrim(email))",
            name="ck_users_email_normalized",
        ),
        sa.CheckConstraint(
            "length(password_hash) >= 60",
            name="ck_users_password_hash_length",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'deletion_pending')",
            name="ck_users_status",
        ),
        sa.CheckConstraint(
            "status = 'deletion_pending' OR deleted_at IS NULL",
            name="ck_users_deleted_state",
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "sessions",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", TIMESTAMP, nullable=False),
        sa.Column("last_seen_at", TIMESTAMP, nullable=True),
        sa.Column("revoked_at", TIMESTAMP, nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "octet_length(token_hash) = 32",
            name="ck_sessions_token_hash_length",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_sessions_expiry",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_sessions_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )

    op.create_table(
        "source_profiles",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_key", sa.String(100), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("contract_version", sa.String(20), nullable=False),
        sa.Column("profile_type", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'disabled'"),
        ),
        sa.Column(
            "authorisation_decision_ref",
            sa.String(100),
            nullable=False,
        ),
        sa.Column("access_method", sa.String(50), nullable=False),
        sa.Column("approved_at", TIMESTAMP, nullable=True),
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
            "profile_type IN ('fixture', 'live')",
            name="ck_source_profiles_type",
        ),
        sa.CheckConstraint(
            "status IN ('enabled', 'disabled')",
            name="ck_source_profiles_status",
        ),
        sa.CheckConstraint(
            "profile_type <> 'live' OR status = 'disabled'",
            name="ck_source_profiles_live_disabled",
        ),
        sa.UniqueConstraint("profile_key", name="uq_source_profiles_key"),
    )

    op.create_table(
        "articles",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_profile_id", UUID, nullable=False),
        sa.Column("source_item_id", sa.String(200), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("current_snapshot_id", UUID, nullable=True),
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
            "canonical_url ~ '^https://'",
            name="ck_articles_canonical_url_https",
        ),
        sa.CheckConstraint(
            "length(canonical_url) <= 2048",
            name="ck_articles_canonical_url_length",
        ),
        sa.CheckConstraint(
            "length(btrim(source_item_id)) BETWEEN 1 AND 200",
            name="ck_articles_source_item_id",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'quarantined', 'withdrawn', 'expired')",
            name="ck_articles_status",
        ),
        sa.ForeignKeyConstraint(
            ["source_profile_id"],
            ["source_profiles.id"],
            name="fk_articles_source_profile",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "source_profile_id",
            "source_item_id",
            name="uq_articles_source_identity",
        ),
        sa.UniqueConstraint("canonical_url", name="uq_articles_canonical_url"),
    )

    op.create_table(
        "article_snapshots",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("article_id", UUID, nullable=False),
        sa.Column("snapshot_number", sa.Integer(), nullable=False),
        sa.Column("contract_version", sa.String(20), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("publication_date", TIMESTAMP, nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column(
            "permitted_content_status",
            sa.String(20),
            nullable=False,
        ),
        sa.Column(
            "permitted_content_type",
            sa.String(40),
            nullable=False,
        ),
        sa.Column("permitted_content_text", sa.Text(), nullable=True),
        sa.Column("storage_allowed", sa.Boolean(), nullable=False),
        sa.Column("display_allowed", sa.Boolean(), nullable=False),
        sa.Column(
            "ai_processing_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "derivative_output_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("rights_decision_ref", sa.String(100), nullable=False),
        sa.Column("access_method", sa.String(50), nullable=False),
        sa.Column("retention_rule", sa.String(100), nullable=False),
        sa.Column("rights_expires_at", TIMESTAMP, nullable=True),
        sa.Column(
            "attribution_display_name",
            sa.String(200),
            nullable=False,
        ),
        sa.Column("attribution_text", sa.String(500), nullable=False),
        sa.Column("byline", sa.String(300), nullable=True),
        sa.Column("copyright_notice", sa.String(500), nullable=True),
        sa.Column("retrieved_at", TIMESTAMP, nullable=False),
        sa.Column("source_modified_at", TIMESTAMP, nullable=True),
        sa.Column("content_fingerprint", sa.CHAR(64), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "snapshot_number > 0",
            name="ck_article_snapshots_number",
        ),
        sa.CheckConstraint(
            "length(btrim(title)) BETWEEN 1 AND 300",
            name="ck_article_snapshots_title",
        ),
        sa.CheckConstraint(
            "category IN ('technology', 'business', 'world_news', 'science', 'other')",
            name="ck_article_snapshots_category",
        ),
        sa.CheckConstraint(
            "canonical_url ~ '^https://' AND length(canonical_url) <= 2048",
            name="ck_article_snapshots_url",
        ),
        sa.CheckConstraint(
            "permitted_content_status IN ('available', 'missing', 'not_permitted')",
            name="ck_article_snapshots_content_status",
        ),
        sa.CheckConstraint(
            "permitted_content_type IN "
            "('synthetic', 'provider_description', "
            "'licensed_article_text', 'none')",
            name="ck_article_snapshots_content_type",
        ),
        sa.CheckConstraint(
            "(permitted_content_status = 'available' "
            "AND permitted_content_text IS NOT NULL "
            "AND permitted_content_type <> 'none') "
            "OR (permitted_content_status IN ('missing', 'not_permitted') "
            "AND permitted_content_text IS NULL "
            "AND permitted_content_type = 'none')",
            name="ck_article_snapshots_content_state",
        ),
        sa.CheckConstraint(
            "permitted_content_text IS NULL OR length(permitted_content_text) <= 20000",
            name="ck_article_snapshots_content_length",
        ),
        sa.CheckConstraint(
            "storage_allowed",
            name="ck_article_snapshots_storage_allowed",
        ),
        sa.CheckConstraint(
            "NOT derivative_output_allowed OR ai_processing_allowed",
            name="ck_article_snapshots_derivative_permission",
        ),
        sa.CheckConstraint(
            "source_modified_at IS NULL OR source_modified_at >= publication_date",
            name="ck_article_snapshots_modified_at",
        ),
        sa.CheckConstraint(
            "rights_expires_at IS NULL OR rights_expires_at > retrieved_at",
            name="ck_article_snapshots_rights_expiry",
        ),
        sa.CheckConstraint(
            "content_fingerprint IS NULL OR content_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_article_snapshots_fingerprint",
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            name="fk_article_snapshots_article",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "article_id",
            "snapshot_number",
            name="uq_article_snapshot_number",
        ),
        sa.UniqueConstraint(
            "id",
            "article_id",
            name="uq_article_snapshots_id_article",
        ),
    )

    op.create_foreign_key(
        "fk_articles_current_snapshot",
        "articles",
        "article_snapshots",
        ["current_snapshot_id", "id"],
        ["id", "article_id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_table(
        "generated_posts",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("article_snapshot_id", UUID, nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
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
        sa.Column("deleted_at", TIMESTAMP, nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'saved', 'archived', 'deleted')",
            name="ck_generated_posts_status",
        ),
        sa.CheckConstraint(
            "(status = 'deleted') = (deleted_at IS NOT NULL)",
            name="ck_generated_posts_deleted_state",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_generated_posts_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["article_snapshot_id"],
            ["article_snapshots.id"],
            name="fk_generated_posts_article_snapshot",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "id",
            "user_id",
            name="uq_generated_posts_id_user",
        ),
    )

    op.create_table(
        "generation_runs",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("generated_post_id", UUID, nullable=False),
        sa.Column("generation_type", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'queued'"),
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_template_version", sa.String(50), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("additional_instructions", sa.String(1000), nullable=True),
        sa.Column(
            "internal_trace_id",
            UUID,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider_request_id", sa.String(200), nullable=True),
        sa.Column(
            "attempt_count",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(12, 6), nullable=True),
        sa.Column("currency_code", sa.CHAR(3), nullable=True),
        sa.Column("safe_error_code", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", TIMESTAMP, nullable=True),
        sa.Column("completed_at", TIMESTAMP, nullable=True),
        sa.CheckConstraint(
            "generation_type IN ('post', 'image')",
            name="ck_generation_runs_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'blocked')",
            name="ck_generation_runs_status",
        ),
        sa.CheckConstraint(
            "attempt_count BETWEEN 1 AND 3",
            name="ck_generation_runs_attempt_count",
        ),
        sa.CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="ck_generation_runs_input_tokens",
        ),
        sa.CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="ck_generation_runs_output_tokens",
        ),
        sa.CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="ck_generation_runs_estimated_cost",
        ),
        sa.CheckConstraint(
            "length(prompt_text) BETWEEN 1 AND 50000",
            name="ck_generation_runs_prompt_length",
        ),
        sa.CheckConstraint(
            "(status IN ('succeeded', 'failed', 'blocked') "
            "AND completed_at IS NOT NULL) "
            "OR (status IN ('queued', 'running') "
            "AND completed_at IS NULL)",
            name="ck_generation_runs_completion_state",
        ),
        sa.CheckConstraint(
            "status NOT IN ('failed', 'blocked') OR safe_error_code IS NOT NULL",
            name="ck_generation_runs_error_code",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= created_at",
            name="ck_generation_runs_completed_at",
        ),
        sa.ForeignKeyConstraint(
            ["generated_post_id"],
            ["generated_posts.id"],
            name="fk_generation_runs_generated_post",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "generated_post_id",
            "generation_type",
            "idempotency_key",
            name="uq_generation_idempotency",
        ),
        sa.UniqueConstraint(
            "internal_trace_id",
            name="uq_generation_runs_trace_id",
        ),
        sa.UniqueConstraint(
            "id",
            "generated_post_id",
            name="uq_generation_runs_id_post",
        ),
    )

    op.create_table(
        "generation_facts",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("generation_run_id", UUID, nullable=False),
        sa.Column("fact_key", sa.String(50), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("fact_text", sa.String(2000), nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "position > 0",
            name="ck_generation_facts_position",
        ),
        sa.CheckConstraint(
            "length(btrim(fact_text)) > 0",
            name="ck_generation_facts_text",
        ),
        sa.ForeignKeyConstraint(
            ["generation_run_id"],
            ["generation_runs.id"],
            name="fk_generation_facts_run",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "generation_run_id",
            "fact_key",
            name="uq_generation_facts_key",
        ),
        sa.UniqueConstraint(
            "generation_run_id",
            "position",
            name="uq_generation_facts_position",
        ),
    )

    op.create_table(
        "post_versions",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("generated_post_id", UUID, nullable=False),
        sa.Column("generation_run_id", UUID, nullable=True),
        sa.Column("previous_version_id", UUID, nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("tone", sa.String(30), nullable=False),
        sa.Column("length_option", sa.String(20), nullable=False),
        sa.Column("audience", sa.String(40), nullable=False),
        sa.Column("hook", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("insight", sa.Text(), nullable=True),
        sa.Column("call_to_action", sa.Text(), nullable=True),
        sa.Column("rendered_text", sa.Text(), nullable=False),
        sa.Column("source_attribution", sa.String(500), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name="ck_post_versions_number",
        ),
        sa.CheckConstraint(
            "origin IN ('ai', 'manual')",
            name="ck_post_versions_origin",
        ),
        sa.CheckConstraint(
            "origin <> 'ai' OR generation_run_id IS NOT NULL",
            name="ck_post_versions_ai_run",
        ),
        sa.CheckConstraint(
            "tone IN "
            "('professional', 'educational', 'conversational', "
            "'inspirational', 'analytical')",
            name="ck_post_versions_tone",
        ),
        sa.CheckConstraint(
            "length_option IN ('short', 'medium', 'long')",
            name="ck_post_versions_length_option",
        ),
        sa.CheckConstraint(
            "audience IN "
            "('general_professionals', 'business_leaders', "
            "'technology_professionals', 'entrepreneurs')",
            name="ck_post_versions_audience",
        ),
        sa.CheckConstraint(
            "length(btrim(hook)) > 0 "
            "AND length(btrim(summary)) > 0 "
            "AND length(btrim(rendered_text)) > 0",
            name="ck_post_versions_required_text",
        ),
        sa.CheckConstraint(
            "word_count >= 0",
            name="ck_post_versions_word_count",
        ),
        sa.ForeignKeyConstraint(
            ["generated_post_id"],
            ["generated_posts.id"],
            name="fk_post_versions_generated_post",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["generation_run_id", "generated_post_id"],
            ["generation_runs.id", "generation_runs.generated_post_id"],
            name="fk_post_versions_generation_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["previous_version_id"],
            ["post_versions.id"],
            name="fk_post_versions_previous",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_post_versions_creator",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "generated_post_id",
            "version_number",
            name="uq_post_version_number",
        ),
        sa.UniqueConstraint(
            "generation_run_id",
            name="uq_post_versions_generation_run",
        ),
        sa.UniqueConstraint(
            "id",
            "generated_post_id",
            name="uq_post_versions_id_post",
        ),
    )

    op.create_table(
        "post_version_hashtags",
        sa.Column("post_version_id", UUID, primary_key=True),
        sa.Column("position", sa.SmallInteger(), primary_key=True),
        sa.Column("hashtag", sa.String(100), nullable=False),
        sa.CheckConstraint(
            "position BETWEEN 1 AND 5",
            name="ck_post_version_hashtags_position",
        ),
        sa.CheckConstraint(
            "hashtag ~ '^#[^[:space:]]+$'",
            name="ck_post_version_hashtags_format",
        ),
        sa.ForeignKeyConstraint(
            ["post_version_id"],
            ["post_versions.id"],
            name="fk_post_version_hashtags_version",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "post_version_id",
            "hashtag",
            name="uq_post_version_hashtags_value",
        ),
    )

    op.create_table(
        "post_claims",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("post_version_id", UUID, nullable=False),
        sa.Column("claim_key", sa.String(50), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("claim_text", sa.String(2000), nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("position > 0", name="ck_post_claims_position"),
        sa.CheckConstraint(
            "length(btrim(claim_text)) > 0",
            name="ck_post_claims_text",
        ),
        sa.ForeignKeyConstraint(
            ["post_version_id"],
            ["post_versions.id"],
            name="fk_post_claims_version",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "post_version_id",
            "claim_key",
            name="uq_post_claims_key",
        ),
        sa.UniqueConstraint(
            "post_version_id",
            "position",
            name="uq_post_claims_position",
        ),
    )

    op.create_table(
        "post_claim_sources",
        sa.Column("post_claim_id", UUID, primary_key=True),
        sa.Column("generation_fact_id", UUID, primary_key=True),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["post_claim_id"],
            ["post_claims.id"],
            name="fk_post_claim_sources_claim",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["generation_fact_id"],
            ["generation_facts.id"],
            name="fk_post_claim_sources_fact",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "generated_images",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("generated_post_id", UUID, nullable=False),
        sa.Column("source_post_version_id", UUID, nullable=True),
        sa.Column("generation_run_id", UUID, nullable=False),
        sa.Column("storage_provider", sa.String(50), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("width_px", sa.Integer(), nullable=False),
        sa.Column("height_px", sa.Integer(), nullable=False),
        sa.Column("alt_text", sa.String(1000), nullable=True),
        sa.Column(
            "safety_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "ai_disclosure_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'available'"),
        ),
        sa.Column(
            "created_at",
            TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", TIMESTAMP, nullable=True),
        sa.CheckConstraint(
            "byte_size > 0 AND width_px > 0 AND height_px > 0",
            name="ck_generated_images_dimensions",
        ),
        sa.CheckConstraint(
            "mime_type IN ('image/png', 'image/jpeg', 'image/webp')",
            name="ck_generated_images_mime_type",
        ),
        sa.CheckConstraint(
            "safety_status IN ('pending', 'approved', 'blocked')",
            name="ck_generated_images_safety_status",
        ),
        sa.CheckConstraint(
            "status IN ('available', 'deleted')",
            name="ck_generated_images_status",
        ),
        sa.CheckConstraint(
            "(status = 'deleted') = (deleted_at IS NOT NULL)",
            name="ck_generated_images_deleted_state",
        ),
        sa.ForeignKeyConstraint(
            ["generated_post_id"],
            ["generated_posts.id"],
            name="fk_generated_images_generated_post",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_post_version_id", "generated_post_id"],
            ["post_versions.id", "post_versions.generated_post_id"],
            name="fk_generated_images_post_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["generation_run_id", "generated_post_id"],
            ["generation_runs.id", "generation_runs.generated_post_id"],
            name="fk_generated_images_generation_run",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "generation_run_id",
            name="uq_generated_images_run",
        ),
        sa.UniqueConstraint(
            "storage_key",
            name="uq_generated_images_storage_key",
        ),
        sa.UniqueConstraint(
            "id",
            "generated_post_id",
            name="uq_generated_images_id_post",
        ),
    )

    op.create_table(
        "saved_content_items",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("generated_post_id", UUID, nullable=False),
        sa.Column("selected_post_version_id", UUID, nullable=False),
        sa.Column("selected_image_id", UUID, nullable=True),
        sa.Column("library_title", sa.String(200), nullable=True),
        sa.Column(
            "saved_at",
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
        sa.Column("deleted_at", TIMESTAMP, nullable=True),
        sa.ForeignKeyConstraint(
            ["generated_post_id", "user_id"],
            ["generated_posts.id", "generated_posts.user_id"],
            name="fk_saved_content_owned_post",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["selected_post_version_id", "generated_post_id"],
            ["post_versions.id", "post_versions.generated_post_id"],
            name="fk_saved_content_post_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["selected_image_id", "generated_post_id"],
            ["generated_images.id", "generated_images.generated_post_id"],
            name="fk_saved_content_image",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "user_id",
            "generated_post_id",
            name="uq_saved_content_post",
        ),
    )

    op.create_index(
        "ix_sessions_active_user",
        "sessions",
        ["user_id", "expires_at"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "ix_articles_catalogue",
        "articles",
        ["status", sa.text("updated_at DESC")],
    )
    op.create_index(
        "ix_article_snapshots_article",
        "article_snapshots",
        ["article_id", sa.text("retrieved_at DESC")],
    )
    op.create_index(
        "ix_article_snapshots_category_date",
        "article_snapshots",
        ["category", sa.text("publication_date DESC")],
    )
    op.create_index(
        "ix_generated_posts_owner_updated",
        "generated_posts",
        ["user_id", sa.text("updated_at DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_generation_runs_status",
        "generation_runs",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_generation_runs_post",
        "generation_runs",
        ["generated_post_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_post_versions_post",
        "post_versions",
        ["generated_post_id", sa.text("version_number DESC")],
    )
    op.create_index(
        "uq_post_current_version",
        "post_versions",
        ["generated_post_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "ix_generated_images_post",
        "generated_images",
        ["generated_post_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_saved_content_owner_updated",
        "saved_content_items",
        ["user_id", sa.text("updated_at DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.execute(
        """
        CREATE FUNCTION set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $function$
        """
    )
    for table in (
        "users",
        "source_profiles",
        "articles",
        "generated_posts",
        "saved_content_items",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_set_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at()
            """
        )

    op.execute(
        """
        CREATE FUNCTION validate_generated_post_snapshot()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            snapshot article_snapshots%ROWTYPE;
        BEGIN
            SELECT * INTO snapshot
            FROM article_snapshots
            WHERE id = NEW.article_snapshot_id;

            IF NOT snapshot.ai_processing_allowed
               OR NOT snapshot.derivative_output_allowed
               OR (snapshot.rights_expires_at IS NOT NULL
                   AND snapshot.rights_expires_at <= now()) THEN
                RAISE EXCEPTION
                    'The selected article snapshot is not eligible for generation.';
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_generated_posts_validate_snapshot
        BEFORE INSERT OR UPDATE OF article_snapshot_id ON generated_posts
        FOR EACH ROW
        EXECUTE FUNCTION validate_generated_post_snapshot()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_generation_fact()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            run_type varchar(20);
        BEGIN
            SELECT generation_type INTO run_type
            FROM generation_runs
            WHERE id = NEW.generation_run_id;

            IF run_type <> 'post' THEN
                RAISE EXCEPTION
                    'Generation facts require a post generation run.';
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_generation_facts_validate_run
        BEFORE INSERT OR UPDATE ON generation_facts
        FOR EACH ROW
        EXECUTE FUNCTION validate_generation_fact()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_post_version()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            owner_id uuid;
            previous_post_id uuid;
            run_type varchar(20);
        BEGIN
            SELECT user_id INTO owner_id
            FROM generated_posts
            WHERE id = NEW.generated_post_id;

            IF owner_id IS DISTINCT FROM NEW.created_by_user_id THEN
                RAISE EXCEPTION
                    'Post version creator must own the generated post.';
            END IF;

            IF NEW.previous_version_id IS NOT NULL THEN
                SELECT generated_post_id INTO previous_post_id
                FROM post_versions
                WHERE id = NEW.previous_version_id;

                IF previous_post_id IS DISTINCT FROM NEW.generated_post_id THEN
                    RAISE EXCEPTION
                        'Previous version must belong to the same post.';
                END IF;
            END IF;

            IF NEW.generation_run_id IS NOT NULL THEN
                SELECT generation_type INTO run_type
                FROM generation_runs
                WHERE id = NEW.generation_run_id;

                IF run_type <> 'post' THEN
                    RAISE EXCEPTION
                        'Post versions require a post generation run.';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_post_versions_validate
        BEFORE INSERT ON post_versions
        FOR EACH ROW
        EXECUTE FUNCTION validate_post_version()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_new_post_version_hashtags()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            hashtag_count integer;
        BEGIN
            SELECT count(*) INTO hashtag_count
            FROM post_version_hashtags
            WHERE post_version_id = NEW.id;

            IF hashtag_count < 3 OR hashtag_count > 5 THEN
                RAISE EXCEPTION
                    'A post version must contain between three and five hashtags.';
            END IF;
            RETURN NULL;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_post_versions_hashtag_count
        AFTER INSERT ON post_versions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION validate_new_post_version_hashtags()
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_changed_post_hashtags()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            target_version_id uuid;
            hashtag_count integer;
        BEGIN
            target_version_id = COALESCE(NEW.post_version_id, OLD.post_version_id);

            IF NOT EXISTS (
                SELECT 1 FROM post_versions WHERE id = target_version_id
            ) THEN
                RETURN NULL;
            END IF;

            SELECT count(*) INTO hashtag_count
            FROM post_version_hashtags
            WHERE post_version_id = target_version_id;

            IF hashtag_count < 3 OR hashtag_count > 5 THEN
                RAISE EXCEPTION
                    'A post version must contain between three and five hashtags.';
            END IF;
            RETURN NULL;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_post_hashtags_count
        AFTER INSERT OR UPDATE OR DELETE ON post_version_hashtags
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION validate_changed_post_hashtags()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_claim_source()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            claim_post_id uuid;
            fact_post_id uuid;
        BEGIN
            SELECT pv.generated_post_id INTO claim_post_id
            FROM post_claims AS pc
            JOIN post_versions AS pv ON pv.id = pc.post_version_id
            WHERE pc.id = NEW.post_claim_id;

            SELECT gr.generated_post_id INTO fact_post_id
            FROM generation_facts AS gf
            JOIN generation_runs AS gr ON gr.id = gf.generation_run_id
            WHERE gf.id = NEW.generation_fact_id;

            IF claim_post_id IS DISTINCT FROM fact_post_id THEN
                RAISE EXCEPTION
                    'A claim can reference facts only from the same generated post.';
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_post_claim_sources_validate
        BEFORE INSERT OR UPDATE ON post_claim_sources
        FOR EACH ROW
        EXECUTE FUNCTION validate_claim_source()
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_new_claim_has_source()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            source_count integer;
        BEGIN
            SELECT count(*) INTO source_count
            FROM post_claim_sources
            WHERE post_claim_id = NEW.id;

            IF source_count < 1 THEN
                RAISE EXCEPTION
                    'Every factual claim must reference at least one source fact.';
            END IF;
            RETURN NULL;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_post_claims_require_source
        AFTER INSERT ON post_claims
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION validate_new_claim_has_source()
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_claim_source_delete()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            source_count integer;
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM post_claims WHERE id = OLD.post_claim_id
            ) THEN
                RETURN NULL;
            END IF;

            SELECT count(*) INTO source_count
            FROM post_claim_sources
            WHERE post_claim_id = OLD.post_claim_id;

            IF source_count < 1 THEN
                RAISE EXCEPTION
                    'Every factual claim must reference at least one source fact.';
            END IF;
            RETURN NULL;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_post_claim_sources_require_source
        AFTER DELETE ON post_claim_sources
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION validate_claim_source_delete()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_generated_image()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            run_type varchar(20);
        BEGIN
            SELECT generation_type INTO run_type
            FROM generation_runs
            WHERE id = NEW.generation_run_id;

            IF run_type <> 'image' THEN
                RAISE EXCEPTION
                    'Generated images require an image generation run.';
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_generated_images_validate
        BEFORE INSERT OR UPDATE ON generated_images
        FOR EACH ROW
        EXECUTE FUNCTION validate_generated_image()
        """
    )

    op.execute(
        """
        CREATE FUNCTION validate_saved_content()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            post_status varchar(20);
            image_status varchar(20);
            image_safety varchar(20);
        BEGIN
            SELECT status INTO post_status
            FROM generated_posts
            WHERE id = NEW.generated_post_id;

            IF post_status = 'deleted' THEN
                RAISE EXCEPTION 'Deleted posts cannot be saved.';
            END IF;

            IF NEW.selected_image_id IS NOT NULL THEN
                SELECT status, safety_status
                INTO image_status, image_safety
                FROM generated_images
                WHERE id = NEW.selected_image_id;

                IF image_status <> 'available'
                   OR image_safety <> 'approved' THEN
                    RAISE EXCEPTION
                        'Only available and approved images can be saved.';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_saved_content_validate
        BEFORE INSERT OR UPDATE ON saved_content_items
        FOR EACH ROW
        EXECUTE FUNCTION validate_saved_content()
        """
    )


def downgrade() -> None:
    """Remove the NFA-20 MVP schema in reverse dependency order."""

    op.drop_constraint(
        "fk_articles_current_snapshot",
        "articles",
        type_="foreignkey",
    )

    for table in (
        "saved_content_items",
        "generated_images",
        "post_claim_sources",
        "post_claims",
        "post_version_hashtags",
        "post_versions",
        "generation_facts",
        "generation_runs",
        "generated_posts",
        "article_snapshots",
        "articles",
        "source_profiles",
        "sessions",
        "users",
    ):
        op.drop_table(table)

    for function_name in (
        "validate_saved_content",
        "validate_generated_image",
        "validate_claim_source_delete",
        "validate_new_claim_has_source",
        "validate_claim_source",
        "validate_changed_post_hashtags",
        "validate_new_post_version_hashtags",
        "validate_post_version",
        "validate_generation_fact",
        "validate_generated_post_snapshot",
        "set_updated_at",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function_name}()")
