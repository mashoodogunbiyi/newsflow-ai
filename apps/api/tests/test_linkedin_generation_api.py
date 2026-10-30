"""NFA-40 authenticated LinkedIn generation API contract tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    require_authenticated_session,
    require_csrf_authenticated_session,
)
from app.api.routes.linkedin_generation import router
from app.core.errors import ApplicationError, register_exception_handlers
from app.models.ai import AITokenUsage
from app.models.generation_preferences import LinkedInGenerationPreferences
from app.models.grounding import GroundingResult, GroundingStatus
from app.models.linkedin_generation import (
    LinkedInDraft,
    LinkedInDraftSourceReference,
)
from app.repositories import AuthenticatedSession
from app.security import InMemoryRateLimiter

USER_ID = UUID("41000000-0000-4000-8000-000000000001")
ARTICLE_ID = UUID("41000000-0000-4000-8000-000000000002")
RIGHTS_ID = UUID("41000000-0000-4000-8000-000000000003")
NOW = datetime(2026, 10, 29, 18, 0, tzinfo=UTC)


class StubGenerationService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.item = LinkedInDraft(
            draft_id=uuid4(),
            generation_id=uuid4(),
            owner_id=USER_ID,
            draft="A private synthetic LinkedIn post draft for human review.",
            source=LinkedInDraftSourceReference(
                article_id=ARTICLE_ID,
                title="Synthetic source title",
                source_name="NewsFlow AI synthetic fixture",
                source_url="https://example.invalid/newsflow-ai/nfa-40",
                attribution_text="Source: NewsFlow AI synthetic fixture",
                rights_version_id=RIGHTS_ID,
            ),
            tone="professional",
            length="medium",
            grounding=GroundingResult(
                status=GroundingStatus.PASSED_AUTOMATED_CHECKS,
                checked_claim_count=1,
            ),
            prompt_version="linkedin_post_v1",
            model_identifier="test-openai-model",
            token_usage=AITokenUsage(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
            ),
            created_at=NOW,
        )

    async def generate_draft(
        self,
        *,
        owner_id: UUID,
        article_id: UUID,
        preferences: LinkedInGenerationPreferences,
        idempotency_key: str | None,
    ) -> LinkedInDraft:
        self.calls.append(
            {
                "owner_id": owner_id,
                "article_id": article_id,
                "preferences": preferences,
                "idempotency_key": idempotency_key,
            }
        )
        return self.item

    async def get_draft(self, *, owner_id: UUID, draft_id: UUID) -> LinkedInDraft:
        assert owner_id == USER_ID
        assert draft_id == self.item.draft_id
        return self.item


def active_session() -> AuthenticatedSession:
    return AuthenticatedSession(
        user_id=USER_ID,
        email="nfa40@example.invalid",
        csrf_token_hash=b"x" * 32,
        expires_at=NOW + timedelta(hours=1),
    )


def client(*, authenticated: bool = True, attempts: int = 10):
    service = StubGenerationService()
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router)
    application.state.linkedin_generation_service = service
    application.state.generation_rate_limiter = InMemoryRateLimiter(
        max_attempts=attempts,
        window_seconds=60,
    )
    if authenticated:

        async def session_override() -> AuthenticatedSession:
            return active_session()

    else:

        async def session_override() -> AuthenticatedSession:
            raise ApplicationError(
                status_code=401,
                code="authentication_required",
                message="Authentication is required.",
            )

    application.dependency_overrides[require_authenticated_session] = session_override
    application.dependency_overrides[require_csrf_authenticated_session] = (
        session_override
    )
    return TestClient(application), service


def test_generation_endpoint_requires_authentication_and_valid_preferences() -> None:
    unauthenticated, _ = client(authenticated=False)
    denied = unauthenticated.post(
        "/api/v1/linkedin-drafts",
        json={
            "article_id": str(ARTICLE_ID),
            "tone": "professional",
            "length": "medium",
        },
    )
    authenticated, _ = client()
    invalid = authenticated.post(
        "/api/v1/linkedin-drafts",
        json={
            "article_id": str(ARTICLE_ID),
            "tone": "unlimited-expert",
            "length": "medium",
        },
    )

    assert denied.status_code == 401
    assert invalid.status_code == 422


def test_generation_and_private_get_return_no_store_human_review_draft() -> None:
    test_client, service = client()
    response = test_client.post(
        "/api/v1/linkedin-drafts",
        headers={"Idempotency-Key": "nfa40-request-001"},
        json={
            "article_id": str(ARTICLE_ID),
            "tone": "professional",
            "length": "medium",
        },
    )
    retrieved = test_client.get(f"/api/v1/linkedin-drafts/{service.item.draft_id}")

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["status"] == "draft"
    assert response.json()["review_required"] is True
    assert response.json()["grounding"]["status"] == "passed_automated_checks"
    assert response.json()["source"]["article_id"] == str(ARTICLE_ID)
    assert "owner_id" not in response.json()
    assert "model_identifier" in response.json()
    assert retrieved.status_code == 200
    assert retrieved.headers["cache-control"] == "private, no-store"
    assert service.calls[0]["idempotency_key"] == "nfa40-request-001"


def test_generation_endpoint_applies_per_user_request_limit() -> None:
    test_client, _ = client(attempts=1)
    payload = {
        "article_id": str(ARTICLE_ID),
        "tone": "professional",
        "length": "medium",
    }

    first = test_client.post("/api/v1/linkedin-drafts", json=payload)
    limited = test_client.post("/api/v1/linkedin-drafts", json=payload)

    assert first.status_code == 201
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "generation_limit_exceeded"
    assert int(limited.headers["retry-after"]) >= 1
