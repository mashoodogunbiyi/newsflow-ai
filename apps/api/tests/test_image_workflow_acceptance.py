"""NFA-54 joined E5 image workflow acceptance tests using synthetic data."""

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr

from app.api.dependencies import (
    require_authenticated_session,
    require_csrf_authenticated_session,
)
from app.api.routes.image_delivery import router as image_delivery_router
from app.api.routes.image_regeneration import router as image_regeneration_router
from app.core.errors import register_exception_handlers
from app.core.image_generation_config import OpenAIImageGenerationConfiguration
from app.core.image_storage_config import ImageStorageConfiguration
from app.models.ai import AITokenUsage
from app.models.article_rights import (
    ArticleRightsDecision,
    ArticleUseOperation,
    RightsDecisionReason,
)
from app.models.generated_image import (
    GeneratedImagePersistenceResult,
    GeneratedImageStorageRequest,
    ImageSafetyReviewStatus,
    StoredGeneratedImageRecord,
)
from app.models.grounding import GroundingResult, GroundingStatus
from app.models.image_generation import OpenAIImageGenerationRequest
from app.models.image_prompt import (
    IllustrationStyle,
    ImageAspectRatio,
    ImageComposition,
    ImagePromptRequest,
)
from app.models.image_safety import (
    ImageProviderSafetyCapabilities,
    ImageSafetyDecision,
    ImageSafetyRequest,
)
from app.models.linkedin_generation import (
    LinkedInDraft,
    LinkedInDraftSourceReference,
)
from app.repositories import AuthenticatedSession
from app.repositories.image_regeneration import CompletedImageRegeneration
from app.repositories.linkedin_generation import LinkedInGenerationArticle
from app.security import InMemoryRateLimiter
from app.services.generated_image_storage import GeneratedImageStorageService
from app.services.image_delivery import ImageDeliveryService
from app.services.image_prompt import ImagePromptComposer, ImagePromptRightsError
from app.services.image_regeneration import ImageRegenerationService
from app.services.image_safety import ImageSafetyService
from app.services.image_storage import LocalPrivateImageStorage
from app.services.image_validation import (
    GeneratedImageValidationError,
    GeneratedImageValidationService,
)
from app.services.openai_image_service import (
    ImageGenerationSafetyDeniedError,
    OpenAIImageGenerationService,
)
from tests.support.image_workflow import (
    MockOpenAIImageClient,
    SyntheticImageFiles,
    synthetic_article,
)

NOW = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
OWNER_ID = UUID("54000000-0000-4000-8000-000000000001")
OTHER_OWNER_ID = UUID("54000000-0000-4000-8000-000000000002")
ARTICLE_ID = UUID("54000000-0000-4000-8000-000000000003")
SNAPSHOT_ID = UUID("54000000-0000-4000-8000-000000000004")
RIGHTS_ID = UUID("54000000-0000-4000-8000-000000000005")
POST_ID = UUID("54000000-0000-4000-8000-000000000006")
POST_RUN_ID = UUID("54000000-0000-4000-8000-000000000007")
INITIAL_IMAGE_RUN_ID = UUID("54000000-0000-4000-8000-000000000008")
INITIAL_REQUEST_ID = UUID("54000000-0000-4000-8000-000000000009")


def run(coroutine):
    return asyncio.run(coroutine)


def provider_configuration() -> OpenAIImageGenerationConfiguration:
    return OpenAIImageGenerationConfiguration(
        api_key=SecretStr("synthetic-test-key-not-a-real-credential"),
        model="gpt-image-2.5-flare",
        request_timeout_seconds=10,
        max_concurrent_requests=1,
        max_retries=0,
        retry_base_seconds=0,
        max_response_bytes=2_097_152,
        duplicate_cache_size=10,
    )


def rights_decision(*, allowed: bool = True) -> ArticleRightsDecision:
    return ArticleRightsDecision(
        article_id=ARTICLE_ID,
        operation=ArticleUseOperation.USE_FOR_AI_GENERATION,
        allowed=allowed,
        reason=(
            RightsDecisionReason.PERMITTED
            if allowed
            else RightsDecisionReason.OPERATION_RESTRICTED
        ),
        rights_version_id=RIGHTS_ID if allowed else None,
        attribution_required=True,
        attribution_text="Source: NewsFlow AI synthetic E5 fixture",
    )


def draft(article) -> LinkedInDraft:
    return LinkedInDraft(
        draft_id=POST_ID,
        generation_id=POST_RUN_ID,
        owner_id=OWNER_ID,
        draft=(
            "A synthetic LinkedIn draft about a controlled accessibility "
            "technology demonstration."
        ),
        source=LinkedInDraftSourceReference(
            article_id=ARTICLE_ID,
            title=article.title,
            source_name=article.source_name,
            source_url=article.url,
            attribution_text="Source: NewsFlow AI synthetic E5 fixture",
            rights_version_id=RIGHTS_ID,
        ),
        tone="professional",
        length="short",
        grounding=GroundingResult(
            status=GroundingStatus.PASSED_AUTOMATED_CHECKS,
            checked_claim_count=1,
        ),
        prompt_version="linkedin_post_v1",
        model_identifier="synthetic-text-model",
        token_usage=AITokenUsage(total_tokens=30),
        created_at=NOW,
    )


def safety_service() -> ImageSafetyService:
    return ImageSafetyService(
        provider_capabilities=ImageProviderSafetyCapabilities(
            prompt_moderation_available=True,
            output_moderation_available=True,
            strict_safety_level_available=True,
            content_credentials_available=True,
        ),
        clock=lambda: NOW,
        id_factory=uuid4,
    )


class MemoryImages:
    """In-memory metadata adapter used only by the joined fast test."""

    def __init__(self) -> None:
        self.records: dict[UUID, StoredGeneratedImageRecord] = {}

    async def get_by_request_id(self, *, request_id: UUID):
        return next(
            (item for item in self.records.values() if item.request_id == request_id),
            None,
        )

    async def get_for_owner(self, *, image_id: UUID, owner_id: UUID):
        item = self.records.get(image_id)
        return item if item is not None and item.owner_id == owner_id else None

    async def save(self, image) -> GeneratedImagePersistenceResult:
        existing = await self.get_by_request_id(request_id=image.request_id)
        if existing is not None:
            return GeneratedImagePersistenceResult(record=existing, created=False)
        sequence = sum(
            item.generated_post_id == image.generated_post_id
            for item in self.records.values()
        )
        record = StoredGeneratedImageRecord(
            **image.model_dump(exclude={"regeneration_sequence"}),
            article_snapshot_id=SNAPSHOT_ID,
            regeneration_sequence=sequence,
        )
        self.records[record.id] = record
        return GeneratedImagePersistenceResult(record=record, created=True)


class MemoryRuns:
    def __init__(self, images: MemoryImages) -> None:
        self.images = images
        self.entries: dict[str, tuple[str, UUID]] = {}
        self.failed: list[str] = []

    async def get_completed_by_request_key(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        request_key: str,
        request_marker: str,
    ):
        entry = self.entries.get(request_key)
        if entry is None or entry[0] != request_marker:
            return None
        run_id = entry[1]
        image = next(
            (
                item
                for item in self.images.records.values()
                if item.owner_id == owner_id
                and item.generated_post_id == generated_post_id
                and item.generation_run_id == run_id
            ),
            None,
        )
        return (
            None
            if image is None
            else CompletedImageRegeneration(
                image_id=image.id,
                generation_run_id=run_id,
            )
        )

    async def create_succeeded_run(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        request_key: str,
        request_marker: str,
        generated,
    ) -> UUID:
        del owner_id, generated_post_id, generated
        run_id = uuid4()
        self.entries[request_key] = (request_marker, run_id)
        return run_id

    async def mark_run_failed(
        self,
        *,
        generation_run_id: UUID,
        generated_post_id: UUID,
        safe_error_code: str,
    ) -> None:
        del generation_run_id, generated_post_id
        self.failed.append(safe_error_code)


class Drafts:
    def __init__(self, article, selected_draft: LinkedInDraft) -> None:
        self.article = article
        self.draft = selected_draft

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


class Rights:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed

    async def can_use_article(self, *, article_id: UUID, operation):
        assert article_id == ARTICLE_ID
        assert operation == ArticleUseOperation.USE_FOR_AI_GENERATION
        return rights_decision(allowed=self.allowed)


class RegenerationProviderFactory:
    def __init__(self, image_bytes: bytes) -> None:
        self.image_bytes = image_bytes
        self.clients: list[MockOpenAIImageClient] = []

    def __call__(self) -> OpenAIImageGenerationService:
        client = MockOpenAIImageClient(self.image_bytes)
        self.clients.append(client)
        return OpenAIImageGenerationService(
            configuration=provider_configuration(),
            client=client,
            clock=lambda: NOW,
        )

    @property
    def provider_calls(self) -> int:
        return sum(len(client.images.calls) for client in self.clients)


class ImageWorkflowHarness:
    def __init__(
        self,
        *,
        fixture_files: SyntheticImageFiles,
        private_root: Path,
        regeneration_bytes: bytes | None = None,
    ) -> None:
        self.article = synthetic_article()
        self.draft = draft(self.article)
        self.images = MemoryImages()
        self.storage_adapter = LocalPrivateImageStorage(private_root)
        self.storage = GeneratedImageStorageService(
            validator=GeneratedImageValidationService(
                ImageStorageConfiguration(
                    local_root=private_root,
                    max_file_bytes=1_048_576,
                )
            ),
            storage=self.storage_adapter,
            repository=self.images,
            clock=lambda: NOW,
        )
        self.initial_client = MockOpenAIImageClient(
            fixture_files.valid_png.read_bytes()
        )
        self.initial_provider = OpenAIImageGenerationService(
            configuration=provider_configuration(),
            client=self.initial_client,
            clock=lambda: NOW,
        )
        self.regeneration_factory = RegenerationProviderFactory(
            regeneration_bytes or fixture_files.alternate_png.read_bytes()
        )
        self.runs = MemoryRuns(self.images)
        self.regeneration = ImageRegenerationService(
            images=self.images,
            runs=self.runs,
            drafts=Drafts(self.article, self.draft),
            rights=Rights(),  # type: ignore[arg-type]
            prompt_composer=ImagePromptComposer(),
            safety=safety_service(),
            image_generator_factory=self.regeneration_factory,
            storage=self.storage,
        )
        self.delivery = ImageDeliveryService(
            images=self.images,
            storage=self.storage_adapter,
        )

    async def create_initial_image(self):
        prompt = ImagePromptComposer().compose(
            request=ImagePromptRequest(
                article_id=ARTICLE_ID,
                generation_id=self.draft.generation_id,
                style=IllustrationStyle.EDITORIAL_ILLUSTRATION,
                aspect_ratio=ImageAspectRatio.LANDSCAPE,
                composition=ImageComposition.BALANCED,
            ),
            article=self.article,
            rights_decision=rights_decision(),
            draft=self.draft,
        )
        safety = safety_service().evaluate(ImageSafetyRequest(prompt=prompt))
        generated = await self.initial_provider.generate(
            OpenAIImageGenerationRequest(
                request_id=INITIAL_REQUEST_ID,
                prompt=prompt,
                safety_result=safety,
                rights_decision=rights_decision(),
                safety_identifier=SecretStr(
                    "nf_" + hashlib.sha256(str(OWNER_ID).encode()).hexdigest()
                ),
            )
        )
        return await self.storage.store(
            GeneratedImageStorageRequest(
                owner_id=OWNER_ID,
                article_id=ARTICLE_ID,
                generated_post_id=POST_ID,
                generation_run_id=INITIAL_IMAGE_RUN_ID,
                result=generated,
                output_safety_status=ImageSafetyReviewStatus.APPROVED,
            )
        )

    def client(self, *, owner_id: UUID = OWNER_ID) -> TestClient:
        application = FastAPI()
        register_exception_handlers(application)
        application.include_router(image_delivery_router)
        application.include_router(image_regeneration_router)
        application.state.image_delivery_service = self.delivery
        application.state.image_regeneration_service = self.regeneration
        application.state.generation_rate_limiter = InMemoryRateLimiter(
            max_attempts=20,
            window_seconds=60,
        )

        async def session() -> AuthenticatedSession:
            return AuthenticatedSession(
                user_id=owner_id,
                email="nfa54@example.invalid",
                csrf_token_hash=b"x" * 32,
                expires_at=NOW + timedelta(hours=1),
            )

        application.dependency_overrides[require_authenticated_session] = session
        application.dependency_overrides[require_csrf_authenticated_session] = session
        return TestClient(application)


def image_colour(content: bytes) -> tuple[int, int, int]:
    with Image.open(BytesIO(content)) as image:
        image.load()
        assert image.size == (1536, 1024)
        return image.convert("RGB").getpixel((0, 0))


def test_complete_mocked_image_workflow_preserves_versions_and_private_delivery(
    image_workflow_files: SyntheticImageFiles,
    tmp_path: Path,
) -> None:
    harness = ImageWorkflowHarness(
        fixture_files=image_workflow_files,
        private_root=tmp_path / "private-storage",
    )
    parent = run(harness.create_initial_image())
    client = harness.client()

    parent_metadata = client.get(f"/api/images/{parent.id}")
    parent_content = client.get(f"/api/images/{parent.id}/content")
    regenerated = client.post(
        f"/api/images/{parent.id}/regenerate",
        headers={"Idempotency-Key": "nfa54-regeneration-001"},
        json={
            "style": "minimalist_illustration",
            "aspect_ratio": "landscape",
            "composition": "focal_point_left",
        },
    )
    duplicate = client.post(
        f"/api/images/{parent.id}/regenerate",
        headers={"Idempotency-Key": "nfa54-regeneration-001"},
        json={
            "style": "minimalist_illustration",
            "aspect_ratio": "landscape",
            "composition": "focal_point_left",
        },
    )

    assert parent_metadata.status_code == 200
    assert parent_metadata.json()["is_ai_generated"] is True
    assert parent_metadata.json()["ai_disclosure_required"] is True
    assert parent_content.status_code == 200
    assert image_colour(parent_content.content) == (17, 91, 121)
    assert regenerated.status_code == 201
    assert duplicate.status_code == 201
    assert duplicate.json()["image_id"] == regenerated.json()["image_id"]
    assert harness.initial_client.images.calls
    assert harness.regeneration_factory.provider_calls == 1

    child_id = UUID(regenerated.json()["image_id"])
    child_content = client.get(f"/api/images/{child_id}/download")
    parent_after = client.get(f"/api/images/{parent.id}/content")
    assert child_content.status_code == 200
    assert image_colour(child_content.content) == (93, 44, 123)
    assert child_content.headers["content-type"] == "image/png"
    assert child_content.headers["content-disposition"].startswith("attachment;")
    assert parent_after.status_code == 200
    assert image_colour(parent_after.content) == (17, 91, 121)
    assert set(harness.images.records) == {parent.id, child_id}
    assert harness.images.records[child_id].parent_image_id == parent.id
    assert harness.images.records[child_id].regeneration_sequence == 1

    foreign = harness.client(owner_id=OTHER_OWNER_ID).get(
        f"/api/images/{parent.id}/content"
    )
    assert foreign.status_code == 404
    assert "storage_key" not in parent_metadata.text


def test_restricted_source_and_documentary_fabrication_stop_before_provider(
    image_workflow_files: SyntheticImageFiles,
) -> None:
    restricted = synthetic_article("restricted_source", processing_allowed=False)
    with pytest.raises(ImagePromptRightsError):
        ImagePromptComposer().compose(
            request=ImagePromptRequest(
                article_id=ARTICLE_ID,
                style=IllustrationStyle.EDITORIAL_ILLUSTRATION,
                aspect_ratio=ImageAspectRatio.LANDSCAPE,
            ),
            article=restricted,
            rights_decision=rights_decision(),
        )

    sensitive = synthetic_article("sensitive_conflict")
    prompt = ImagePromptComposer().compose(
        request=ImagePromptRequest(
            article_id=ARTICLE_ID,
            style=IllustrationStyle.EDITORIAL_ILLUSTRATION,
            aspect_ratio=ImageAspectRatio.LANDSCAPE,
        ),
        article=sensitive,
        rights_decision=rights_decision(),
    )
    safety = safety_service().evaluate(
        ImageSafetyRequest(
            prompt=prompt,
            user_request=SecretStr(
                "Create a realistic news photograph showing the exact attack."
            ),
        )
    )
    client = MockOpenAIImageClient(image_workflow_files.valid_png.read_bytes())
    provider = OpenAIImageGenerationService(
        configuration=provider_configuration(),
        client=client,
    )

    assert safety.decision == ImageSafetyDecision.REJECTED
    assert safety.provider_call_allowed is False
    with pytest.raises(ImageGenerationSafetyDeniedError):
        run(
            provider.generate(
                OpenAIImageGenerationRequest(
                    request_id=uuid4(),
                    prompt=prompt,
                    safety_result=safety,
                    rights_decision=rights_decision(),
                )
            )
        )
    assert client.images.calls == []


def test_valid_invalid_corrupt_and_oversized_fixtures_are_deterministic(
    image_workflow_files: SyntheticImageFiles,
    tmp_path: Path,
) -> None:
    validator = GeneratedImageValidationService(
        ImageStorageConfiguration(
            local_root=tmp_path / "unused-private-storage",
            max_file_bytes=1_048_576,
        )
    )

    valid = validator.validate(
        image_workflow_files.valid_png.read_bytes(),
        expected_media_type="image/png",
        expected_dimensions=(1536, 1024),
    )
    assert valid.mime_type == "image/png"
    assert valid.metadata_removed is True

    for path in (
        image_workflow_files.invalid_binary,
        image_workflow_files.corrupt_png,
        image_workflow_files.oversized_binary,
    ):
        with pytest.raises(GeneratedImageValidationError):
            validator.validate(
                path.read_bytes(),
                expected_media_type="image/png",
                expected_dimensions=(1536, 1024),
            )


def test_failed_regeneration_keeps_original_available(
    image_workflow_files: SyntheticImageFiles,
    tmp_path: Path,
) -> None:
    harness = ImageWorkflowHarness(
        fixture_files=image_workflow_files,
        private_root=tmp_path / "private-storage",
        regeneration_bytes=image_workflow_files.corrupt_png.read_bytes(),
    )
    parent = run(harness.create_initial_image())
    client = harness.client()

    failed = client.post(
        f"/api/images/{parent.id}/regenerate",
        headers={"Idempotency-Key": "nfa54-corrupt-output-001"},
        json={
            "style": "minimalist_illustration",
            "aspect_ratio": "landscape",
            "composition": "balanced",
        },
    )
    original = client.get(f"/api/images/{parent.id}/content")

    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "image_corrupt"
    assert original.status_code == 200
    assert image_colour(original.content) == (17, 91, 121)
    assert set(harness.images.records) == {parent.id}
    assert harness.runs.failed == ["image_corrupt"]
