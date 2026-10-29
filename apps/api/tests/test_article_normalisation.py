"""NFA-30 article normalisation, validation, and sanitisation tests."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.providers import (
    FIXTURE_NORMALISATION_POLICY,
    ArticleCategory,
    ArticleFieldMapping,
    ArticleNormalisationError,
    ArticleNormalisationErrorCode,
    ArticleNormalisationService,
)


def valid_record(**changes: object) -> dict[str, object]:
    """Return one approved synthetic provider record."""

    record: dict[str, object] = {
        "record_key": "fixture-normalisation-001",
        "headline": "Synthetic article for normalisation testing",
        "link": "https://example.invalid/newsflow-ai/fixture-normalisation-001",
        "published_at": "2026-10-20T09:00:00+01:00",
        "topic": "technology",
        "summary": "A fictional summary created only for automated testing.",
        "body": "Original synthetic facts for NewsFlow AI tests.",
        "collected_at": "2026-10-20T09:05:00+01:00",
        "changed_at": None,
    }
    record.update(changes)
    return record


def test_valid_article_is_normalised_into_the_approved_contract() -> None:
    service = ArticleNormalisationService()
    record = valid_record(
        headline="  Synthetic   Cafe&#769;   update  ",
        link=(
            "HTTPS://EXAMPLE.INVALID/newsflow-ai/fixture-normalisation-001"
            "#provider-fragment"
        ),
        summary="  A   fictional   summary.  ",
    )

    article = service.normalise(record)

    assert article.title == "Synthetic Café update"
    assert str(article.url) == (
        "https://example.invalid/newsflow-ai/fixture-normalisation-001"
    )
    assert article.description == "A fictional summary."
    assert article.publication_date == datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
    assert article.retrieved_at == datetime(2026, 10, 20, 8, 5, tzinfo=UTC)
    assert article.category == ArticleCategory.TECHNOLOGY


def test_different_provider_field_names_use_an_explicit_mapping() -> None:
    alternate_mapping = ArticleFieldMapping(
        source_item_id="provider_id",
        title="title",
        url="article_link",
        publication_date="publication_date",
        category="section",
        description="permitted_summary",
        permitted_content="permitted_facts",
        retrieved_at="received_at",
        modified_at="updated_at",
    )
    policy = replace(
        FIXTURE_NORMALISATION_POLICY,
        field_mapping=alternate_mapping,
    )
    service = ArticleNormalisationService(policy)
    record = {
        "provider_id": "fixture-alternate-002",
        "title": "Synthetic differently shaped article",
        "article_link": "https://example.invalid/newsflow-ai/fixture-alternate-002",
        "publication_date": "2026-10-20T10:00:00Z",
        "section": "science",
        "permitted_summary": None,
        "permitted_facts": "Synthetic facts supplied through an alternate mapping.",
        "received_at": "2026-10-20T10:02:00Z",
        "updated_at": None,
    }

    article = service.normalise(record)

    assert article.source_item_id == "fixture-alternate-002"
    assert article.title == "Synthetic differently shaped article"
    assert article.category == ArticleCategory.SCIENCE
    assert article.description is None


@pytest.mark.parametrize(
    "invalid_date",
    ["not-a-date", "2026-10-20 09:00:00", 12345],
)
def test_invalid_publication_date_has_a_safe_documented_error(
    invalid_date: object,
) -> None:
    with pytest.raises(ArticleNormalisationError) as captured:
        ArticleNormalisationService().normalise(valid_record(published_at=invalid_date))

    assert captured.value.code == ArticleNormalisationErrorCode.INVALID_DATE
    assert captured.value.field_name == "published_at"
    assert str(invalid_date) not in captured.value.safe_message


@pytest.mark.parametrize("missing_field", ["headline", "link"])
def test_missing_required_fields_are_not_invented(missing_field: str) -> None:
    record = valid_record()
    del record[missing_field]

    with pytest.raises(ArticleNormalisationError) as captured:
        ArticleNormalisationService().normalise(record)

    assert captured.value.code == (ArticleNormalisationErrorCode.MISSING_REQUIRED_FIELD)
    assert captured.value.field_name == missing_field


@pytest.mark.parametrize(
    "unsafe_title",
    [
        "<script>alert('unsafe')</script>",
        "&lt;img src=x onerror=alert('unsafe')&gt;",
        "<svg/onload=alert('unsafe')",
        "Synthetic\x00title",
    ],
)
def test_unsafe_markup_and_control_characters_are_rejected(
    unsafe_title: str,
) -> None:
    with pytest.raises(ArticleNormalisationError) as captured:
        ArticleNormalisationService().normalise(valid_record(headline=unsafe_title))

    assert captured.value.code == ArticleNormalisationErrorCode.UNSAFE_TEXT
    assert unsafe_title not in captured.value.safe_message


@pytest.mark.parametrize(
    "invalid_url",
    [
        "http://example.invalid/article",
        "https://user:password@example.invalid/article",
        "https://unapproved.example/article",
        "not-a-url",
    ],
)
def test_invalid_or_unapproved_urls_are_rejected(invalid_url: str) -> None:
    with pytest.raises(ArticleNormalisationError) as captured:
        ArticleNormalisationService().normalise(valid_record(link=invalid_url))

    assert captured.value.code == ArticleNormalisationErrorCode.INVALID_URL
    assert invalid_url not in captured.value.safe_message


def test_unpermitted_provider_fields_are_never_retained() -> None:
    restricted_text = "Unlicensed full article text that must not be processed."
    article = ArticleNormalisationService().normalise(
        valid_record(
            image_url="https://example.invalid/restricted-image.jpg",
            private_provider_note="Confidential provider note",
            unlicensed_full_text=restricted_text,
        )
    )

    serialised = article.model_dump_json()
    assert "image_url" not in serialised
    assert "private_provider_note" not in serialised
    assert "unlicensed_full_text" not in serialised
    assert restricted_text not in serialised


def test_allowlist_contains_only_the_approved_fixture_fields() -> None:
    service = ArticleNormalisationService()

    assert service.permitted_input_fields == {
        "record_key",
        "headline",
        "link",
        "published_at",
        "topic",
        "summary",
        "body",
        "collected_at",
        "changed_at",
    }


def test_attribution_and_provenance_come_from_the_approved_policy() -> None:
    article = ArticleNormalisationService().normalise(
        valid_record(
            source_name="Untrusted replacement source",
            decision_id="UNTRUSTED-DECISION",
            attribution="Remove the required attribution",
        )
    )

    assert article.source_name == "NewsFlow AI synthetic fixture"
    assert article.rights.decision_id == "NFA-SRC-AUTH-001"
    assert article.attribution.attribution_text == (
        "Source: NewsFlow AI synthetic fixture - not live news"
    )
    assert article.attribution.canonical_url == article.url


def test_blank_optional_description_becomes_an_explicit_missing_value() -> None:
    article = ArticleNormalisationService().normalise(valid_record(summary="   "))

    assert article.description is None


def test_unknown_non_empty_category_maps_to_other() -> None:
    article = ArticleNormalisationService().normalise(
        valid_record(topic="Synthetic New Category")
    )

    assert article.category == ArticleCategory.OTHER


def test_missing_category_is_rejected_instead_of_invented() -> None:
    record = valid_record()
    del record["topic"]

    with pytest.raises(ArticleNormalisationError) as captured:
        ArticleNormalisationService().normalise(record)

    assert captured.value.code == (ArticleNormalisationErrorCode.MISSING_REQUIRED_FIELD)
    assert captured.value.field_name == "topic"


def test_rights_policy_blocks_processing_before_article_fields_are_read() -> None:
    policy = replace(FIXTURE_NORMALISATION_POLICY, storage_allowed=False)

    with pytest.raises(ArticleNormalisationError) as captured:
        ArticleNormalisationService(policy).normalise({})

    assert captured.value.code == (ArticleNormalisationErrorCode.RIGHTS_NOT_PERMITTED)


def test_malformed_top_level_record_is_rejected() -> None:
    with pytest.raises(ArticleNormalisationError) as captured:
        ArticleNormalisationService().normalise(  # type: ignore[arg-type]
            ["not", "a", "mapping"]
        )

    assert captured.value.code == ArticleNormalisationErrorCode.INVALID_RECORD


def test_safe_error_does_not_repeat_restricted_article_content() -> None:
    restricted_content = "<script>private-provider-content</script>"

    with pytest.raises(ArticleNormalisationError) as captured:
        ArticleNormalisationService().normalise(valid_record(body=restricted_content))

    assert restricted_content not in captured.value.safe_message
    assert "private-provider-content" not in captured.value.safe_message
