"""NFA-52 image regeneration workflow and API tests."""

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretBytes, SecretStr

from app.api.dependencies import require_csrf_authenticated_session
from app.api.routes.image_regeneration import router
from app.core.errors import ApplicationError, register_exception_handlers
from app.models.ai import AITokenUsage
from app.models.article_rights import (
    ArticleRightsDecision,
    RightsDecisionReason,
)
from app.models.generated_image import (
    GeneratedImageStorageRequest,
    ImageSafetyReviewStatus,
    StoredGeneratedImage,
    StoredGeneratedImageRecord,
)
from app.models.generation_usage import GenerationUsageAttempt
from app.models.grounding import GroundingResult, GroundingStatus
from app.models.image_generation import (
    GeneratedImageDataReference,
    ImageDataReferenceKind,
    ImageGenerationErrorCategory,
    ImageGenerationUsage,
    OpenAIImageGenerationResult,
)
from app.models.image_regeneration import (
    ImageRegenerationRequest,
    ImageRegenerationResponse,
)
from app.models.image_safety import ImageProviderSafetyCapabilities
from app.models.linkedin_generation import LinkedInDraft, LinkedInDraftSourceReference
from app.providers.fixture_provider import DEFAULT_FIXTURES
from app.providers.normalisation import ArticleNormalisationService
from app.repositories import AuthenticatedSession
from app.repositories.image_regeneration import (
    CompletedImageRegeneration,
    ImageRegenerationIdempotencyConflict,
)
from app.repositories.linkedin_generation import LinkedInGenerationArticle
from app.security import InMemoryRateLimiter
from app.services.generated_image_storage import GeneratedImageStorageWorkflowError
from app.services.generation_usage import GenerationLimitExceeded
from app.services.image_prompt import ImagePromptComposer
from app.services.image_regeneration import (
    ImageRegenerationNotFoundError,
    ImageRegenerationRightsDeniedError,
    ImageRegenerationSafetyDeniedError,
    ImageRegenerationService,
)
from app.services.image_safety import ImageSafetyService
from app.services.openai_image_service import OpenAIImageUnavailableError

OWNER_ID = UUID("52000000-0000-4000-8000-000000000001")
OTHER_OWNER_ID = UUID("52000000-0000-4000-8000-000000000002")
ARTICLE_ID = UUID("52000000-0000-4000-8000-000000000003")
SNAPSHOT_ID = UUID("52000000-0000-4000-8000-000000000004")
POST_ID = UUID("52000000-0000-4000-8000-000000000005")
POST_RUN_ID = UUID("52000000-0000-4000-8000-000000000006")
POST_VERSION_ID = UUID("52000000-0000-4000-8000-000000000007")
PARENT_IMAGE_ID = UUID("52000000-0000-4000-8000-000000000008")
PARENT_IMAGE_RUN_ID = UUID("52000000-0000-4000-8000-000000000009")
CHILD_IMAGE_ID = UUID("52000000-0000-4000-8000-000000000010")
CHILD_RUN_ID = UUID("52000000-0000-4000-8000-000000000011")
RIGHTS_ID = UUID("52000000-0000-4000-8000-000000000012")
SAFETY_ID = UUID("52000000-0000-4000-8000-000000000013")
NOW = datetime(2026, 10, 31, 18, 0, tzinfo=UTC)


def run(coroutine):
    return asyncio.run(coroutine)


def source_article(*, uncertain: bool = False):
    article = ArticleNormalisationService().normalise(DEFAULT_FIXTURES[0])
    if not uncertain:
        return article
    values = article.model_dump(mode="json")
    text = "Details remain uncertain in this synthetic developing report."
    values.update(
        {
            "title": "Synthetic uncertain technology report",
            "description": text,
            "permitted_content": {
                "status": "available",
                "content_type": "synthetic",
                "text": text,
                "ai_processing_allowed": True,
                "derivative_output_allowed": True,
            },
        }
    )
    return type(article).model_validate(values)


def draft_for(article) -> LinkedInDraft:
    return LinkedInDraft(
        draft_id=POST_ID,
        generation_id=POST_RUN_ID,
        owner_id=OWNER_ID,
        draft=(
            "A synthetic, source-grounded LinkedIn draft about a controlled "
            "technology demonstration."
        ),
        source=LinkedInDraftSourceReference(
            article_id=ARTICLE_ID,
            title=article.title,
            source_name=article.source_name,
            source_url=article.url,
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
        model_identifier="synthetic-text-model",
        token_usage=AITokenUsage(total_tokens=30),
        created_at=NOW,
    )


def parent_record() -> StoredGeneratedImageRecord:
    return StoredGeneratedImageRecord(
        id=PARENT_IMAGE_ID,
        request_id=UUID("52000000-0000-4000-8000-000000000014"),
        owner_id=OWNER_ID,
        article_id=ARTICLE_ID,
        article_snapshot_id=SNAPSHOT_ID,
        generated_post_id=POST_ID,
        source_post_version_id=POST_VERSION_ID,
        generation_run_id=PARENT_IMAGE_RUN_ID,
        parent_image_id=None,
        regeneration_sequence=0,
        storage_provider="private_test",
        storage_key=SecretStr("generated-images/parent.png"),
        mime_type="image/png",
        file_size_bytes=100,
        width=1024,
        height=1024,
        content_sha256="a" * 64,
        model_identifier="synthetic-image-model",
        prompt_version="image_prompt_v1",
        safety_policy_version="image_safety_v1",
        safety_status=ImageSafetyReviewStatus.PENDING,
        created_at=NOW,
    )


class MemoryImages:
    def __init__(self) -> None:
        self.records = {PARENT_IMAGE_ID: parent_record()}

    async def get_for_owner(self, *, image_id: UUID, owner_id: UUID):
        record = self.records.get(image_id)
        return record if record is not None and record.owner_id == owner_id else None

    async def get_by_request_id(self, *, request_id: UUID):
        return next(
            (item for item in self.records.values() if item.request_id == request_id),
            None,
        )

    async def save(self, image):
        raise AssertionError("The fake storage owns image creation in this test.")


class MemoryRuns:
    def __init__(self) -> None:
        self.entries: dict[str, dict[str, object]] = {}
        self.failed_codes: list[str] = []

    async def get_completed_by_request_key(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        request_key: str,
        request_marker: str,
    ):
        del owner_id, generated_post_id
        entry = self.entries.get(request_key)
        if entry is None:
            return None
        if entry["marker"] != request_marker or entry["image_id"] is None:
            raise ImageRegenerationIdempotencyConflict("synthetic conflict")
        return CompletedImageRegeneration(
            image_id=entry["image_id"],
            generation_run_id=entry["run_id"],
        )

    async def create_succeeded_run(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        request_key: str,
        request_marker: str,
        generated: OpenAIImageGenerationResult,
    ) -> UUID:
        del owner_id, generated_post_id, generated
        self.entries[request_key] = {
            "marker": request_marker,
            "run_id": CHILD_RUN_ID,
            "image_id": None,
        }
        return CHILD_RUN_ID

    async def mark_run_failed(
        self,
        *,
        generation_run_id: UUID,
        generated_post_id: UUID,
        safe_error_code: str,
    ) -> None:
        assert generation_run_id == CHILD_RUN_ID
        assert generated_post_id == POST_ID
        self.failed_codes.append(safe_error_code)

    def complete(self, image_id: UUID) -> None:
        entry = next(reversed(self.entries.values()))
        entry["image_id"] = image_id


class DraftRepository:
    def __init__(self, *, uncertain: bool = False) -> None:
        self.article = source_article(uncertain=uncertain)
        self.draft = draft_for(self.article)

    async def get_draft_for_owner(self, *, owner_id: UUID, draft_id: UUID):
        if owner_id == OWNER_ID and draft_id == POST_ID:
            return self.draft
        return None

    async def get_article(self, article_id: UUID):
        if article_id != ARTICLE_ID:
            return None
        return LinkedInGenerationArticle(
            article_id=ARTICLE_ID,
            snapshot_id=SNAPSHOT_ID,
            article=self.article,
        )


class RightsService:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls = 0

    async def can_use_article(self, *, article_id: UUID, operation):
        self.calls += 1
        return ArticleRightsDecision(
            article_id=article_id,
            operation=operation,
            allowed=self.allowed,
            reason=(
                RightsDecisionReason.PERMITTED
                if self.allowed
                else RightsDecisionReason.OPERATION_RESTRICTED
            ),
            rights_version_id=RIGHTS_ID,
            attribution_required=True,
            attribution_text="Source: NewsFlow AI synthetic fixture",
        )


class FakeGenerator:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls = 0
        self.closed = 0

    async def generate(self, request):
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        raw = b"synthetic-image-bytes"
        return OpenAIImageGenerationResult(
            request_id=request.request_id,
            model_identifier="gpt-image-2.5-flare",
            image_data_reference=GeneratedImageDataReference(
                kind=ImageDataReferenceKind.INLINE_BYTES,
                media_type="image/png",
                data=SecretBytes(raw),
                byte_length=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
            ),
            usage_metadata=ImageGenerationUsage(
                input_tokens=4,
                output_tokens=8,
                total_tokens=12,
            ),
            provider_request_id="synthetic-provider-request",
            prompt_version=request.prompt.prompt_version,
            safety_policy_version=request.safety_result.policy_version,
            safety_evaluation_id=request.safety_result.evaluation_id,
            rights_version_id=RIGHTS_ID,
            size=request.resolved_size,
            quality=request.quality,
            output_format=request.output_format,
            created_at=NOW,
        )

    async def close(self) -> None:
        self.closed += 1


class FakeStorage:
    def __init__(self, images: MemoryImages, runs: MemoryRuns) -> None:
        self.images = images
        self.runs = runs
        self.calls: list[GeneratedImageStorageRequest] = []
        self.failure: Exception | None = None

    async def store(self, request: GeneratedImageStorageRequest):
        self.calls.append(request)
        if self.failure is not None:
            raise self.failure
        parent = self.images.records[request.parent_image_id]
        record = StoredGeneratedImageRecord(
            id=CHILD_IMAGE_ID,
            request_id=request.result.request_id,
            owner_id=request.owner_id,
            article_id=request.article_id,
            article_snapshot_id=SNAPSHOT_ID,
            generated_post_id=request.generated_post_id,
            source_post_version_id=request.source_post_version_id,
            generation_run_id=request.generation_run_id,
            parent_image_id=request.parent_image_id,
            regeneration_sequence=parent.regeneration_sequence + 1,
            storage_provider="private_test",
            storage_key=SecretStr("generated-images/child.png"),
            mime_type="image/png",
            file_size_bytes=120,
            width=1536,
            height=1024,
            content_sha256="b" * 64,
            model_identifier=request.result.model_identifier,
            prompt_version=request.result.prompt_version,
            safety_policy_version=request.result.safety_policy_version,
            safety_status=request.output_safety_status,
            created_at=NOW,
        )
        self.images.records[record.id] = record
        self.runs.complete(record.id)
        return StoredGeneratedImage.from_record(record)


class FakeUsage:
    def __init__(self, *, limited: bool = False) -> None:
        self.limited = limited
        self.started = 0
        self.completed = 0
        self.failed = 0

    async def start_attempt(self, *, owner_id: UUID, request_fingerprint: str):
        if self.limited:
            raise GenerationLimitExceeded(
                code="generation_limit_exceeded",
                message="You have reached your current generation limit.",
                retry_after_seconds=60,
            )
        self.started += 1
        return GenerationUsageAttempt(
            id=UUID("52000000-0000-4000-8000-000000000015"),
            owner_id=owner_id,
            request_fingerprint=request_fingerprint,
            created_at=NOW,
            expires_at=NOW + timedelta(minutes=3),
        )

    async def complete_attempt(self, **kwargs) -> None:
        assert kwargs["generation_run_id"] == CHILD_RUN_ID
        assert kwargs["token_usage"].total_tokens == 12
        self.completed += 1

    async def fail_attempt(self, **kwargs) -> None:
        assert kwargs["category"] is not None
        self.failed += 1


def preferences() -> ImageRegenerationRequest:
    return ImageRegenerationRequest(
        style="minimalist_illustration",
        aspect_ratio="landscape",
        composition="focal_point_left",
    )


def service(
    *,
    allowed: bool = True,
    uncertain: bool = False,
    generator_failure: Exception | None = None,
    limited: bool = False,
):
    images = MemoryImages()
    runs = MemoryRuns()
    generator = FakeGenerator(failure=generator_failure)
    storage = FakeStorage(images, runs)
    usage = FakeUsage(limited=limited)
    selected = ImageRegenerationService(
        images=images,
        runs=runs,
        drafts=DraftRepository(uncertain=uncertain),
        rights=RightsService(allowed=allowed),
        prompt_composer=ImagePromptComposer(),
        safety=ImageSafetyService(
            provider_capabilities=ImageProviderSafetyCapabilities(
                prompt_moderation_available=True,
                output_moderation_available=True,
                strict_safety_level_available=True,
                content_credentials_available=True,
            ),
            id_factory=lambda: SAFETY_ID,
            clock=lambda: NOW,
        ),
        image_generator_factory=lambda: generator,
        storage=storage,
        usage=usage,
    )
    return selected, images, runs, generator, storage, usage


def test_successful_regeneration_preserves_parent_and_records_new_version() -> None:
    selected, images, _, generator, storage, usage = service()

    result = run(
        selected.regenerate(
            owner_id=OWNER_ID,
            parent_image_id=PARENT_IMAGE_ID,
            preferences=preferences(),
            idempotency_key="nfa52-success-001",
        )
    )

    assert result.image_id == CHILD_IMAGE_ID
    assert result.parent_image_id == PARENT_IMAGE_ID
    assert result.generation_id == CHILD_RUN_ID
    assert result.generated_post_id == POST_ID
    assert result.regeneration_sequence == 1
    assert result.status == "completed"
    assert result.is_ai_generated is True
    assert result.review_required is True
    assert PARENT_IMAGE_ID in images.records
    assert CHILD_IMAGE_ID in images.records
    assert generator.calls == 1
    assert generator.closed == 1
    assert storage.calls[0].source_post_version_id == POST_VERSION_ID
    assert storage.calls[0].output_safety_status == ImageSafetyReviewStatus.PENDING
    assert usage.completed == 1


def test_duplicate_request_returns_same_child_without_second_provider_call() -> None:
    selected, _, _, generator, _, usage = service()
    arguments = {
        "owner_id": OWNER_ID,
        "parent_image_id": PARENT_IMAGE_ID,
        "preferences": preferences(),
        "idempotency_key": "nfa52-duplicate-001",
    }

    first = run(selected.regenerate(**arguments))
    second = run(selected.regenerate(**arguments))

    assert second.image_id == first.image_id
    assert generator.calls == 1
    assert usage.started == 1


def test_missing_or_differently_owned_image_is_not_disclosed() -> None:
    selected, _, _, generator, _, _ = service()

    with pytest.raises(ImageRegenerationNotFoundError):
        run(
            selected.regenerate(
                owner_id=OTHER_OWNER_ID,
                parent_image_id=PARENT_IMAGE_ID,
                preferences=preferences(),
            )
        )

    assert generator.calls == 0


def test_current_rights_are_rechecked_before_provider_access() -> None:
    selected, _, _, generator, _, _ = service(allowed=False)

    with pytest.raises(ImageRegenerationRightsDeniedError):
        run(
            selected.regenerate(
                owner_id=OWNER_ID,
                parent_image_id=PARENT_IMAGE_ID,
                preferences=preferences(),
            )
        )

    assert generator.calls == 0


def test_uncertain_sensitive_context_is_stopped_by_reapplied_safety_policy() -> None:
    selected, _, _, generator, _, _ = service(uncertain=True)

    with pytest.raises(ImageRegenerationSafetyDeniedError):
        run(
            selected.regenerate(
                owner_id=OWNER_ID,
                parent_image_id=PARENT_IMAGE_ID,
                preferences=preferences(),
            )
        )

    assert generator.calls == 0


def test_provider_failure_preserves_original_and_records_failed_usage() -> None:
    failure = OpenAIImageUnavailableError(
        category=ImageGenerationErrorCategory.UNAVAILABLE,
        code="openai_image_unavailable",
        message="The image service is temporarily unavailable.",
        retryable=True,
    )
    selected, images, _, _, storage, usage = service(generator_failure=failure)

    with pytest.raises(OpenAIImageUnavailableError):
        run(
            selected.regenerate(
                owner_id=OWNER_ID,
                parent_image_id=PARENT_IMAGE_ID,
                preferences=preferences(),
            )
        )

    assert set(images.records) == {PARENT_IMAGE_ID}
    assert storage.calls == []
    assert usage.failed == 1


def test_storage_failure_marks_run_failed_without_false_image_success() -> None:
    selected, images, runs, _, storage, usage = service()
    storage.failure = GeneratedImageStorageWorkflowError(
        code="image_private_storage_failed",
        message="Generated image could not be stored safely.",
    )

    with pytest.raises(GeneratedImageStorageWorkflowError):
        run(
            selected.regenerate(
                owner_id=OWNER_ID,
                parent_image_id=PARENT_IMAGE_ID,
                preferences=preferences(),
            )
        )

    assert set(images.records) == {PARENT_IMAGE_ID}
    assert runs.failed_codes == ["image_private_storage_failed"]
    assert usage.failed == 1


def test_usage_limit_stops_provider_and_storage() -> None:
    selected, images, _, generator, storage, _ = service(limited=True)

    with pytest.raises(GenerationLimitExceeded):
        run(
            selected.regenerate(
                owner_id=OWNER_ID,
                parent_image_id=PARENT_IMAGE_ID,
                preferences=preferences(),
            )
        )

    assert set(images.records) == {PARENT_IMAGE_ID}
    assert generator.calls == 0
    assert storage.calls == []


class StubApiService:
    def __init__(self) -> None:
        self.calls = 0

    async def regenerate(self, **kwargs):
        self.calls += 1
        assert kwargs["owner_id"] == OWNER_ID
        assert kwargs["parent_image_id"] == PARENT_IMAGE_ID
        return ImageRegenerationResponse(
            image_id=CHILD_IMAGE_ID,
            parent_image_id=PARENT_IMAGE_ID,
            generation_id=CHILD_RUN_ID,
            generated_post_id=POST_ID,
            regeneration_sequence=1,
            safety_status=ImageSafetyReviewStatus.PENDING,
            created_at=NOW,
        )


def api_client(*, authenticated: bool = True):
    selected_service = StubApiService()
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router)
    application.state.image_regeneration_service = selected_service
    application.state.generation_rate_limiter = InMemoryRateLimiter(
        max_attempts=10,
        window_seconds=60,
    )

    async def session_override():
        if not authenticated:
            raise ApplicationError(
                status_code=401,
                code="authentication_required",
                message="Authentication is required.",
            )
        return AuthenticatedSession(
            user_id=OWNER_ID,
            email="nfa52@example.invalid",
            csrf_token_hash=b"x" * 32,
            expires_at=NOW + timedelta(hours=1),
        )

    application.dependency_overrides[require_csrf_authenticated_session] = (
        session_override
    )
    return TestClient(application), selected_service


def test_api_requires_authentication_and_rejects_invalid_preferences() -> None:
    unauthenticated, _ = api_client(authenticated=False)
    denied = unauthenticated.post(
        f"/api/images/{PARENT_IMAGE_ID}/regenerate",
        json={"style": "minimalist_illustration", "aspect_ratio": "landscape"},
    )
    authenticated, service = api_client()
    invalid = authenticated.post(
        f"/api/images/{PARENT_IMAGE_ID}/regenerate",
        json={"style": "photorealistic_news", "aspect_ratio": "unbounded"},
    )

    assert denied.status_code == 401
    assert invalid.status_code == 422
    assert service.calls == 0


def test_api_contract_returns_private_review_required_version_metadata() -> None:
    client, selected_service = api_client()
    response = client.post(
        f"/api/images/{PARENT_IMAGE_ID}/regenerate",
        headers={"Idempotency-Key": "nfa52-api-001"},
        json={
            "style": "minimalist_illustration",
            "aspect_ratio": "landscape",
            "composition": "focal_point_left",
        },
    )

    assert response.status_code == 201
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json() == {
        "image_id": str(CHILD_IMAGE_ID),
        "parent_image_id": str(PARENT_IMAGE_ID),
        "generation_id": str(CHILD_RUN_ID),
        "generated_post_id": str(POST_ID),
        "regeneration_sequence": 1,
        "status": "completed",
        "safety_status": "pending",
        "is_ai_generated": True,
        "review_required": True,
        "created_at": "2026-10-31T18:00:00Z",
    }
    assert selected_service.calls == 1
