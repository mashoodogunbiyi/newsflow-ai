"""NFA-34 article catalogue service and REST endpoint tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import require_authenticated_session
from app.api.routes.articles import router
from app.core.errors import ApplicationError, register_exception_handlers
from app.models.article_catalogue import ArticleCatalogueQuery, ArticleCatalogueSort
from app.repositories import AuthenticatedSession
from app.repositories.article_catalogue import (
    ArticleCatalogueCursor,
    ArticleCatalogueFilters,
    ArticleCatalogueRecord,
    ArticleCatalogueRepositoryError,
)
from app.services.article_catalogue import (
    ArticleCatalogueNotFoundError,
    ArticleCatalogueService,
)

NOW = datetime(2026, 10, 29, 15, 0, tzinfo=UTC)
USER_ID = uuid4()


def article_record(
    *,
    article_id: UUID | None = None,
    title: str = "Synthetic technology briefing",
    published_at: datetime | None = None,
    **changes: object,
) -> ArticleCatalogueRecord:
    """Create rights-approved synthetic article metadata."""

    values: dict[str, object] = {
        "id": article_id or uuid4(),
        "article_status": "active",
        "title": title,
        "description": "Synthetic metadata used only for automated testing.",
        "canonical_url": "https://example.invalid/newsflow-ai/catalogue-test",
        "provider": "fixture-v1",
        "source_name": "NewsFlow AI synthetic fixture",
        "published_at": published_at or NOW - timedelta(hours=2),
        "category": "technology",
        "snapshot_display_allowed": True,
        "attribution_display_name": "NewsFlow AI synthetic fixture",
        "attribution_text": "Source: NewsFlow AI synthetic fixture - not live news",
        "byline": None,
        "copyright_notice": None,
        "source_status": "enabled",
        "rights_verification_status": "verified",
        "rights_display_allowed": True,
        "attribution_required": True,
        "rights_attribution_text": (
            "Source: NewsFlow AI synthetic fixture - not live news"
        ),
        "retention_expires_at": NOW + timedelta(days=30),
        "rights_last_verified_at": NOW - timedelta(days=1),
        "rights_effective_from": NOW - timedelta(days=1),
    }
    values.update(changes)
    return ArticleCatalogueRecord(**values)


class InMemoryArticleCatalogueRepository:
    """Small read repository that records already-validated query values."""

    def __init__(self, records: list[ArticleCatalogueRecord]) -> None:
        self.records = records
        self.list_calls: list[
            tuple[
                ArticleCatalogueFilters,
                ArticleCatalogueCursor | None,
                datetime,
                int,
            ]
        ] = []
        self.fail = False

    async def list_visible(
        self,
        *,
        filters: ArticleCatalogueFilters,
        cursor: ArticleCatalogueCursor | None,
        checked_at: datetime,
        limit: int,
    ) -> list[ArticleCatalogueRecord]:
        if self.fail:
            raise ArticleCatalogueRepositoryError("Synthetic database detail.")
        self.list_calls.append((filters, cursor, checked_at, limit))
        return self.records[:limit]

    async def get_visible(
        self,
        *,
        article_id: UUID,
        checked_at: datetime,
    ) -> ArticleCatalogueRecord | None:
        del checked_at
        if self.fail:
            raise ArticleCatalogueRepositoryError("Synthetic database detail.")
        return next((item for item in self.records if item.id == article_id), None)


def authenticated_session() -> AuthenticatedSession:
    return AuthenticatedSession(
        user_id=USER_ID,
        email="catalogue.user@example.invalid",
        csrf_token_hash=b"x" * 32,
        expires_at=NOW + timedelta(hours=1),
    )


def make_client(
    repository: InMemoryArticleCatalogueRepository,
    *,
    authenticated: bool = True,
) -> TestClient:
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router)
    application.state.article_catalogue_service = ArticleCatalogueService(
        repository,
        clock=lambda: NOW,
    )

    if authenticated:

        async def session_override() -> AuthenticatedSession:
            return authenticated_session()

    else:

        async def session_override() -> AuthenticatedSession:
            raise ApplicationError(
                status_code=401,
                code="authentication_required",
                message="Authentication is required.",
            )

    application.dependency_overrides[require_authenticated_session] = session_override
    return TestClient(application)


def test_list_endpoint_returns_only_public_rights_approved_metadata() -> None:
    record = article_record()
    repository = InMemoryArticleCatalogueRepository([record])
    client = make_client(repository)

    response = client.get(
        "/api/articles",
        params={
            "search": "technology",
            "provider": "FIXTURE-V1",
            "published_from": "2026-10-01T00:00:00Z",
            "published_to": "2026-10-30T00:00:00Z",
            "sort": "newest",
            "limit": 20,
        },
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    item = response.json()["items"][0]
    assert item == {
        "id": str(record.id),
        "title": record.title,
        "description": record.description,
        "source_url": record.canonical_url,
        "provider": "fixture-v1",
        "published_at": "2026-10-29T13:00:00Z",
        "category": "Technology",
        "attribution": {
            "display_name": "NewsFlow AI synthetic fixture",
            "text": "Source: NewsFlow AI synthetic fixture - not live news",
            "byline": None,
            "copyright_notice": None,
        },
    }
    assert response.json()["next_cursor"] is None
    assert (
        not {
            "source_item_id",
            "rights_decision_ref",
            "rights_verification_status",
            "permitted_content_text",
            "source_profile_id",
        }
        & item.keys()
    )
    filters, cursor, checked_at, requested_limit = repository.list_calls[0]
    assert filters.search == "technology"
    assert filters.provider == "fixture-v1"
    assert filters.published_from == datetime(2026, 10, 1, tzinfo=UTC)
    assert filters.published_to == datetime(2026, 10, 30, tzinfo=UTC)
    assert cursor is None
    assert checked_at == NOW
    assert requested_limit == 21


def test_individual_endpoint_returns_article_and_missing_is_404() -> None:
    record = article_record()
    client = make_client(InMemoryArticleCatalogueRepository([record]))

    response = client.get(f"/api/articles/{record.id}")
    missing = client.get(f"/api/articles/{uuid4()}")

    assert response.status_code == 200
    assert response.json()["id"] == str(record.id)
    assert missing.status_code == 404
    assert missing.json() == {
        "error": {
            "code": "article_not_found",
            "message": "The requested article was not found.",
        }
    }


def test_restricted_or_expired_article_is_not_disclosed() -> None:
    record = article_record(retention_expires_at=NOW - timedelta(seconds=1))
    service = ArticleCatalogueService(
        InMemoryArticleCatalogueRepository([record]),
        clock=lambda: NOW,
    )

    try:
        import asyncio

        asyncio.run(service.get_article(record.id))
    except ArticleCatalogueNotFoundError:
        pass
    else:
        raise AssertionError("An expired article must not be disclosed.")


def test_cursor_pagination_is_opaque_stable_and_bound_to_filters() -> None:
    records = [
        article_record(
            title=f"Synthetic item {number}",
            published_at=NOW - timedelta(hours=number),
        )
        for number in range(1, 4)
    ]
    repository = InMemoryArticleCatalogueRepository(records)
    client = make_client(repository)

    first = client.get("/api/articles", params={"limit": 2, "sort": "newest"})

    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert cursor
    assert str(records[1].id) not in cursor

    repository.records = [records[2]]
    second = client.get(
        "/api/articles",
        params={"limit": 2, "sort": "newest", "cursor": cursor},
    )
    assert second.status_code == 200
    assert second.json()["items"][0]["id"] == str(records[2].id)
    assert repository.list_calls[-1][1] == ArticleCatalogueCursor(
        published_at=records[1].published_at,
        article_id=records[1].id,
    )

    changed_query = client.get(
        "/api/articles",
        params={
            "limit": 2,
            "sort": "oldest",
            "cursor": cursor,
        },
    )
    assert changed_query.status_code == 422
    assert changed_query.json()["error"]["code"] == "invalid_article_cursor"

    tampered = client.get(
        "/api/articles",
        params={"limit": 2, "sort": "newest", "cursor": f"{cursor}!"},
    )
    assert tampered.status_code == 422


def test_search_input_is_forwarded_as_data_without_interpretation() -> None:
    repository = InMemoryArticleCatalogueRepository([])
    client = make_client(repository)
    malicious_text = "%' OR 1=1 --"

    response = client.get("/api/articles", params={"search": malicious_text})

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert repository.list_calls[0][0].search == malicious_text


def test_invalid_query_parameters_use_standard_validation_response() -> None:
    client = make_client(InMemoryArticleCatalogueRepository([]))

    invalid_limit = client.get("/api/articles", params={"limit": 0})
    invalid_provider = client.get("/api/articles", params={"provider": "bad value"})
    invalid_range = client.get(
        "/api/articles",
        params={
            "published_from": "2026-10-30T00:00:00Z",
            "published_to": "2026-10-01T00:00:00Z",
        },
    )

    assert invalid_limit.status_code == 422
    assert invalid_provider.status_code == 422
    assert invalid_range.status_code == 422
    assert invalid_limit.json()["error"]["code"] == "validation_error"


def test_authentication_is_required_for_list_and_detail() -> None:
    record = article_record()
    client = make_client(
        InMemoryArticleCatalogueRepository([record]),
        authenticated=False,
    )

    assert client.get("/api/articles").status_code == 401
    assert client.get(f"/api/articles/{record.id}").status_code == 401


def test_database_failure_returns_safe_controlled_error() -> None:
    repository = InMemoryArticleCatalogueRepository([])
    repository.fail = True
    client = make_client(repository)

    response = client.get("/api/articles")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "article_catalogue_unavailable",
            "message": "The article catalogue is temporarily unavailable.",
        }
    }
    assert "Synthetic database detail" not in response.text


def test_openapi_documents_catalogue_parameters_security_and_responses() -> None:
    client = make_client(InMemoryArticleCatalogueRepository([]))

    document = client.get("/openapi.json").json()
    listing = document["paths"]["/api/articles"]["get"]
    detail = document["paths"]["/api/articles/{article_id}"]["get"]

    assert {parameter["name"] for parameter in listing["parameters"]} >= {
        "limit",
        "cursor",
        "search",
        "provider",
        "published_from",
        "published_to",
        "sort",
    }
    assert listing["security"] == [{"SessionCookie": []}]
    assert "200" in listing["responses"]
    assert "404" in detail["responses"]


def test_query_model_normalises_oldest_sort_and_provider() -> None:
    query = ArticleCatalogueQuery(provider="FIXTURE-V1", sort="oldest")

    assert query.provider == "fixture-v1"
    assert query.sort == ArticleCatalogueSort.OLDEST
