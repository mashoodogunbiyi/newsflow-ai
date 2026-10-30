"""NFA-46 integrated E4 generation acceptance tests using synthetic data."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import require_csrf_authenticated_session
from app.api.routes.generations import router
from app.core.errors import ApplicationError, register_exception_handlers
from app.models.ai import AITextGenerationResult, AITokenUsage
from app.models.article_rights import (
    ArticleRightsPolicy,
    ArticleRightsRecord,
    RightsVerificationStatus,
)
from app.models.generation_audit import (
    GenerationAuditEvent,
    GenerationAuditEventCreate,
    GenerationAuditEventType,
)
from app.models.generation_usage import (
    GenerationErrorCategory,
    GenerationUsageAttempt,
)
from app.models.linkedin_generation import LinkedInDraft
from app.providers.fixture_provider import DEFAULT_FIXTURES
from app.providers.models import NewsArticle
from app.providers.normalisation import ArticleNormalisationService
from app.repositories import AuthenticatedSession
from app.repositories.article_rights import CurrentArticleRights
from app.repositories.linkedin_generation import LinkedInGenerationArticle
from app.security import InMemoryRateLimiter
from app.services.article_rights import ArticleRightsService
from app.services.generation_audit import GenerationAuditService
from app.services.generation_usage import GenerationLimitExceeded
from app.services.linkedin_generation import LinkedInGenerationService
from app.services.openai_service import OpenAIUnavailableFailure

NOW = datetime(2026, 10, 30, 16, 0, tzinfo=UTC)
USER_ID = UUID("46000000-0000-4000-8000-000000000001")
ARTICLE_ID = UUID("46000000-0000-4000-8000-000000000002")
SNAPSHOT_ID = UUID("46000000-0000-4000-8000-000000000003")
RIGHTS_ID = UUID("46000000-0000-4000-8000-000000000004")
EXPECTED_RESPONSE_FIELDS = {
    "generation_id",
    "article_id",
    "draft",
    "tone",
    "length",
    "source_title",
    "source_name",
    "source_url",
    "source_attribution",
    "status",
    "review_required",
    "grounding_status",
    "validation_warnings",
    "grounding_policy_version",
    "created_at",
}


def _article(*, sufficient: bool = True) -> NewsArticle:
    article = ArticleNormalisationService().normalise(DEFAULT_FIXTURES[0])
    if sufficient:
        return article
    values = article.model_dump(mode="json")
    values["description"] = None
    values["permitted_content"] = {
        "status": "missing",
        "content_type": "none",
        "text": None,
        "ai_processing_allowed": False,
        "derivative_output_allowed": False,
    }
    return NewsArticle.model_validate(values)


def _rights(*, ai_allowed: bool = True) -> ArticleRightsRecord:
    policy = ArticleRightsPolicy(
        verification_status=RightsVerificationStatus.VERIFIED,
        storage_allowed=True,
        display_allowed=True,
        ai_processing_allowed=ai_allowed,
        derivative_output_allowed=ai_allowed,
        redistribution_allowed=False,
        attribution_required=True,
        attribution_text="Source: NewsFlow AI synthetic fixture",
        retention_rule="synthetic-test-only",
        retention_expires_at=NOW + timedelta(days=30),
        authorisation_reference="NFA-SYNTHETIC-TEST",
        source_contract_version="1.0",
        rights_last_verified_at=NOW - timedelta(days=1),
        effective_from=NOW - timedelta(days=1),
    )
    return ArticleRightsRecord(
        id=RIGHTS_ID,
        article_id=ARTICLE_ID,
        version_number=1,
        superseded_at=None,
        **policy.model_dump(),
    )


def _draft_text() -> str:
    return " ".join("platform" for _ in range(80))


def _provider_result(*, text: str | None = None) -> AITextGenerationResult:
    return AITextGenerationResult(
        text=(
            text
            if text is not None
            else json.dumps(
                {
                    "status": "ready",
                    "draft": _draft_text(),
                    "insufficiency_reason": None,
                }
            )
        ),
        model="synthetic-openai-model",
        response_id="synthetic-response-id",
        request_id="synthetic-request-id",
        usage=AITokenUsage(
            input_tokens=120,
            output_tokens=100,
            total_tokens=220,
        ),
    )


class InMemoryRightsRepository:
    def __init__(self, rights: ArticleRightsRecord) -> None:
        self.rights = rights

    async def get_current(self, article_id: UUID) -> CurrentArticleRights | None:
        if article_id != self.rights.article_id:
            return None
        return CurrentArticleRights(record=self.rights, source_enabled=True)


class InMemoryGenerationRepository:
    def __init__(self, article: NewsArticle) -> None:
        self.source = LinkedInGenerationArticle(
            article_id=ARTICLE_ID,
            snapshot_id=SNAPSHOT_ID,
            article=article,
        )
        self.saved: list[LinkedInDraft] = []

    async def get_article(
        self,
        article_id: UUID,
    ) -> LinkedInGenerationArticle | None:
        return self.source if article_id == ARTICLE_ID else None

    async def get_draft_by_request_key(self, **values: object) -> None:
        del values
        return None

    async def save_draft(self, **values: object) -> LinkedInDraft:
        generated = values["generated"]
        preferences = values["preferences"]
        assert isinstance(generated, AITextGenerationResult)
        item = LinkedInDraft(
            draft_id=uuid4(),
            generation_id=uuid4(),
            owner_id=values["owner_id"],
            draft=values["draft_text"],
            source=values["source_reference"],
            tone=preferences.tone,  # type: ignore[union-attr]
            length=preferences.post_length,  # type: ignore[union-attr]
            grounding=values["grounding"],
            prompt_version=values["prompt_version"],
            model_identifier=generated.model,
            token_usage=generated.usage,
            created_at=NOW,
        )
        self.saved.append(item)
        return item


class MockOpenAIGenerator:
    def __init__(self, outcome: AITextGenerationResult | Exception) -> None:
        self.outcome = outcome
        self.calls: list[object] = []
        self.closed = False

    async def generate_text(self, request: object) -> AITextGenerationResult:
        self.calls.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome

    async def close(self) -> None:
        self.closed = True


class RecordingUsageService:
    def __init__(self, *, reject: bool = False) -> None:
        self.reject = reject
        self.started: list[GenerationUsageAttempt] = []
        self.completed: list[dict[str, object]] = []
        self.failed: list[dict[str, object]] = []

    async def start_attempt(
        self,
        *,
        owner_id: UUID,
        request_fingerprint: str,
    ) -> GenerationUsageAttempt:
        if self.reject:
            raise GenerationLimitExceeded(
                code="generation_limit_exceeded",
                message="You have reached your current generation limit.",
                retry_after_seconds=3600,
            )
        attempt = GenerationUsageAttempt(
            id=uuid4(),
            owner_id=owner_id,
            request_fingerprint=request_fingerprint,
            created_at=NOW,
            expires_at=NOW + timedelta(minutes=3),
        )
        self.started.append(attempt)
        return attempt

    async def complete_attempt(self, **values: object) -> None:
        self.completed.append(values)

    async def fail_attempt(self, **values: object) -> None:
        self.failed.append(values)


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self.events: list[GenerationAuditEvent] = []

    async def delete_before(self, cutoff: datetime) -> int:
        retained = [event for event in self.events if event.occurred_at >= cutoff]
        deleted = len(self.events) - len(retained)
        self.events = retained
        return deleted

    async def record_event(
        self,
        event: GenerationAuditEventCreate,
    ) -> GenerationAuditEvent:
        stored = GenerationAuditEvent(id=uuid4(), **event.model_dump())
        self.events.append(stored)
        return stored


@dataclass
class AcceptanceHarness:
    client: TestClient
    application: FastAPI
    repository: InMemoryGenerationRepository
    generator: MockOpenAIGenerator
    usage: RecordingUsageService
    audit: InMemoryAuditRepository


def _harness(
    *,
    authenticated: bool = True,
    csrf_valid: bool = True,
    ai_allowed: bool = True,
    sufficient_source: bool = True,
    provider_outcome: AITextGenerationResult | Exception | None = None,
    reject_usage: bool = False,
) -> AcceptanceHarness:
    repository = InMemoryGenerationRepository(_article(sufficient=sufficient_source))
    generator = MockOpenAIGenerator(provider_outcome or _provider_result())
    usage = RecordingUsageService(reject=reject_usage)
    audit_repository = InMemoryAuditRepository()
    audit = GenerationAuditService(
        repository=audit_repository,
        retention=timedelta(days=90),
        clock=lambda: NOW,
    )
    rights = ArticleRightsService(
        InMemoryRightsRepository(_rights(ai_allowed=ai_allowed))
    )
    generation = LinkedInGenerationService(
        repository=repository,
        rights=rights,
        openai_factory=lambda: generator,
        usage=usage,  # type: ignore[arg-type]
        audit=audit,
    )
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router)
    application.state.linkedin_generation_service = generation
    application.state.generation_audit_service = audit
    application.state.generation_rate_limiter = InMemoryRateLimiter(
        max_attempts=20,
        window_seconds=60,
    )

    async def session_override() -> AuthenticatedSession:
        if not authenticated:
            raise ApplicationError(
                status_code=401,
                code="authentication_required",
                message="Authentication is required.",
            )
        if not csrf_valid:
            raise ApplicationError(
                status_code=403,
                code="csrf_validation_failed",
                message="CSRF validation failed.",
            )
        return AuthenticatedSession(
            user_id=USER_ID,
            email="nfa46@example.invalid",
            csrf_token_hash=b"x" * 32,
            expires_at=NOW + timedelta(hours=1),
        )

    application.dependency_overrides[require_csrf_authenticated_session] = (
        session_override
    )
    return AcceptanceHarness(
        client=TestClient(application),
        application=application,
        repository=repository,
        generator=generator,
        usage=usage,
        audit=audit_repository,
    )


def _post(
    harness: AcceptanceHarness,
    *,
    tone: str = "professional",
    length: str = "short",
):
    return harness.client.post(
        "/api/generations",
        headers={"Idempotency-Key": "nfa46-acceptance-request"},
        json={
            "article_id": str(ARTICLE_ID),
            "tone": tone,
            "length": length,
        },
    )


def test_complete_authenticated_generation_workflow_and_frontend_contract() -> None:
    harness = _harness()

    response = _post(harness)
    body = response.json()

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert set(body) == EXPECTED_RESPONSE_FIELDS
    assert body["article_id"] == str(ARTICLE_ID)
    assert body["draft"] == _draft_text()
    assert body["source_title"] == harness.repository.source.article.title
    assert body["source_url"] == str(harness.repository.source.article.url)
    assert body["source_attribution"] == "Source: NewsFlow AI synthetic fixture"
    assert body["status"] == "draft"
    assert body["review_required"] is True
    assert body["grounding_status"] in {
        "passed_automated_checks",
        "review_required",
    }
    assert len(harness.repository.saved) == 1
    assert len(harness.generator.calls) == 1
    assert harness.generator.closed is True
    assert harness.usage.completed[0]["token_usage"].total_tokens == 220
    assert [event.event_type for event in harness.audit.events] == [
        GenerationAuditEventType.GENERATION_STARTED,
        GenerationAuditEventType.RIGHTS_VERIFIED,
        GenerationAuditEventType.VALIDATION_PASSED,
        GenerationAuditEventType.GENERATION_COMPLETED,
    ]
    assert len({event.generation_request_id for event in harness.audit.events}) == 1


@pytest.mark.parametrize(
    ("authenticated", "csrf_valid", "status", "code"),
    [
        (False, True, 401, "authentication_required"),
        (True, False, 403, "csrf_validation_failed"),
    ],
)
def test_authentication_and_csrf_are_required_before_generation(
    authenticated: bool,
    csrf_valid: bool,
    status: int,
    code: str,
) -> None:
    harness = _harness(authenticated=authenticated, csrf_valid=csrf_valid)

    response = _post(harness)

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert harness.generator.calls == []
    assert harness.audit.events == []


def test_restricted_article_is_rejected_before_openai() -> None:
    harness = _harness(ai_allowed=False)

    response = _post(harness)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == ("article_ai_generation_not_permitted")
    assert harness.generator.calls == []
    assert harness.repository.saved == []
    assert [event.event_type for event in harness.audit.events] == [
        GenerationAuditEventType.GENERATION_STARTED,
        GenerationAuditEventType.RIGHTS_DENIED,
        GenerationAuditEventType.GENERATION_FAILED,
    ]


def test_invalid_preferences_are_rejected_by_the_frontend_contract() -> None:
    harness = _harness()

    response = _post(harness, tone="invented-tone", length="unbounded")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert harness.generator.calls == []
    assert harness.audit.events == []


def test_insufficient_permitted_context_fails_without_invention() -> None:
    harness = _harness(sufficient_source=False)

    response = _post(harness)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "insufficient_source_information"
    assert harness.generator.calls == []
    assert harness.repository.saved == []
    assert GenerationAuditEventType.VALIDATION_FAILED in {
        event.event_type for event in harness.audit.events
    }


def test_openai_unavailability_returns_a_controlled_failure_and_audit_event() -> None:
    harness = _harness(
        provider_outcome=OpenAIUnavailableFailure(
            code="openai_unavailable",
            message="The AI service is temporarily unavailable.",
            retryable=True,
            request_id="private-provider-request-id",
        )
    )

    response = _post(harness)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "openai_unavailable"
    assert "private-provider-request-id" not in response.text
    assert harness.repository.saved == []
    assert harness.usage.failed[0]["category"] == (
        GenerationErrorCategory.AI_SERVICE_UNAVAILABLE
    )
    assert harness.audit.events[-1].event_type == (
        GenerationAuditEventType.GENERATION_FAILED
    )


def test_malformed_provider_output_is_rejected_and_not_persisted() -> None:
    harness = _harness(provider_outcome=_provider_result(text="not-json"))

    response = _post(harness)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_generated_draft"
    assert harness.repository.saved == []
    assert GenerationAuditEventType.VALIDATION_FAILED in {
        event.event_type for event in harness.audit.events
    }


def test_shared_usage_limit_stops_openai_and_is_audited() -> None:
    harness = _harness(reject_usage=True)

    response = _post(harness)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "generation_limit_exceeded"
    assert response.headers["retry-after"] == "3600"
    assert harness.generator.calls == []
    assert GenerationAuditEventType.USAGE_REJECTED in {
        event.event_type for event in harness.audit.events
    }


def test_workflow_returns_only_a_private_draft_and_has_no_publish_route() -> None:
    harness = _harness()

    response = _post(harness)

    assert response.status_code == 201
    assert response.json()["status"] == "draft"
    assert response.json()["review_required"] is True
    paths = [
        route.path.lower()
        for route in harness.application.routes
        if hasattr(route, "path")
    ]
    assert all("publish" not in path for path in paths)
    assert all("linkedin.com" not in path for path in paths)
