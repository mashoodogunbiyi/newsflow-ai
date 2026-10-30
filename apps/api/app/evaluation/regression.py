"""Prompt-version comparison for property-based regression evaluation."""

from app.evaluation.schemas import (
    DimensionScoreChange,
    EvaluationDimension,
    GenerationEvaluationReport,
    PromptRegressionComparison,
)


def compare_prompt_versions(
    baseline: GenerationEvaluationReport,
    candidate: GenerationEvaluationReport,
) -> PromptRegressionComparison:
    """Compare quality properties without requiring identical generated wording."""

    if baseline.case_id != candidate.case_id:
        raise ValueError("Prompt comparisons require the same evaluation case.")
    if baseline.prompt_version == candidate.prompt_version:
        raise ValueError("Prompt comparisons require different prompt versions.")

    baseline_scores = {item.dimension: item.score for item in baseline.criteria}
    candidate_scores = {item.dimension: item.score for item in candidate.criteria}
    changes = tuple(
        DimensionScoreChange(
            dimension=dimension,
            baseline_score=baseline_scores[dimension],
            candidate_score=candidate_scores[dimension],
            delta=candidate_scores[dimension] - baseline_scores[dimension],
        )
        for dimension in EvaluationDimension
    )
    regressed = tuple(item.dimension for item in changes if item.delta < 0)
    improved = tuple(item.dimension for item in changes if item.delta > 0)
    regression_detected = bool(regressed) or (baseline.passed and not candidate.passed)
    return PromptRegressionComparison(
        case_id=baseline.case_id,
        baseline_prompt_version=baseline.prompt_version,
        candidate_prompt_version=candidate.prompt_version,
        baseline_overall_score=baseline.overall_score,
        candidate_overall_score=candidate.overall_score,
        score_delta=round(candidate.overall_score - baseline.overall_score, 2),
        changes=changes,
        regressed_dimensions=regressed,
        improved_dimensions=improved,
        candidate_passed=candidate.passed,
        regression_detected=regression_detected,
    )
