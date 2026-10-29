"""NFA-31 article identity and idempotent ingestion tests."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.providers.normalisation import ArticleNormalisationService
from app.repositories.articles import (
    ArticleIdentityConflictError,
    ArticleIngestionAction,
    ArticleIngestionResult,
    ArticleRepository,
    article_content_fingerprint,
)
from app.services.article_deduplication import (
    ArticleDeduplicationService,
    ArticleStorageNotPermittedError,
)
from app.services.article_identity import (
    ArticleIdentityService,
    ArticleIdentityStrategy,
)


def normalised_article(**changes: object):
    """Return one validated synthetic article for identity tests."""

    record: dict[str, object] = {
        "record_key": "fixture-deduplication-001",
        "headline": "Synthetic article identity example",
        "link": "https://example.invalid/newsflow-ai/deduplication-001",
        "published_at": "2026-10-20T09:00:00Z",
        "topic": "technology",
        "summary": "A fictional summary for article identity testing.",
        "body": "Original synthetic facts used only by automated tests.",
        "collected_at": "2026-10-20T09:05:00Z",
        "changed_at": None,
    }
    record.update(changes)
    return ArticleNormalisationService().normalise(record)


@dataclass
class _StoredArticle:
    article_id: UUID
    canonical_url: str
    fingerprint: str
    current_snapshot_id: UUID
    snapshot_ids: list[UUID] = field(default_factory=list)


class InMemoryArticleRepository(ArticleRepository):
    """Concurrency-safe fake that follows the PostgreSQL identity rules."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.by_source: dict[tuple[str, str], _StoredArticle] = {}
        self.by_url: dict[str, _StoredArticle] = {}

    async def ingest(self, article) -> ArticleIngestionResult:
        async with self._lock:
            source_key = (article.source_profile, article.source_item_id)
            canonical_url = str(article.url)
            source_match = self.by_source.get(source_key)
            url_match = self.by_url.get(canonical_url)
            if source_match is None and url_match is not None:
                raise ArticleIdentityConflictError(
                    "The canonical URL belongs to a different article identity."
                )
            if (
                source_match is not None
                and url_match is not None
                and source_match.article_id != url_match.article_id
            ):
                raise ArticleIdentityConflictError(
                    "The identity fields point to different articles."
                )

            fingerprint = article_content_fingerprint(article)
            if source_match is None:
                article_id = uuid4()
                snapshot_id = uuid4()
                stored = _StoredArticle(
                    article_id=article_id,
                    canonical_url=canonical_url,
                    fingerprint=fingerprint,
                    current_snapshot_id=snapshot_id,
                    snapshot_ids=[snapshot_id],
                )
                self.by_source[source_key] = stored
                self.by_url[canonical_url] = stored
                return ArticleIngestionResult(
                    article_id=article_id,
                    snapshot_id=snapshot_id,
                    action=ArticleIngestionAction.CREATED,
                )

            if source_match.fingerprint == fingerprint:
                return ArticleIngestionResult(
                    article_id=source_match.article_id,
                    snapshot_id=source_match.current_snapshot_id,
                    action=ArticleIngestionAction.SKIPPED,
                )

            self.by_url.pop(source_match.canonical_url)
            snapshot_id = uuid4()
            source_match.canonical_url = canonical_url
            source_match.fingerprint = fingerprint
            source_match.current_snapshot_id = snapshot_id
            source_match.snapshot_ids.append(snapshot_id)
            self.by_url[canonical_url] = source_match
            return ArticleIngestionResult(
                article_id=source_match.article_id,
                snapshot_id=snapshot_id,
                action=ArticleIngestionAction.UPDATED,
            )


def run(coroutine):
    """Run one asynchronous service operation in a normal Pytest test."""

    return asyncio.run(coroutine)


def test_provider_item_id_is_preferred_and_scoped_to_its_provider() -> None:
    service = ArticleIdentityService()
    first = service.resolve(
        provider_id="provider-one",
        external_article_id="shared-123",
        canonical_url="https://example.invalid/one",
    )
    second = service.resolve(
        provider_id="provider-two",
        external_article_id="shared-123",
        canonical_url="https://example.invalid/two",
    )

    assert first.strategy == ArticleIdentityStrategy.PROVIDER_ITEM_ID
    assert first.external_article_id == second.external_article_id
    assert first.provider_id != second.provider_id
    assert (first.provider_id, first.external_article_id) != (
        second.provider_id,
        second.external_article_id,
    )


def test_missing_provider_id_uses_a_repeatable_canonical_url_hash() -> None:
    service = ArticleIdentityService()
    parameters = {
        "provider_id": "fixture-v1",
        "external_article_id": None,
        "canonical_url": "https://example.invalid/fallback-identity",
        "fallback_prefix": "fixture-url-",
    }

    first = service.resolve(**parameters)
    second = service.resolve(**parameters)
    changed_url = service.resolve(
        **{**parameters, "canonical_url": "https://example.invalid/different"}
    )

    assert first.strategy == ArticleIdentityStrategy.CANONICAL_URL_SHA256
    assert first.external_article_id.startswith("fixture-url-")
    assert first.external_article_id == second.external_article_id
    assert first.external_article_id != changed_url.external_article_id


def test_normalisation_applies_the_fallback_before_contract_validation() -> None:
    article = normalised_article(record_key=None)

    assert article.source_item_id.startswith("fixture-url-")
    assert len(article.source_item_id) == len("fixture-url-") + 64


def test_new_and_repeated_article_are_created_then_skipped() -> None:
    repository = InMemoryArticleRepository()
    service = ArticleDeduplicationService(repository)
    article = normalised_article()

    first = run(service.ingest(article))
    second = run(service.ingest(article))

    assert first.action == ArticleIngestionAction.CREATED
    assert second.action == ArticleIngestionAction.SKIPPED
    assert second.article_id == first.article_id
    assert second.snapshot_id == first.snapshot_id
    assert len(repository.by_source) == 1


def test_retrieval_time_alone_does_not_create_a_new_snapshot() -> None:
    repository = InMemoryArticleRepository()
    service = ArticleDeduplicationService(repository)
    article = normalised_article()
    first = run(service.ingest(article))
    later_retrieval = article.model_copy(
        update={"retrieved_at": article.retrieved_at + timedelta(hours=1)}
    )

    second = run(service.ingest(later_retrieval))

    assert second.action == ArticleIngestionAction.SKIPPED
    assert second.snapshot_id == first.snapshot_id


def test_permitted_metadata_update_keeps_identity_and_old_snapshot() -> None:
    repository = InMemoryArticleRepository()
    service = ArticleDeduplicationService(repository)
    article = normalised_article()
    first = run(service.ingest(article))
    updated = article.model_copy(
        update={
            "title": "Synthetic article identity example - corrected",
            "modified_at": datetime(2026, 10, 20, 10, 0, tzinfo=UTC),
        }
    )

    second = run(service.ingest(updated))
    stored = repository.by_source[(article.source_profile, article.source_item_id)]

    assert second.action == ArticleIngestionAction.UPDATED
    assert second.article_id == first.article_id
    assert second.snapshot_id != first.snapshot_id
    assert stored.snapshot_ids == [first.snapshot_id, second.snapshot_id]


def test_same_source_identity_can_receive_a_new_unclaimed_canonical_url() -> None:
    repository = InMemoryArticleRepository()
    service = ArticleDeduplicationService(repository)
    article = normalised_article()
    first = run(service.ingest(article))
    updated = normalised_article(
        link="https://example.invalid/newsflow-ai/deduplication-001-canonical"
    )

    second = run(service.ingest(updated))

    assert second.action == ArticleIngestionAction.UPDATED
    assert second.article_id == first.article_id
    assert str(article.url) not in repository.by_url
    assert str(updated.url) in repository.by_url


def test_similar_titles_do_not_merge_different_source_identities() -> None:
    repository = InMemoryArticleRepository()
    service = ArticleDeduplicationService(repository)
    first_article = normalised_article()
    second_article = normalised_article(
        record_key="fixture-deduplication-002",
        headline=first_article.title,
        link="https://example.invalid/newsflow-ai/deduplication-002",
    )

    first = run(service.ingest(first_article))
    second = run(service.ingest(second_article))

    assert first.action == second.action == ArticleIngestionAction.CREATED
    assert first.article_id != second.article_id
    assert len(repository.by_source) == 2


def test_same_url_with_different_provider_identity_is_a_safe_conflict() -> None:
    repository = InMemoryArticleRepository()
    service = ArticleDeduplicationService(repository)
    first_article = normalised_article()
    conflicting_article = normalised_article(
        record_key="fixture-conflicting-identity",
        link=str(first_article.url),
    )
    run(service.ingest(first_article))

    with pytest.raises(ArticleIdentityConflictError):
        run(service.ingest(conflicting_article))

    assert len(repository.by_source) == 1


def test_concurrent_repeated_ingestion_creates_only_one_article() -> None:
    repository = InMemoryArticleRepository()
    service = ArticleDeduplicationService(repository)
    article = normalised_article()

    async def ingest_together():
        return await asyncio.gather(*(service.ingest(article) for _ in range(5)))

    results = run(ingest_together())

    assert [result.action for result in results].count(
        ArticleIngestionAction.CREATED
    ) == 1
    assert [result.action for result in results].count(
        ArticleIngestionAction.SKIPPED
    ) == 4
    assert len({result.article_id for result in results}) == 1
    assert len(repository.by_source) == 1


def test_storage_permission_is_checked_before_repository_use() -> None:
    repository = InMemoryArticleRepository()
    service = ArticleDeduplicationService(repository)
    article = normalised_article()
    restricted = article.model_copy(
        update={"rights": article.rights.model_copy(update={"storage_allowed": False})}
    )

    with pytest.raises(ArticleStorageNotPermittedError):
        run(service.ingest(restricted))

    assert repository.by_source == {}
