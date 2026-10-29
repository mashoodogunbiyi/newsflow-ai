"""NFA-40 LinkedIn draft generation orchestration tests."""

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.models.ai import AITextGenerationResult, AITokenUsage
from app.models.article_rights import (
    ArticleRightsDecision,
    ArticleUseOperation,
    RightsDecisionReason,
)
from app.models.generation_preferences import (
    LinkedInGenerationPreferences,
    LinkedInPostLength,
    LinkedInTone,
)
from app.models.linkedin_generation import LinkedInDraft
from app.providers.fixture_provider import DEFAULT_FIXTURES
from app.providers.models import NewsArticle
from app.providers.normalisation import ArticleNormalisationService
from app.repositories.linkedin_generation import LinkedInGenerationArticle
from app.services.authorization import PrivateResourceNotFoundError
from app.services.linkedin_generation import (
    GenerationArticleNotFoundError,
    GenerationInsufficientSourceError,
    GenerationRightsDeniedError,
    InvalidGeneratedDraftError,
    LinkedInGenerationService,
)
from app.services.openai_service import OpenAITimeoutFailure

NOW = datetime(2026, 10, 29, 18, 0, tzinfo=UTC)
OWNER_ID = UUID("40000000-0000-4000-8000-000000000001")
OTHER_OWNER_ID = UUID("40000000-0000-4000-8000-000000000002")
ARTICLE_ID = UUID("40000000-0000-4000-8000-000000000003")
SNAPSHOT_ID = UUID("40000000-0000-4000-8000-000000000004")
RIGHTS_VERSION_ID = UUID("40000000-0000-4000-8000-000000000005")


def run(coroutine):
    return asyncio.run(coroutine)


def source_article(**changes: object) -> NewsArticle:
    article = ArticleNormalisationService().normalise(DEFAULT_FIXTURES[0])
    values = article.model_dump(mode="json")
    values.update(changes)
    return NewsArticle.model_validate(values)


def source(**changes: object) -> LinkedInGenerationArticle:
    return LinkedInGenerationArticle(
        article_id=ARTICLE_ID,
        snapshot_id=SNAPSHOT_ID,
        article=source_article(**changes),
    )


def draft_text(words: int = 80) -> str:
    return " ".join(f"synthetic{number}" for number in range(words))


def provider_result(text: str | None = None) -> AITextGenerationResult:
    output = {
        "status": "ready",
        "draft": text or draft_text(),
        "insufficiency_reason": None,
    }
    return AITextGenerationResult(
        text=json.dumps(output),
        model="test-openai-model",
        response_id="resp_nfa40",
        request_id="req_nfa40",
        usage=AITokenUsage(
            input_tokens=120,
            output_tokens=100,
            total_tokens=220,
        ),
    )


class FakeRightsService:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls: list[tuple[UUID, ArticleUseOperation]] = []

    async def can_use_article(
        self,
        *,
        article_id: UUID,
        operation: ArticleUseOperation,
        checked_at: datetime | None = None,
    ) -> ArticleRightsDecision:
        del checked_at
        self.calls.append((article_id, operation))
        permitted = self.allowed or operation == ArticleUseOperation.DISPLAY_METADATA
        return ArticleRightsDecision(
            article_id=article_id,
            operation=operation,
            allowed=permitted,
            reason=(
                RightsDecisionReason.PERMITTED
                if permitted
                else RightsDecisionReason.OPERATION_RESTRICTED
            ),
            rights_version_id=RIGHTS_VERSION_ID if permitted else None,
            attribution_required=True,
            attribution_text=(
                "Source: NewsFlow AI synthetic fixture - not live news"
                if permitted
                else None
            ),
        )


class FakeGenerator:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls: list[object] = []
        self.closed = False

    async def generate_text(self, request: object) -> AITextGenerationResult:
        self.calls.append(request)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        assert isinstance(self.outcome, AITextGenerationResult)
        return self.outcome

    async def close(self) -> None:
        self.closed = True


class InMemoryGenerationRepository:
    def __init__(self, selected: LinkedInGenerationArticle | None) -> None:
        self.selected = selected
        self.saved: dict[UUID, LinkedInDraft] = {}
        self.requests: dict[tuple[UUID, str], tuple[str, UUID]] = {}
        self.save_calls: list[dict[str, object]] = []

    async def get_article(
        self,
        article_id: UUID,
    ) -> LinkedInGenerationArticle | None:
        if self.selected is None or article_id != self.selected.article_id:
            return None
        return self.selected

    async def get_draft_by_request_key(
        self,
        *,
        owner_id: UUID,
        request_key: str,
        request_marker: str,
    ) -> LinkedInDraft | None:
        existing = self.requests.get((owner_id, request_key))
        if existing is None:
            return None
        marker, draft_id = existing
        if marker != request_marker:
            raise AssertionError("Synthetic idempotency conflict.")
        return self.saved[draft_id]

    async def save_draft(self, **values: object) -> LinkedInDraft:
        self.save_calls.append(values)
        draft_id = uuid4()
        generated = values["generated"]
        preferences = values["preferences"]
        source_reference = values["source_reference"]
        assert isinstance(generated, AITextGenerationResult)
        assert isinstance(preferences, LinkedInGenerationPreferences)
        item = LinkedInDraft(
            draft_id=draft_id,
            generation_id=uuid4(),
            owner_id=values["owner_id"],
            draft=values["draft_text"],
            source=source_reference,
            tone=preferences.tone,
            length=preferences.post_length,
            prompt_version=values["prompt_version"],
            model_identifier=generated.model,
            token_usage=generated.usage,
            created_at=NOW,
        )
        self.saved[draft_id] = item
        self.requests[(values["owner_id"], values["request_key"])] = (
            values["request_marker"],
            draft_id,
        )
        return item

    async def get_draft_for_owner(
        self,
        *,
        owner_id: UUID,
        draft_id: UUID,
    ) -> LinkedInDraft | None:
        item = self.saved.get(draft_id)
        return item if item is not None and item.owner_id == owner_id else None


def service(
    *,
    selected: LinkedInGenerationArticle | None = None,
    allowed: bool = True,
    outcome: object | None = None,
):
    repository = InMemoryGenerationRepository(selected or source())
    rights = FakeRightsService(allowed=allowed)
    generator = FakeGenerator(outcome or provider_result())
    created: list[FakeGenerator] = []

    def factory() -> FakeGenerator:
        created.append(generator)
        return generator

    application_service = LinkedInGenerationService(
        repository=repository,
        rights=rights,  # type: ignore[arg-type]
        openai_factory=factory,
    )
    return application_service, repository, rights, generator, created


def test_success_connects_rights_prompt_openai_validation_and_persistence() -> None:
    application_service, repository, rights, generator, _ = service()

    result = run(
        application_service.generate_draft(
            owner_id=OWNER_ID,
            article_id=ARTICLE_ID,
            preferences=LinkedInGenerationPreferences(
                tone=LinkedInTone.PROFESSIONAL,
                post_length=LinkedInPostLength.SHORT,
            ),
            idempotency_key="request-nfa40-success",
        ),
    )

    assert result.owner_id == OWNER_ID
    assert result.status == "draft"
    assert result.review_required is True
    assert result.source.article_id == ARTICLE_ID
    assert result.source.rights_version_id == RIGHTS_VERSION_ID
    assert result.source.source_url == source().article.url
    assert result.draft == draft_text()
    assert result.prompt_version == "linkedin_post_v1"
    assert result.token_usage.total_tokens == 220
    assert rights.calls == [
        (ARTICLE_ID, ArticleUseOperation.DISPLAY_METADATA),
        (ARTICLE_ID, ArticleUseOperation.USE_FOR_AI_GENERATION),
    ]
    request = generator.calls[0]
    assert request.json_schema_format.name == "linkedin_post_draft"
    assert request.json_schema_format.schema_definition["additionalProperties"] is False
    assert "Tone: professional" in request.instructions.get_secret_value()
    assert repository.save_calls[0]["word_count"] == 80
    assert generator.closed is True


def test_missing_article_and_denied_rights_fail_before_openai() -> None:
    missing_service, _, _, _, missing_created = service()
    missing_service._repository.selected = None  # type: ignore[attr-defined]

    with pytest.raises(GenerationArticleNotFoundError):
        run(
            missing_service.generate_draft(
                owner_id=OWNER_ID,
                article_id=ARTICLE_ID,
                preferences=LinkedInGenerationPreferences(),
            )
        )

    denied_service, _, _, _, denied_created = service(allowed=False)
    with pytest.raises(GenerationRightsDeniedError):
        run(
            denied_service.generate_draft(
                owner_id=OWNER_ID,
                article_id=ARTICLE_ID,
                preferences=LinkedInGenerationPreferences(),
            )
        )

    assert missing_created == []
    assert denied_created == []


def test_missing_permitted_information_fails_before_openai() -> None:
    unavailable = source(
        description=None,
        permitted_content={
            "status": "missing",
            "content_type": "none",
            "text": None,
            "ai_processing_allowed": False,
            "derivative_output_allowed": False,
        },
    )
    application_service, _, _, _, created = service(selected=unavailable)

    with pytest.raises(GenerationInsufficientSourceError):
        run(
            application_service.generate_draft(
                owner_id=OWNER_ID,
                article_id=ARTICLE_ID,
                preferences=LinkedInGenerationPreferences(),
            )
        )

    assert created == []


@pytest.mark.parametrize(
    ("provider_text", "expected_code"),
    [
        ("not-json", "invalid_generated_draft"),
        (
            json.dumps(
                {
                    "status": "ready",
                    "draft": "",
                    "insufficiency_reason": None,
                }
            ),
            "invalid_generated_draft",
        ),
        (
            json.dumps(
                {
                    "status": "ready",
                    "draft": draft_text(79),
                    "insufficiency_reason": None,
                }
            ),
            "generated_draft_length_invalid",
        ),
    ],
)
def test_malformed_empty_and_out_of_range_outputs_are_rejected(
    provider_text: str,
    expected_code: str,
) -> None:
    result = provider_result().model_copy(update={"text": provider_text})
    application_service, repository, _, generator, _ = service(outcome=result)

    with pytest.raises(InvalidGeneratedDraftError) as error:
        run(
            application_service.generate_draft(
                owner_id=OWNER_ID,
                article_id=ARTICLE_ID,
                preferences=LinkedInGenerationPreferences(
                    post_length=LinkedInPostLength.SHORT
                ),
            )
        )

    assert error.value.code == expected_code
    assert repository.save_calls == []
    assert generator.closed is True


def test_model_insufficiency_and_provider_timeout_are_controlled() -> None:
    insufficient = provider_result().model_copy(
        update={
            "text": json.dumps(
                {
                    "status": "insufficient_source_information",
                    "draft": "",
                    "insufficiency_reason": "More authorised detail is required.",
                }
            )
        }
    )
    application_service, _, _, generator, _ = service(outcome=insufficient)
    with pytest.raises(GenerationInsufficientSourceError):
        run(
            application_service.generate_draft(
                owner_id=OWNER_ID,
                article_id=ARTICLE_ID,
                preferences=LinkedInGenerationPreferences(),
            )
        )
    assert generator.closed is True

    timeout = OpenAITimeoutFailure(
        code="openai_timeout",
        message="The AI service request timed out.",
        retryable=True,
    )
    timeout_service, _, _, timeout_generator, _ = service(outcome=timeout)
    with pytest.raises(OpenAITimeoutFailure):
        run(
            timeout_service.generate_draft(
                owner_id=OWNER_ID,
                article_id=ARTICLE_ID,
                preferences=LinkedInGenerationPreferences(),
            )
        )
    assert timeout_generator.closed is True


def test_idempotency_reuses_draft_and_private_reads_enforce_owner() -> None:
    application_service, repository, _, generator, created = service()
    values = {
        "owner_id": OWNER_ID,
        "article_id": ARTICLE_ID,
        "preferences": LinkedInGenerationPreferences(
            post_length=LinkedInPostLength.SHORT
        ),
        "idempotency_key": "same-client-request",
    }

    first = run(application_service.generate_draft(**values))
    second = run(application_service.generate_draft(**values))
    owned = run(
        application_service.get_draft(
            owner_id=OWNER_ID,
            draft_id=first.draft_id,
        )
    )

    assert second.draft_id == first.draft_id
    assert owned.draft_id == first.draft_id
    assert len(generator.calls) == 1
    assert len(created) == 1
    assert len(repository.save_calls) == 1
    with pytest.raises(PrivateResourceNotFoundError):
        run(
            application_service.get_draft(
                owner_id=OTHER_OWNER_ID,
                draft_id=first.draft_id,
            )
        )
