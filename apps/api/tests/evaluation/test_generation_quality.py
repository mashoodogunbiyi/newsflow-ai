"""NFA-44 structure, tone, length, quality, and dataset evaluation tests."""

import pytest

from app.evaluation import EvaluationDimension, GenerationEvaluator
from app.models.generation_preferences import (
    LinkedInGenerationPreferences,
    LinkedInPostLength,
)
from app.prompts.linkedin_post import LINKEDIN_LENGTH_SPECIFICATIONS
from tests.support.generation_evaluation import (
    article_record,
    assert_dataset_contains_no_live_content,
    load_article_dataset,
    load_generation_dataset,
    source_reference,
)


def criterion(report: object, dimension: EvaluationDimension):
    return next(item for item in report.criteria if item.dimension == dimension)


def evaluate_case(case: object):
    record = article_record(case.article_fixture)
    return GenerationEvaluator().evaluate(
        case_id=case.case_id,
        draft=case.draft,
        article_id=record.article_id,
        source_reference=source_reference(record),
        article=record.article,
        preferences=LinkedInGenerationPreferences(
            tone=case.tone,
            post_length=case.length,
        ),
        prompt_version=case.prompt_version,
        model_identifier=case.model_identifier,
    )


def test_synthetic_dataset_covers_required_subjects_and_uses_no_live_news() -> None:
    dataset = load_article_dataset()
    identifiers = {item.evaluation_id for item in dataset.articles}

    assert {
        "technology-efficiency",
        "ai-support-tool",
        "business-training-hub",
        "science-sensor-study",
        "healthcare-scheduling",
        "economic-training-index",
        "insufficient-context",
        "prompt-injection",
        "restricted-article",
    } <= identifiers
    assert_dataset_contains_no_live_content()


def test_mocked_regression_outputs_produce_the_expected_pass_decisions() -> None:
    dataset = load_generation_dataset()

    decisions = {case.case_id: evaluate_case(case).passed for case in dataset.cases}

    assert decisions == {case.case_id: case.expected_pass for case in dataset.cases}


def test_professional_tone_flags_informal_and_exaggerated_markers() -> None:
    case = load_generation_dataset().cases[0]
    report = evaluate_case(
        case.model_copy(
            update={
                "case_id": "unprofessional-tone",
                "draft": case.draft.replace(
                    "A fictional manufacturer",
                    "OMG!! A fictional manufacturer",
                ),
            }
        )
    )

    result = criterion(report, EvaluationDimension.TONE_COMPLIANCE)
    assert result.score == 2
    assert result.passed is False
    assert result.findings[0].code == "professional_tone_not_met"


def test_empty_draft_fails_structural_validation() -> None:
    case = load_generation_dataset().cases[0]
    report = evaluate_case(
        case.model_copy(
            update={
                "case_id": "empty-structured-output",
                "draft": "   ",
            }
        )
    )

    result = criterion(report, EvaluationDimension.STRUCTURE)
    assert report.passed is False
    assert result.score == 1
    assert result.findings[0].code == "empty_draft"


@pytest.mark.parametrize("post_length", list(LinkedInPostLength))
def test_every_configured_length_uses_the_versioned_word_range(
    post_length: LinkedInPostLength,
) -> None:
    case = load_generation_dataset().cases[0]
    specification = LINKEDIN_LENGTH_SPECIFICATIONS[post_length]
    report = evaluate_case(
        case.model_copy(
            update={
                "case_id": f"{post_length.value}-length-boundary",
                "length": post_length,
                "draft": " ".join(
                    f"synthetic{number}"
                    for number in range(specification.minimum_words)
                ),
            }
        )
    )

    result = criterion(report, EvaluationDimension.LENGTH_COMPLIANCE)
    assert result.score == 5
    assert result.passed is True


def test_length_is_measured_against_the_versioned_prompt_range() -> None:
    case = load_generation_dataset().cases[0]
    report = evaluate_case(
        case.model_copy(
            update={
                "case_id": "short-post-too-short",
                "draft": "A fictional manufacturer tested a platform. Human review remains required.",
            }
        )
    )

    result = criterion(report, EvaluationDimension.LENGTH_COMPLIANCE)
    assert result.score == 1
    assert result.passed is False
    assert result.findings[0].code == "length_outside_target"


def test_report_has_all_weighted_dimensions_and_requires_human_review() -> None:
    report = evaluate_case(load_generation_dataset().cases[0])

    assert {item.dimension for item in report.criteria} == set(EvaluationDimension)
    assert round(sum(item.weight for item in report.criteria), 2) == 1.0
    assert report.passing_score == 4.0
    assert report.human_review_required is True
    assert "cannot prove factual accuracy" in report.limitations[0]
