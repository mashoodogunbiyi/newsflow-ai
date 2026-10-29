"""NFA-28 source-provider contract and synthetic fixture tests."""

import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any, TypeVar

import pytest

from app.core.config import Settings
from app.providers import (
    ArticleDiscoveryService,
    ArticleNotFoundError,
    ArticleQuery,
    FixtureNewsProvider,
    InvalidProviderCursorError,
    NewsArticle,
    NewsProvider,
    ProviderCapabilities,
    ProviderDataError,
    ProviderErrorCode,
    ProviderPage,
    ProviderUnavailableError,
    SourceNotAuthorisedError,
    create_news_provider,
)

Result = TypeVar("Result")


def resolve(operation: Coroutine[Any, Any, Result]) -> Result:
    """Run one provider operation without requiring an async pytest plugin."""

    return asyncio.run(operation)


def valid_fixture(**changes: object) -> dict[str, object]:
    """Return one provider-shaped synthetic record for focused tests."""

    fixture: dict[str, object] = {
        "record_key": "fixture-alternate-001",
        "headline": "Synthetic provider headline",
        "link": "https://example.invalid/newsflow-ai/fixture-alternate-001",
        "published_at": "2026-10-15T09:00:00Z",
        "topic": "community innovation",
        "summary": "A fictional summary written for interface testing.",
        "body": "Original synthetic content with no connection to live news.",
        "collected_at": "2026-10-15T09:02:00Z",
        "changed_at": None,
    }
    fixture.update(changes)
    return fixture


def test_fixture_provider_implements_the_reusable_protocol() -> None:
    provider = FixtureNewsProvider()

    assert isinstance(provider, NewsProvider)
    assert provider.provider_id == "fixture"
    assert provider.capabilities == ProviderCapabilities(
        pagination=True,
        incremental_retrieval=True,
    )


def test_fixture_provider_returns_the_approved_article_contract() -> None:
    page = resolve(FixtureNewsProvider().fetch_articles(ArticleQuery(limit=10)))

    assert len(page.items) == 3
    article = page.items[0]
    assert isinstance(article, NewsArticle)
    assert article.contract_version == "1.0"
    assert article.source_profile == "fixture-v1"
    assert article.source_item_id == "fixture-technology-001"
    assert article.title.startswith("Synthetic company")
    assert str(article.url).startswith("https://example.invalid/")
    assert article.permitted_content.ai_processing_allowed is True
    assert article.permitted_content.derivative_output_allowed is True
    assert article.rights.storage_allowed is True
    assert article.rights.display_allowed is True
    assert article.attribution.canonical_url == article.url


def test_provider_specific_fields_are_mapped_to_consistent_output() -> None:
    provider = FixtureNewsProvider([valid_fixture()])

    article = resolve(provider.fetch_article("fixture-alternate-001"))

    assert article.title == "Synthetic provider headline"
    assert article.category.value == "Other"
    assert article.publication_date == datetime(2026, 10, 15, 9, 0, tzinfo=UTC)
    assert not hasattr(article, "headline")
    assert not hasattr(article, "topic")


@pytest.mark.parametrize(
    ("change", "private_value"),
    [
        ({"headline": ""}, None),
        ({"link": "http://user:private@example.invalid/article"}, "private"),
        ({"body": "<script>unsafe()</script>"}, "unsafe()"),
    ],
)
def test_invalid_provider_data_becomes_a_safe_documented_error(
    change: dict[str, object],
    private_value: str | None,
) -> None:
    provider = FixtureNewsProvider([valid_fixture(**change)])

    with pytest.raises(ProviderDataError) as captured:
        resolve(provider.fetch_articles(ArticleQuery()))

    assert captured.value.code == ProviderErrorCode.PROVIDER_DATA_INVALID
    assert captured.value.retryable is False
    if private_value is not None:
        assert private_value not in captured.value.safe_message


def test_provider_failure_uses_a_stable_safe_error() -> None:
    provider = FixtureNewsProvider(simulated_error=ProviderUnavailableError())

    with pytest.raises(ProviderUnavailableError) as captured:
        resolve(provider.fetch_articles(ArticleQuery()))

    assert captured.value.code == ProviderErrorCode.PROVIDER_UNAVAILABLE
    assert captured.value.retryable is True
    assert (
        captured.value.safe_message == "The news provider is temporarily unavailable."
    )


def test_fixture_provider_returns_cursor_based_pages() -> None:
    provider = FixtureNewsProvider()

    first_page = resolve(provider.fetch_articles(ArticleQuery(limit=2)))
    second_page = resolve(
        provider.fetch_articles(
            ArticleQuery(limit=2, cursor=first_page.next_cursor),
        )
    )

    assert [item.source_item_id for item in first_page.items] == [
        "fixture-technology-001",
        "fixture-business-001",
    ]
    assert first_page.next_cursor is not None
    assert [item.source_item_id for item in second_page.items] == [
        "fixture-science-001"
    ]
    assert second_page.next_cursor is None


def test_fixture_provider_supports_incremental_discovery() -> None:
    page = resolve(
        FixtureNewsProvider().fetch_articles(
            ArticleQuery(published_after=datetime(2026, 10, 13, tzinfo=UTC))
        )
    )

    assert [item.source_item_id for item in page.items] == [
        "fixture-business-001",
        "fixture-science-001",
    ]


def test_invalid_cursor_is_rejected_without_internal_details() -> None:
    with pytest.raises(InvalidProviderCursorError) as captured:
        resolve(
            FixtureNewsProvider().fetch_articles(
                ArticleQuery(cursor="not-a-provider-cursor")
            )
        )

    assert captured.value.code == ProviderErrorCode.INVALID_PROVIDER_CURSOR


def test_missing_article_uses_a_documented_provider_error() -> None:
    with pytest.raises(ArticleNotFoundError) as captured:
        resolve(FixtureNewsProvider().fetch_article("fixture-missing-999"))

    assert captured.value.code == ProviderErrorCode.ARTICLE_NOT_FOUND


def test_provider_can_be_replaced_without_changing_the_consumer() -> None:
    article = resolve(FixtureNewsProvider().fetch_article("fixture-technology-001"))

    class AlternateCompliantProvider:
        provider_id = "alternate-test-provider"
        capabilities = ProviderCapabilities(
            pagination=False,
            incremental_retrieval=False,
        )

        async def fetch_articles(self, query: ArticleQuery) -> ProviderPage:
            del query
            return ProviderPage(
                provider_id=self.provider_id,
                items=(article,),
                capabilities=self.capabilities,
            )

        async def fetch_article(self, source_item_id: str) -> NewsArticle:
            del source_item_id
            return article

    service = ArticleDiscoveryService(AlternateCompliantProvider())

    page = resolve(service.discover(ArticleQuery()))
    selected = resolve(service.retrieve(article.source_item_id))

    assert page.provider_id == "alternate-test-provider"
    assert page.items == (article,)
    assert selected == article


def test_provider_factory_enables_only_the_explicit_fixture_mode() -> None:
    provider = create_news_provider(
        Settings(_env_file=None, news_source_mode="fixture")
    )

    assert isinstance(provider, FixtureNewsProvider)

    with pytest.raises(SourceNotAuthorisedError) as captured:
        create_news_provider(Settings(_env_file=None, news_source_mode="disabled"))

    assert captured.value.code == ProviderErrorCode.SOURCE_NOT_AUTHORISED
