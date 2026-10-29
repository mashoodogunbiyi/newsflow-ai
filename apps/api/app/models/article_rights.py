"""Validated provenance, rights-policy, and permission-decision models."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RightsVerificationStatus(str, Enum):
    """Whether the current permissions have a trusted decision."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    REVOKED = "revoked"


class ArticleUseOperation(str, Enum):
    """Rights-sensitive actions supported by the application."""

    DISPLAY_METADATA = "display_metadata"
    STORE_METADATA = "store_metadata"
    USE_FOR_AI_GENERATION = "use_for_ai_generation"
    EXPORT_SOURCE_INFORMATION = "export_source_information"
    RETAIN_ARTICLE = "retain_article"


class RightsDecisionReason(str, Enum):
    """Safe explanation for a permission decision."""

    PERMITTED = "permitted"
    MISSING_RIGHTS = "missing_rights"
    UNVERIFIED_RIGHTS = "unverified_rights"
    REVOKED_RIGHTS = "revoked_rights"
    EXPIRED_RIGHTS = "expired_rights"
    SOURCE_DISABLED = "source_disabled"
    OPERATION_RESTRICTED = "operation_restricted"
    ATTRIBUTION_INCOMPLETE = "attribution_incomplete"


def _aware_utc(value: datetime | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone.")
    return value.astimezone(UTC)


class ArticleRightsPolicy(BaseModel):
    """One validated and versionable article rights decision."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    verification_status: RightsVerificationStatus
    storage_allowed: bool
    display_allowed: bool
    ai_processing_allowed: bool
    derivative_output_allowed: bool
    redistribution_allowed: bool
    attribution_required: bool
    attribution_text: str | None = Field(default=None, max_length=500)
    retention_rule: str = Field(min_length=1, max_length=200)
    retention_expires_at: datetime | None = None
    authorisation_reference: str = Field(min_length=1, max_length=100)
    source_contract_version: str = Field(min_length=1, max_length=20)
    rights_last_verified_at: datetime | None = None
    effective_from: datetime

    @field_validator(
        "retention_expires_at",
        "rights_last_verified_at",
        "effective_from",
    )
    @classmethod
    def validate_timestamp(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        field_name = getattr(info, "field_name", "timestamp")
        return _aware_utc(value, field_name)

    @model_validator(mode="after")
    def validate_policy_relationships(self) -> "ArticleRightsPolicy":
        permissions = (
            self.storage_allowed,
            self.display_allowed,
            self.ai_processing_allowed,
            self.derivative_output_allowed,
            self.redistribution_allowed,
        )
        if (
            self.verification_status == RightsVerificationStatus.VERIFIED
            and self.rights_last_verified_at is None
        ):
            raise ValueError("Verified rights require a verification timestamp.")
        if self.verification_status != RightsVerificationStatus.VERIFIED and any(
            permissions
        ):
            raise ValueError("Unverified or revoked rights must deny every operation.")
        if self.derivative_output_allowed and not self.ai_processing_allowed:
            raise ValueError("Derivative output requires AI-processing permission.")
        if self.attribution_required and not self.attribution_text:
            raise ValueError("Required attribution must include approved text.")
        if (
            self.retention_expires_at is not None
            and self.retention_expires_at <= self.effective_from
        ):
            raise ValueError("Retention expiry must follow the effective time.")
        return self


class ArticleRightsRecord(ArticleRightsPolicy):
    """Persisted rights version returned without confidential agreement text."""

    id: UUID
    article_id: UUID
    version_number: int = Field(ge=1)
    superseded_at: datetime | None = None

    @field_validator("superseded_at")
    @classmethod
    def validate_superseded_at(cls, value: datetime | None) -> datetime | None:
        return _aware_utc(value, "superseded_at")


class ArticleProvenanceRecord(BaseModel):
    """Non-secret trace of one article retrieval and ingestion decision."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: UUID
    article_id: UUID
    source_profile_id: UUID
    provider_id: str = Field(min_length=1, max_length=100)
    external_article_id: str = Field(min_length=1, max_length=200)
    canonical_url: str = Field(min_length=1, max_length=2048)
    published_at: datetime
    retrieved_at: datetime
    source_integration_id: str = Field(min_length=1, max_length=100)
    source_contract_version: str = Field(min_length=1, max_length=20)
    authorisation_reference: str = Field(min_length=1, max_length=100)
    ingestion_action: str = Field(pattern="^(created|updated|skipped)$")

    @field_validator("published_at", "retrieved_at")
    @classmethod
    def validate_provenance_time(
        cls,
        value: datetime,
        info: object,
    ) -> datetime:
        field_name = getattr(info, "field_name", "timestamp")
        result = _aware_utc(value, field_name)
        assert result is not None
        return result


class ArticleRightsDecision(BaseModel):
    """Fail-closed result used before a rights-sensitive operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    article_id: UUID
    operation: ArticleUseOperation
    allowed: bool
    reason: RightsDecisionReason
    rights_version_id: UUID | None = None
    attribution_required: bool = False
    attribution_text: str | None = None
