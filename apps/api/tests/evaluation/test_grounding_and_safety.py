"""NFA-44 grounding, source-integrity, rights, and injection evaluations."""

from uuid import uuid4

from app.evaluation import EvaluationDimension, GenerationEvaluator
from app.models.generation_preferences import LinkedInGenerationPreferences
from tests.support.generation_evaluation import (
    article_record,
    generation_case,
    source_reference,
)


def evaluate(case_id: str):
    case = generation_case(case_id)
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


def finding_codes(report: object, dimension: EvaluationDimension) -> set[str]:
    selected = next(item for item in report.criteria if item.dimension == dimension)
    return {finding.code for finding in selected.findings}


def test_unsupported_numerical_claim_is_flagged() -> None:
    report = evaluate("unsupported-statistic")

    assert report.passed is False
    assert "unsupported_numerical_claim" in finding_codes(
        report,
        EvaluationDimension.SAFETY,
    )


def test_fabricated_quotation_is_blocking() -> None:
    report = evaluate("fabricated-quotation")

    assert report.passed is False
    assert "unsafe_grounding_output" in finding_codes(
        report,
        EvaluationDimension.SAFETY,
    )


def test_source_reference_identifier_and_url_must_match_trusted_record() -> None:
    case = generation_case("grounded-professional-short")
    record = article_record(case.article_fixture)
    untrusted = source_reference(record).model_copy(update={"article_id": uuid4()})

    report = GenerationEvaluator().evaluate(
        case_id="source-reference-mismatch",
        draft=case.draft,
        article_id=record.article_id,
        source_reference=untrusted,
        article=record.article,
        preferences=LinkedInGenerationPreferences(
            tone=case.tone,
            post_length=case.length,
        ),
        prompt_version=case.prompt_version,
        model_identifier=case.model_identifier,
    )

    assert report.passed is False
    assert "source_reference_mismatch" in finding_codes(
        report,
        EvaluationDimension.SOURCE_ATTRIBUTION,
    )


def test_insufficient_source_information_cannot_receive_a_passing_score() -> None:
    record = article_record("insufficient-context")

    report = GenerationEvaluator().evaluate(
        case_id="insufficient-source",
        draft="A fictional announcement described a major successful programme with broad results.",
        article_id=record.article_id,
        source_reference=source_reference(record),
        article=record.article,
        preferences=LinkedInGenerationPreferences(post_length="short"),
        prompt_version="linkedin_post_v1",
        model_identifier="mock-openai-model",
    )

    assert report.passed is False
    assert "grounding_rejected" in finding_codes(
        report,
        EvaluationDimension.FACTUAL_GROUNDING,
    )


def test_prompt_injection_output_is_blocked() -> None:
    report = evaluate("prompt-injection-followed")

    assert report.passed is False
    assert "prompt_injection_followed" in finding_codes(
        report,
        EvaluationDimension.SAFETY,
    )


def test_restricted_article_information_is_never_approved_for_generation() -> None:
    record = article_record("restricted-article")

    report = GenerationEvaluator().evaluate(
        case_id="restricted-source",
        draft="A generated post must not be produced from restricted information.",
        article_id=record.article_id,
        source_reference=source_reference(record),
        article=record.article,
        preferences=LinkedInGenerationPreferences(post_length="short"),
        prompt_version="linkedin_post_v1",
        model_identifier="mock-openai-model",
    )

    assert report.passed is False
    assert "restricted_article_information" in finding_codes(
        report,
        EvaluationDimension.SAFETY,
    )
