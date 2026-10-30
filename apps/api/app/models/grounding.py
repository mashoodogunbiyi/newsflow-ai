"""Safe, structured results from automated factual-grounding checks."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GroundingStatus(str, Enum):
    """Automated decision labels that never claim factual verification."""

    PASSED_AUTOMATED_CHECKS = "passed_automated_checks"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


class GroundingWarningCode(str, Enum):
    """Stable, content-free warning codes safe for storage and responses."""

    EMPTY_DRAFT = "empty_draft"
    SOURCE_REFERENCE_MISMATCH = "source_reference_mismatch"
    INSUFFICIENT_GROUNDING_CONTEXT = "insufficient_grounding_context"
    UNSUPPORTED_NUMERICAL_CLAIM = "unsupported_numerical_claim"
    UNSUPPORTED_QUOTATION = "unsupported_quotation"
    UNSUPPORTED_DATE_CLAIM = "unsupported_date_claim"
    UNSUPPORTED_NAMED_ENTITY = "unsupported_named_entity"
    UNSUPPORTED_FACTUAL_ASSERTION = "unsupported_factual_assertion"
    LEGACY_UNVALIDATED = "legacy_unvalidated"


class GroundingWarning(BaseModel):
    """One safe warning without source text or generated claim excerpts."""

    code: GroundingWarningCode
    category: Literal[
        "structure",
        "source_reference",
        "insufficient_context",
        "unsupported_claim",
        "legacy_data",
    ]
    severity: Literal["review", "blocking"]
    message: str = Field(min_length=1, max_length=240)

    model_config = ConfigDict(extra="forbid", frozen=True)


class GroundingResult(BaseModel):
    """Persistable outcome of deterministic automated checks."""

    status: GroundingStatus
    warnings: tuple[GroundingWarning, ...] = ()
    policy_version: Literal["grounding_v1"] = "grounding_v1"
    checked_claim_count: int = Field(ge=0)
    human_review_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_decision(self) -> "GroundingResult":
        if self.status == GroundingStatus.PASSED_AUTOMATED_CHECKS and self.warnings:
            raise ValueError("Passed automated checks cannot contain warnings.")
        if self.status != GroundingStatus.PASSED_AUTOMATED_CHECKS and not self.warnings:
            raise ValueError("Review and rejection decisions require a warning.")
        if self.status == GroundingStatus.REJECTED and not any(
            warning.severity == "blocking" for warning in self.warnings
        ):
            raise ValueError("Rejected decisions require a blocking warning.")
        return self

    @classmethod
    def legacy_unvalidated(cls) -> "GroundingResult":
        """Represent pre-NFA-42 rows conservatively when they are retrieved."""

        return cls(
            status=GroundingStatus.REVIEW_REQUIRED,
            warnings=(
                GroundingWarning(
                    code=GroundingWarningCode.LEGACY_UNVALIDATED,
                    category="legacy_data",
                    severity="review",
                    message=(
                        "This draft predates automated grounding checks and requires "
                        "manual source review."
                    ),
                ),
            ),
            checked_claim_count=0,
        )

    model_config = ConfigDict(extra="forbid", frozen=True)
