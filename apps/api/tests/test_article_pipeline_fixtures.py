"""NFA-36 reusable synthetic article-fixture contract tests."""

import asyncio

import pytest

from app.providers.exceptions import ProviderDataError
from app.providers.fixture_provider import FixtureNewsProvider
from app.providers.models import ArticleQuery
from tests.support.article_pipeline import (
    invalid_article_cases,
    synthetic_article_records,
)


def run(coroutine):
    return asyncio.run(coroutine)


def test_valid_fixture_library_runs_without_live_network_access() -> None:
    records = synthetic_article_records("valid")
    provider = FixtureNewsProvider(records)

    page = run(provider.fetch_articles(ArticleQuery(limit=100)))

    assert len(page.items) == 3
    assert {item.source_item_id for item in page.items} == {
        "fixture-pipeline-technology-001",
        "fixture-pipeline-business-001",
        "fixture-pipeline-science-001",
    }
    assert page.items[-1].description is None
    assert all(
        item.source_name == "NewsFlow AI synthetic fixture" for item in page.items
    )
    assert all(item.url.host == "example.invalid" for item in page.items)
    assert all(
        item.permitted_content.content_type == "synthetic" for item in page.items
    )


@pytest.mark.parametrize(
    "case",
    invalid_article_cases(),
    ids=lambda case: case["name"],
)
def test_invalid_fixture_records_fail_with_safe_provider_error(
    case: dict[str, object],
) -> None:
    provider = FixtureNewsProvider([case["record"]])  # type: ignore[list-item]

    with pytest.raises(ProviderDataError) as error:
        run(provider.fetch_articles(ArticleQuery(limit=10)))

    assert error.value.code.value == case["expected_error"]
    assert "restricted-test-value" not in str(error.value)
    assert "unauthorised.example.test" not in str(error.value)


def test_duplicate_and_updated_fixtures_preserve_expected_identity() -> None:
    duplicate_provider = FixtureNewsProvider(synthetic_article_records("duplicates"))
    updated_provider = FixtureNewsProvider(synthetic_article_records("updated"))

    duplicates = run(duplicate_provider.fetch_articles(ArticleQuery(limit=10))).items
    updated = run(updated_provider.fetch_articles(ArticleQuery(limit=10))).items[0]

    assert len(duplicates) == 2
    assert duplicates[0].source_item_id == duplicates[1].source_item_id
    assert duplicates[0].url == duplicates[1].url
    assert updated.source_item_id == "fixture-pipeline-technology-001"
    assert updated.title.endswith("updated lower-energy computing results")
