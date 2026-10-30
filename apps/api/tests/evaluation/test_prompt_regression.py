"""NFA-44 property-based prompt-version regression comparisons."""

import pytest

from app.evaluation import EvaluationDimension, GenerationEvaluator
from app.evaluation.regression import compare_prompt_versions
from app.models.generation_preferences import LinkedInGenerationPreferences
from tests.support.generation_evaluation import (
    article_record,
    generation_case,
    source_reference,
)


def report(*, prompt_version: str, draft: str, case_id: str = "prompt-comparison"):
    case = generation_case("grounded-professional-short")
    record = article_record(case.article_fixture)
    return GenerationEvaluator().evaluate(
        case_id=case_id,
        draft=draft,
        article_id=record.article_id,
        source_reference=source_reference(record),
        article=record.article,
        preferences=LinkedInGenerationPreferences(
            tone=case.tone,
            post_length=case.length,
        ),
        prompt_version=prompt_version,
        model_identifier="mock-openai-model",
    )


def test_prompt_comparison_detects_property_regression_not_wording_change() -> None:
    baseline_case = generation_case("grounded-professional-short")
    baseline = report(
        prompt_version="linkedin_post_v1",
        draft=baseline_case.draft,
    )
    candidate = report(
        prompt_version="linkedin_post_v2",
        draft="A fictional manufacturer tested a platform. Human review remains required.",
    )

    comparison = compare_prompt_versions(baseline, candidate)

    assert comparison.regression_detected is True
    assert EvaluationDimension.LENGTH_COMPLIANCE in comparison.regressed_dimensions
    assert comparison.candidate_passed is False
    assert comparison.score_delta < 0


def test_comparison_requires_the_same_case_and_different_prompt_versions() -> None:
    case = generation_case("grounded-professional-short")
    baseline = report(prompt_version="linkedin_post_v1", draft=case.draft)

    with pytest.raises(ValueError, match="same evaluation case"):
        compare_prompt_versions(
            baseline,
            report(
                prompt_version="linkedin_post_v2",
                draft=case.draft,
                case_id="different-case",
            ),
        )
    with pytest.raises(ValueError, match="different prompt versions"):
        compare_prompt_versions(
            baseline,
            report(prompt_version="linkedin_post_v1", draft=case.draft),
        )
