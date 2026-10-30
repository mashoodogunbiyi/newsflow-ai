"""SQLAlchemy mappings for tables used by the application layer."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base for migration-backed SQLAlchemy table mappings."""


class UserTable(Base):
    """Application mapping for the migration-owned users table."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'active'"),
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'user'"),
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class SessionTable(Base):
    """Application mapping for server-managed authenticated sessions."""

    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        unique=True,
    )
    csrf_token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class SourceProfileTable(Base):
    """Application mapping for an approved source configuration."""

    __tablename__ = "source_profiles"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    profile_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(20), nullable=False)
    profile_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    authorisation_decision_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    access_method: Mapped[str] = mapped_column(String(50), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ArticleTable(Base):
    """Stable article identity whose mutable data lives in snapshots."""

    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint(
            "source_profile_id",
            "source_item_id",
            name="uq_articles_source_identity",
        ),
        UniqueConstraint("canonical_url", name="uq_articles_canonical_url"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_profile_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("source_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_item_id: Mapped[str] = mapped_column(String(200), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'active'")
    )
    current_snapshot_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    current_rights_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ArticleSnapshotTable(Base):
    """Immutable permitted article data for one accepted source version."""

    __tablename__ = "article_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "snapshot_number",
            name="uq_article_snapshot_number",
        ),
        UniqueConstraint(
            "id",
            "article_id",
            name="uq_article_snapshots_id_article",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    article_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_version: Mapped[str] = mapped_column(String(20), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    publication_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    permitted_content_status: Mapped[str] = mapped_column(String(20), nullable=False)
    permitted_content_type: Mapped[str] = mapped_column(String(40), nullable=False)
    permitted_content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    display_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ai_processing_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    derivative_output_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rights_decision_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    access_method: Mapped[str] = mapped_column(String(50), nullable=False)
    retention_rule: Mapped[str] = mapped_column(String(100), nullable=False)
    rights_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attribution_display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    attribution_text: Mapped[str] = mapped_column(String(500), nullable=False)
    byline: Mapped[str | None] = mapped_column(String(300), nullable=True)
    copyright_notice: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    content_fingerprint: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ArticleProvenanceEventTable(Base):
    """Immutable evidence of one authorised article retrieval or ingestion."""

    __tablename__ = "article_provenance_events"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    article_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_profile_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("source_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_item_id: Mapped[str] = mapped_column(String(200), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    publication_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source_integration_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    source_contract_version: Mapped[str] = mapped_column(String(20), nullable=False)
    authorisation_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    ingestion_action: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ArticleRightsVersionTable(Base):
    """Immutable version of the current permissions for one article."""

    __tablename__ = "article_rights_versions"
    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "version_number",
            name="uq_article_rights_version_number",
        ),
        UniqueConstraint(
            "id",
            "article_id",
            name="uq_article_rights_id_article",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    article_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    display_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ai_processing_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    derivative_output_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    redistribution_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attribution_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attribution_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retention_rule: Mapped[str] = mapped_column(String(200), nullable=False)
    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    authorisation_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    source_contract_version: Mapped[str] = mapped_column(String(20), nullable=False)
    rights_last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ArticleSyncCheckpointTable(Base):
    """Durable incremental and schedule position for one provider."""

    __tablename__ = "article_sync_checkpoints"

    provider_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    last_successful_publication_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_successful_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ArticleSyncJobTable(Base):
    """Durable status, lease, and statistics for one sync attempt."""

    __tablename__ = "article_sync_jobs"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    provider_id: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    checkpoint_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checkpoint_candidate: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    articles_retrieved: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    articles_created: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    articles_updated: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    articles_skipped: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    articles_rejected: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    provider_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    provider_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    provider_duration_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    failed_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class GeneratedPostTable(Base):
    """Application mapping for a user-owned generated post."""

    __tablename__ = "generated_posts"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    article_snapshot_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("article_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'draft'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class GenerationRunTable(Base):
    """Application mapping for one bounded AI generation attempt."""

    __tablename__ = "generation_runs"
    __table_args__ = (
        CheckConstraint(
            "grounding_status IS NULL OR grounding_status IN "
            "('passed_automated_checks', 'review_required', 'rejected')",
            name="ck_generation_runs_grounding_status",
        ),
        CheckConstraint(
            "grounding_checked_claims IS NULL OR grounding_checked_claims >= 0",
            name="ck_generation_runs_grounding_checked_claims",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    generated_post_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("generated_posts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    article_rights_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("article_rights_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    generation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_template_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safe_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    grounding_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    grounding_policy_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    grounding_warnings: Mapped[list[dict[str, str]] | None] = mapped_column(
        JSONB, nullable=True
    )
    grounding_checked_claims: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class GenerationUsageEventTable(Base):
    """Content-free operational evidence for one provider-bound attempt."""

    __tablename__ = "generation_usage_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('started', 'succeeded', 'failed')",
            name="ck_generation_usage_events_status",
        ),
        CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="ck_generation_usage_events_input_tokens",
        ),
        CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="ck_generation_usage_events_output_tokens",
        ),
        CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="ck_generation_usage_events_total_tokens",
        ),
        CheckConstraint(
            "(status = 'started' AND completed_at IS NULL) OR "
            "(status IN ('succeeded', 'failed') AND completed_at IS NOT NULL)",
            name="ck_generation_usage_events_completion",
        ),
        CheckConstraint(
            "(status = 'failed' AND error_category IS NOT NULL) OR "
            "(status != 'failed' AND error_category IS NULL)",
            name="ck_generation_usage_events_error_category",
        ),
        CheckConstraint(
            "(status = 'succeeded' AND generation_run_id IS NOT NULL) OR "
            "status != 'succeeded'",
            name="ck_generation_usage_events_generation_run",
        ),
        Index(
            "uq_generation_usage_events_active_request",
            "user_id",
            "request_fingerprint",
            unique=True,
            postgresql_where=text("status = 'started'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    generation_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("generation_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    model_identifier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class GenerationAuditEventTable(Base):
    """Content-free lifecycle event for one correlated generation request."""

    __tablename__ = "generation_audit_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'generation_started', 'generation_rights_verified', "
            "'generation_rights_denied', 'generation_usage_rejected', "
            "'generation_validation_passed', 'generation_validation_failed', "
            "'generation_completed', 'generation_failed')",
            name="ck_generation_audit_events_type",
        ),
        CheckConstraint(
            "status IN ('started', 'passed', 'succeeded', 'rejected', 'failed')",
            name="ck_generation_audit_events_status",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_generation_audit_events_duration",
        ),
        Index(
            "ix_generation_audit_events_request_time",
            "generation_request_id",
            "occurred_at",
        ),
        Index(
            "ix_generation_audit_events_user_time",
            "user_id",
            "occurred_at",
        ),
        Index(
            "ix_generation_audit_events_type_time",
            "event_type",
            "occurred_at",
        ),
        Index(
            "ix_generation_audit_events_error_time",
            "error_category",
            "occurred_at",
        ),
        Index("ix_generation_audit_events_occurred_at", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    generation_request_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    article_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    generation_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("generation_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    usage_event_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("generation_usage_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_identifier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rights_decision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(50), nullable=True)


class PostVersionTable(Base):
    """Application mapping for a version of a generated post."""

    __tablename__ = "post_versions"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    generated_post_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("generated_posts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    generation_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("generation_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    previous_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    tone: Mapped[str] = mapped_column(String(30), nullable=False)
    length_option: Mapped[str] = mapped_column(String(20), nullable=False)
    audience: Mapped[str] = mapped_column(String(40), nullable=False)
    hook: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    insight: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_to_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    rendered_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_attribution: Mapped[str] = mapped_column(String(500), nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PostVersionHashtagTable(Base):
    """Application mapping for ordered hashtags attached to a post version."""

    __tablename__ = "post_version_hashtags"

    post_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("post_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    hashtag: Mapped[str] = mapped_column(String(100), nullable=False)


class GeneratedImageTable(Base):
    """Application mapping for an image attached to a generated post."""

    __tablename__ = "generated_images"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    generated_post_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    safety_status: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class SavedContentItemTable(Base):
    """Application mapping for a private content-library item."""

    __tablename__ = "saved_content_items"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    generated_post_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    selected_post_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    selected_image_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    library_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
