"""NFA-42 deterministic factual-grounding validation tests."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from app.models.grounding import (
    GroundingResult,
    GroundingStatus,
    GroundingWarningCode,
)
from app.models.linkedin_generation import (
    LinkedInDraftSourceReference,
    LinkedInModelOutput,
)
from app.providers.fixture_provider import DEFAULT_FIXTURES
from app.providers.models import NewsArticle
from app.providers.normalisation import ArticleNormalisationService
from app.services.generation_validator import GenerationGroundingValidator

ARTICLE_ID = UUID("42000000-0000-4000-8000-000000000001")
RIGHTS_ID = UUID("42000000-0000-4000-8000-000000000002")


def article(**changes: object) -> NewsArticle:
    item = ArticleNormalisationService().normalise(DEFAULT_FIXTURES[0])
    values = item.model_dump(mode="json")
    values.update(changes)
    return NewsArticle.model_validate(values)


def reference(
    item: NewsArticle,
    *,
    article_id: UUID = ARTICLE_ID,
    source_url: str | None = None,
) -> LinkedInDraftSourceReference:
    return LinkedInDraftSourceReference(
        article_id=article_id,
        title=item.title,
        source_name=item.source_name,
        source_url=source_url or str(item.url),
        attribution_text=item.attribution.attribution_text,
        rights_version_id=RIGHTS_ID,
    )


def validate(draft: str, *, item: NewsArticle | None = None):
    selected = item or article()
    return GenerationGroundingValidator().validate(
        draft=draft,
        article_id=ARTICLE_ID,
        source_reference=reference(selected),
        article=selected,
    )


def warning_codes(result: object) -> set[str]:
    return {warning.code.value for warning in result.warnings}


def test_supported_fact_and_explicit_commentary_pass_automated_checks() -> None:
    result = validate(
        "A fictional technology company announced a test platform designed to "
        "reduce energy use. In my view, this may encourage professionals to "
        "consider practical efficiency."
    )

    assert result.status == GroundingStatus.PASSED_AUTOMATED_CHECKS
    assert result.warnings == ()
    assert result.checked_claim_count == 1
    assert result.human_review_required is True


def test_empty_output_is_rejected_and_structured_model_rejects_malformed_data() -> None:
    result = validate("   ")

    assert result.status == GroundingStatus.REJECTED
    assert GroundingWarningCode.EMPTY_DRAFT.value in warning_codes(result)
    with pytest.raises(ValidationError):
        LinkedInModelOutput.model_validate(
            {"status": "ready", "draft": "", "insufficiency_reason": None}
        )
    with pytest.raises(ValidationError):
        LinkedInModelOutput.model_validate(
            {
                "status": "ready",
                "draft": "A draft",
                "insufficiency_reason": None,
                "unexpected": "not allowed",
            }
        )


def test_unsupported_statistic_is_flagged_for_review() -> None:
    result = validate(
        "A fictional technology company announced a platform designed to reduce "
        "energy use by 45%."
    )

    assert result.status == GroundingStatus.REVIEW_REQUIRED
    assert GroundingWarningCode.UNSUPPORTED_NUMERICAL_CLAIM.value in warning_codes(
        result
    )


def test_supported_publication_date_is_not_flagged() -> None:
    result = validate(
        "On October 12, 2026, a fictional technology company announced a test "
        "platform designed to reduce energy use."
    )

    assert GroundingWarningCode.UNSUPPORTED_DATE_CLAIM.value not in warning_codes(
        result
    )


def test_unsupported_date_is_flagged_for_review() -> None:
    result = validate(
        "On November 30, 2026, a fictional technology company announced a test "
        "platform designed to reduce energy use."
    )

    assert result.status == GroundingStatus.REVIEW_REQUIRED
    assert GroundingWarningCode.UNSUPPORTED_DATE_CLAIM.value in warning_codes(result)


def test_fabricated_quotation_is_rejected() -> None:
    result = validate(
        'The fictional technology company said "This platform guarantees success."'
    )

    assert result.status == GroundingStatus.REJECTED
    assert GroundingWarningCode.UNSUPPORTED_QUOTATION.value in warning_codes(result)


def test_source_reference_must_match_trusted_backend_record() -> None:
    selected = article()
    result = GenerationGroundingValidator().validate(
        draft="A fictional company announced an energy-efficient test platform.",
        article_id=ARTICLE_ID,
        source_reference=reference(
            selected,
            source_url="https://example.invalid/untrusted-replacement",
        ),
        article=selected,
    )

    assert result.status == GroundingStatus.REJECTED
    assert GroundingWarningCode.SOURCE_REFERENCE_MISMATCH.value in warning_codes(result)


def test_insufficient_or_restricted_context_is_rejected_without_using_its_text() -> (
    None
):
    insufficient = article(
        description=None,
        permitted_content={
            "status": "available",
            "content_type": "synthetic",
            "text": "Short context.",
            "ai_processing_allowed": True,
            "derivative_output_allowed": True,
        },
    )
    result = validate("A detailed claim not supported here.", item=insufficient)

    assert result.status == GroundingStatus.REJECTED
    assert GroundingWarningCode.INSUFFICIENT_GROUNDING_CONTEXT.value in warning_codes(
        result
    )
    assert "Short context" not in " ".join(
        warning.message for warning in result.warnings
    )

    restricted = article(
        description="Confidential source text must never appear in a warning.",
        permitted_content={
            "status": "not_permitted",
            "content_type": "none",
            "text": None,
            "ai_processing_allowed": False,
            "derivative_output_allowed": False,
        },
    )
    restricted_result = validate(
        "An unsupported draft that cannot use restricted information.",
        item=restricted,
    )
    warning_text = " ".join(warning.message for warning in restricted_result.warnings)

    assert restricted_result.status == GroundingStatus.REJECTED
    assert "Confidential source text" not in warning_text


def test_opinion_is_not_treated_as_a_source_fact() -> None:
    result = validate(
        "In my view, professionals should consider practical efficiency when "
        "exploring responsible technology."
    )

    assert result.status == GroundingStatus.PASSED_AUTOMATED_CHECKS
    assert result.checked_claim_count == 0


def test_unsupported_entity_and_assertion_create_safe_review_warnings() -> None:
    restricted_phrase = "Private Partner invented a secret reactor"
    result = validate(f"{restricted_phrase} for an undisclosed international team.")
    messages = " ".join(warning.message for warning in result.warnings)

    assert result.status == GroundingStatus.REVIEW_REQUIRED
    assert GroundingWarningCode.UNSUPPORTED_NAMED_ENTITY.value in warning_codes(result)
    assert GroundingWarningCode.UNSUPPORTED_FACTUAL_ASSERTION.value in warning_codes(
        result
    )
    assert restricted_phrase not in messages
    assert "secret reactor" not in messages


def test_legacy_drafts_default_to_manual_review_not_a_pass() -> None:
    result = GroundingResult.legacy_unvalidated()

    assert result.status == GroundingStatus.REVIEW_REQUIRED
    assert GroundingWarningCode.LEGACY_UNVALIDATED.value in warning_codes(result)
    assert result.human_review_required is True
