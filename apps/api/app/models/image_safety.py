"""Structured inputs, decisions, and safe records for image safety."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from app.models.image_prompt import ImagePromptResult


class SensitiveNewsCategory(str, Enum):
    """Deterministic policy categories that require additional safeguards."""

    ARMED_CONFLICT = "armed_conflict"
    TERRORISM = "terrorism"
    NATURAL_DISASTER = "natural_disaster"
    DEATH_OR_SERIOUS_INJURY = "death_or_serious_injury"
    PUBLIC_HEALTH_EMERGENCY = "public_health_emergency"
    ELECTION_OR_POLITICAL_EVENT = "election_or_political_event"
    CRIMINAL_ALLEGATION = "criminal_allegation"
    IDENTIFIABLE_PERSON_SENSITIVE_EVENT = "identifiable_person_sensitive_event"
    UNCERTAIN = "uncertain"
    NON_SENSITIVE = "non_sensitive"


class ImageSafetyDecision(str, Enum):
    """Consistent outcome applied before an image provider can be called."""

    ALLOWED = "allowed"
    ALLOWED_WITH_RESTRICTIONS = "allowed_with_restrictions"
    REJECTED = "rejected"
    REVIEW_REQUIRED = "review_required"


class ImageSafetyReasonCode(str, Enum):
    """Stable content-free explanation for one policy outcome."""

    ORDINARY_CONCEPTUAL_TOPIC = "ordinary_conceptual_topic"
    SENSITIVE_REAL_WORLD_EVENT = "sensitive_real_world_event"
    DOCUMENTARY_FABRICATION_REQUEST = "documentary_fabrication_request"
    IDENTIFIABLE_PERSON_MISREPRESENTATION = "identifiable_person_misrepresentation"
    SAFETY_OVERRIDE_ATTEMPT = "safety_override_attempt"
    CLASSIFICATION_UNCERTAIN = "classification_uncertain"
    PROVIDER_SAFETY_CONTROLS_UNAVAILABLE = "provider_safety_controls_unavailable"


class RequiredImageTreatment(str, Enum):
    """Application-enforced visual treatment, not a frontend preference."""

    CONCEPTUAL_ILLUSTRATION = "conceptual_illustration"


class ImageProviderSafetyCapabilities(BaseModel):
    """Trusted backend configuration for one future image provider."""

    prompt_moderation_available: bool
    output_moderation_available: bool
    strict_safety_level_available: bool
    content_credentials_available: bool

    model_config = ConfigDict(extra="forbid", frozen=True)


class ImageProviderSafetyControls(BaseModel):
    """Provider controls that a later adapter must apply to this request."""

    prompt_moderation_enabled: bool
    output_moderation_enabled: bool
    strict_safety_level_enabled: bool
    content_credentials_requested: bool

    model_config = ConfigDict(extra="forbid", frozen=True)


class ImageSafetyRequest(BaseModel):
    """Internal evaluation input with no safety-override parameters."""

    prompt: ImagePromptResult
    user_request: SecretStr | None = Field(default=None, max_length=2_000)

    model_config = ConfigDict(extra="forbid", frozen=True)


class ImageSafetyResult(BaseModel):
    """Complete internal policy decision returned before provider access."""

    evaluation_id: UUID
    policy_version: str = Field(pattern=r"^image_safety_v[1-9][0-9]*$")
    article_id: UUID
    generation_id: UUID | None = None
    decision: ImageSafetyDecision
    reason_code: ImageSafetyReasonCode
    reason_message: str = Field(min_length=1, max_length=300)
    sensitive_categories: tuple[SensitiveNewsCategory, ...]
    provider_call_allowed: bool
    required_treatment: RequiredImageTreatment
    photorealism_allowed: Literal[False] = False
    documentary_use_allowed: Literal[False] = False
    ai_generated_designation: Literal["AI-generated illustration"] = (
        "AI-generated illustration"
    )
    review_required: Literal[True] = True
    conceptual_alternative_available: bool
    provider_controls: ImageProviderSafetyControls
    evaluated_at: datetime

    @model_validator(mode="after")
    def validate_provider_gate(self) -> "ImageSafetyResult":
        expected = self.decision in {
            ImageSafetyDecision.ALLOWED,
            ImageSafetyDecision.ALLOWED_WITH_RESTRICTIONS,
        }
        if self.provider_call_allowed != expected:
            raise ValueError("Provider-call gate must match the safety decision.")
        return self

    model_config = ConfigDict(extra="forbid", frozen=True)


class ImageSafetyDecisionRecord(BaseModel):
    """Content-free metadata suitable for a future persistence adapter."""

    evaluation_id: UUID
    policy_version: str = Field(pattern=r"^image_safety_v[1-9][0-9]*$")
    article_id: UUID
    generation_id: UUID | None = None
    decision: ImageSafetyDecision
    reason_code: ImageSafetyReasonCode
    sensitive_categories: tuple[SensitiveNewsCategory, ...]
    provider_call_allowed: bool
    review_required: Literal[True]
    photorealism_allowed: Literal[False]
    ai_generated_designation: Literal["AI-generated illustration"]
    evaluated_at: datetime

    model_config = ConfigDict(extra="forbid", frozen=True)
