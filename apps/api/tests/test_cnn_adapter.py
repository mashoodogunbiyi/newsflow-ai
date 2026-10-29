"""NFA-29 tests proving live CNN access remains blocked before networking."""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.providers import (
    ArticleQuery,
    CnnAdapterDecision,
    CnnSourceAdapter,
    NewsProvider,
    ProviderCapabilities,
    ProviderErrorCode,
    SourceNotAuthorisedError,
    create_news_provider,
)

Result = TypeVar("Result")


def resolve(operation: Coroutine[Any, Any, Result]) -> Result:
    """Run one async adapter operation without an async pytest plugin."""

    return asyncio.run(operation)


def test_disabled_cnn_adapter_implements_the_provider_protocol() -> None:
    adapter = CnnSourceAdapter()

    assert isinstance(adapter, NewsProvider)
    assert adapter.provider_id == "cnn-disabled"
    assert adapter.capabilities == ProviderCapabilities(
        pagination=False,
        incremental_retrieval=False,
    )


def test_adapter_records_the_active_no_go_decisions() -> None:
    assert CnnSourceAdapter().decision == CnnAdapterDecision(
        authorisation_decision_id="NFA-SRC-AUTH-001",
        architecture_decision_id="ADR-001",
        status="blocked",
        live_access_authorised=False,
    )


def test_article_discovery_is_blocked_before_an_http_request() -> None:
    adapter = CnnSourceAdapter()

    with patch(
        "httpx.AsyncClient.request",
        side_effect=AssertionError("An HTTP request must not occur."),
    ) as request:
        with pytest.raises(SourceNotAuthorisedError) as captured:
            resolve(adapter.fetch_articles(ArticleQuery()))

    request.assert_not_called()
    assert captured.value.code == ProviderErrorCode.SOURCE_NOT_AUTHORISED
    assert captured.value.retryable is False


def test_article_detail_is_blocked_before_an_http_request() -> None:
    adapter = CnnSourceAdapter()

    with patch(
        "httpx.AsyncClient.request",
        side_effect=AssertionError("An HTTP request must not occur."),
    ) as request:
        with pytest.raises(SourceNotAuthorisedError) as captured:
            resolve(adapter.fetch_article("cnn-article-that-must-not-be-requested"))

    request.assert_not_called()
    assert captured.value.safe_message == (
        "The requested news source is not authorised."
    )


def test_configuration_cannot_select_a_cnn_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, news_source_mode="cnn")  # type: ignore[arg-type]


def test_proposed_cnn_environment_values_do_not_enable_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CNN_INTEGRATION_ENABLED", "true")
    monkeypatch.setenv("CNN_API_BASE_URL", "https://unapproved.example.invalid")
    monkeypatch.setenv("CNN_API_KEY", "synthetic-value-that-must-be-ignored")

    settings = Settings(_env_file=None)

    assert settings.news_source_mode == "disabled"
    assert "CNN_API_KEY" not in repr(settings)
    with pytest.raises(SourceNotAuthorisedError):
        create_news_provider(settings)
