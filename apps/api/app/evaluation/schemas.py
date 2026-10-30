"""Strict, explainable result models for LinkedIn generation evaluation."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluationDimension(str, Enum):
    """Measurable properties evaluated for every generated draft."""

    STRUCTURE = "structure"
    FACTUAL_GROUNDING = "factual_grounding"
    SOURCE_ATTRIBUTION = "source_attribution"
    TONE_COMPLIANCE = "tone_compliance"
    LENGTH_COMPLIANCE = "length_compliance"
    WRITING_QUALITY = "writing_quality"
    SAFETY = "safety"


class EvaluationFindingSeverity(str, Enum):
    """Finding levels used to distinguish review from hard failure."""

    REVIEW = "review"
    BLOCKING = "blocking"


class EvaluationFinding(BaseModel):
    """One safe finding without article or generated-content excerpts."""

    code: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_]+$")
    severity: EvaluationFindingSeverity
    message: str = Field(min_length=1, max_length=240)

    model_config = ConfigDict(extra="forbid", frozen=True)


class CriterionEvaluation(BaseModel):
    """Score and pass decision for one documented quality dimension."""

    dimension: EvaluationDimension
    score: int = Field(ge=1, le=5)
    passed: bool
    weight: float = Field(gt=0, le=1)
    findings: tuple[EvaluationFinding, ...] = ()

    @model_validator(mode="after")
    def decision_matches_findings(self) -> "CriterionEvaluation":
        if self.passed and any(
            item.severity == EvaluationFindingSeverity.BLOCKING
            for item in self.findings
        ):
            raise ValueError("A passing criterion cannot contain a blocking finding.")
        if self.score == 5 and self.findings:
            raise ValueError("An excellent criterion cannot contain findings.")
        return self

    model_config = ConfigDict(extra="forbid", frozen=True)


class EvaluationThresholds(BaseModel):
    """Versioned pass thresholds used by deterministic evaluation."""

    minimum_overall_score: float = Field(default=4.0, ge=1, le=5)
    minimum_criterion_score: int = Field(default=3, ge=1, le=5)
    minimum_sentences: int = Field(default=2, ge=1, le=20)
    maximum_average_sentence_words: int = Field(default=35, ge=10, le=100)

    model_config = ConfigDict(extra="forbid", frozen=True)


class GenerationEvaluationReport(BaseModel):
    """Deterministic report for one synthetic or permitted generation case."""

    evaluation_version: Literal["linkedin_generation_eval_v1"] = (
        "linkedin_generation_eval_v1"
    )
    case_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    prompt_version: str = Field(pattern=r"^linkedin_post_v[1-9][0-9]*$")
    model_identifier: str = Field(min_length=1, max_length=200)
    overall_score: float = Field(ge=1, le=5)
    passing_score: float = Field(ge=1, le=5)
    passed: bool
    criteria: tuple[CriterionEvaluation, ...]
    human_review_required: Literal[True] = True
    limitations: tuple[str, ...] = (
        "Automated evaluation cannot prove factual accuracy.",
        "Human review is required before publication.",
    )

    @model_validator(mode="after")
    def validate_report(self) -> "GenerationEvaluationReport":
        dimensions = [item.dimension for item in self.criteria]
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("An evaluation report cannot repeat a dimension.")
        if set(dimensions) != set(EvaluationDimension):
            raise ValueError("An evaluation report requires every dimension.")
        has_blocker = any(
            finding.severity == EvaluationFindingSeverity.BLOCKING
            for item in self.criteria
            for finding in item.findings
        )
        if self.passed and (has_blocker or self.overall_score < self.passing_score):
            raise ValueError("A passing report must meet its score and safety gates.")
        return self

    model_config = ConfigDict(extra="forbid", frozen=True)


class DimensionScoreChange(BaseModel):
    """Score delta for one dimension between prompt versions."""

    dimension: EvaluationDimension
    baseline_score: int = Field(ge=1, le=5)
    candidate_score: int = Field(ge=1, le=5)
    delta: int = Field(ge=-4, le=4)

    model_config = ConfigDict(extra="forbid", frozen=True)


class PromptRegressionComparison(BaseModel):
    """Property-based comparison that never expects identical model wording."""

    case_id: str
    baseline_prompt_version: str
    candidate_prompt_version: str
    baseline_overall_score: float = Field(ge=1, le=5)
    candidate_overall_score: float = Field(ge=1, le=5)
    score_delta: float = Field(ge=-4, le=4)
    changes: tuple[DimensionScoreChange, ...]
    regressed_dimensions: tuple[EvaluationDimension, ...]
    improved_dimensions: tuple[EvaluationDimension, ...]
    candidate_passed: bool
    regression_detected: bool

    model_config = ConfigDict(extra="forbid", frozen=True)
