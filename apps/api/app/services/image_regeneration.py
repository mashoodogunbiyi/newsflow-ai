"""Authenticated, rights-aware image regeneration orchestration."""

import hashlib
import logging
from collections.abc import Callable
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import SecretStr

from app.core.config import OpenAIConfigurationError
from app.core.logging_config import log_event
from app.models.ai import AITokenUsage
from app.models.article_rights import ArticleUseOperation
from app.models.generated_image import (
    GeneratedImageStorageRequest,
    ImageSafetyReviewStatus,
    StoredGeneratedImage,
)
from app.models.generation_usage import GenerationErrorCategory
from app.models.image_generation import (
    ImageGenerationErrorCategory,
    OpenAIImageGenerationRequest,
)
from app.models.image_prompt import ImagePromptRequest
from app.models.image_regeneration import (
    ImageRegenerationRequest,
    ImageRegenerationResponse,
)
from app.models.image_safety import ImageSafetyDecision, ImageSafetyRequest
from app.repositories.generated_images import (
    GeneratedImageRepository,
    GeneratedImageRepositoryError,
)
from app.repositories.image_regeneration import (
    ImageRegenerationRepository,
    ImageRegenerationRepositoryError,
)
from app.repositories.linkedin_generation import (
    LinkedInGenerationRepository,
    LinkedInGenerationRepositoryError,
)
from app.services.article_rights import ArticleRightsService
from app.services.generated_image_storage import GeneratedImageStorageService
from app.services.generation_usage import (
    GenerationUsageService,
    GenerationUsageUnavailable,
)
from app.services.image_prompt import (
    ImagePromptComposer,
    ImagePromptConstructionError,
    ImagePromptRightsError,
)
from app.services.image_safety import ImageSafetyService
from app.services.openai_image_service import OpenAIImageGenerationError

logger = logging.getLogger(__name__)


class ImageGenerator(Protocol):
    """Small OpenAI image boundary replaced by test doubles."""

    async def generate(self, request: OpenAIImageGenerationRequest): ...

    async def close(self) -> None: ...


ImageGeneratorFactory = Callable[[], ImageGenerator]


class ImageRegenerationError(RuntimeError):
    """Safe base failure for the image regeneration application service."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.safe_message = message
        super().__init__(message)


class ImageRegenerationNotFoundError(ImageRegenerationError):
    """Raised for both missing and differently owned private images."""


class ImageRegenerationRightsDeniedError(ImageRegenerationError):
    """Raised when current source rights no longer permit a derivative."""


class ImageRegenerationSafetyDeniedError(ImageRegenerationError):
    """Raised when the central image policy does not permit provider access."""


class ImageRegenerationContextError(ImageRegenerationError):
    """Raised when the image, draft, and article context no longer agree."""


class ImageRegenerationConfigurationError(ImageRegenerationError):
    """Raised when the backend image provider is not configured."""


class ImageRegenerationService:
    """Create a new private image version without changing its parent."""

    def __init__(
        self,
        *,
        images: GeneratedImageRepository,
        runs: ImageRegenerationRepository,
        drafts: LinkedInGenerationRepository,
        rights: ArticleRightsService,
        prompt_composer: ImagePromptComposer,
        safety: ImageSafetyService,
        image_generator_factory: ImageGeneratorFactory,
        storage: GeneratedImageStorageService,
        usage: GenerationUsageService | None = None,
    ) -> None:
        self._images = images
        self._runs = runs
        self._drafts = drafts
        self._rights = rights
        self._prompt_composer = prompt_composer
        self._safety = safety
        self._image_generator_factory = image_generator_factory
        self._storage = storage
        self._usage = usage

    async def regenerate(
        self,
        *,
        owner_id: UUID,
        parent_image_id: UUID,
        preferences: ImageRegenerationRequest,
        idempotency_key: str | None = None,
    ) -> ImageRegenerationResponse:
        """Generate, validate, and store one immutable child image version."""

        attempt = None
        generation_run_id: UUID | None = None
        parent = await self._images.get_for_owner(
            image_id=parent_image_id,
            owner_id=owner_id,
        )
        if parent is None:
            raise ImageRegenerationNotFoundError(
                code="image_not_found",
                message="The requested image was not found.",
            )

        draft = await self._drafts.get_draft_for_owner(
            owner_id=owner_id,
            draft_id=parent.generated_post_id,
        )
        source = await self._drafts.get_article(parent.article_id)
        if draft is None or source is None:
            raise ImageRegenerationNotFoundError(
                code="image_context_not_found",
                message="The requested image was not found.",
            )

        decision = await self._rights.can_use_article(
            article_id=parent.article_id,
            operation=ArticleUseOperation.USE_FOR_AI_GENERATION,
        )
        if not decision.allowed:
            raise ImageRegenerationRightsDeniedError(
                code="article_image_generation_not_permitted",
                message="Current source rights do not permit image regeneration.",
            )

        try:
            prompt = self._prompt_composer.compose(
                request=ImagePromptRequest(
                    article_id=parent.article_id,
                    generation_id=draft.generation_id,
                    style=preferences.style,
                    aspect_ratio=preferences.aspect_ratio,
                    composition=preferences.composition,
                ),
                article=source.article,
                rights_decision=decision,
                draft=draft,
            )
        except ImagePromptRightsError as exc:
            raise ImageRegenerationRightsDeniedError(
                code=exc.code,
                message=exc.safe_message,
            ) from exc
        except ImagePromptConstructionError as exc:
            raise ImageRegenerationContextError(
                code=exc.code,
                message=exc.safe_message,
            ) from exc

        safety = self._safety.evaluate(ImageSafetyRequest(prompt=prompt))
        if not safety.provider_call_allowed or safety.decision not in {
            ImageSafetyDecision.ALLOWED,
            ImageSafetyDecision.ALLOWED_WITH_RESTRICTIONS,
        }:
            raise ImageRegenerationSafetyDeniedError(
                code="image_regeneration_safety_denied",
                message="The image safety policy does not permit regeneration.",
            )

        request_marker = self._request_marker(parent_image_id, preferences)
        request_key = self._request_key(owner_id, idempotency_key)
        replay = await self._runs.get_completed_by_request_key(
            owner_id=owner_id,
            generated_post_id=parent.generated_post_id,
            request_key=request_key,
            request_marker=request_marker,
        )
        if replay is not None:
            stored = await self._images.get_for_owner(
                image_id=replay.image_id,
                owner_id=owner_id,
            )
            if stored is None or stored.parent_image_id != parent_image_id:
                raise ImageRegenerationNotFoundError(
                    code="image_version_not_found",
                    message="The requested image version was not found.",
                )
            return self._response(stored)

        try:
            if self._usage is not None:
                attempt = await self._usage.start_attempt(
                    owner_id=owner_id,
                    request_fingerprint=self._usage_fingerprint(
                        owner_id,
                        idempotency_key,
                        request_marker,
                        request_key,
                    ),
                )

            generated = await self._generate(
                owner_id=owner_id,
                prompt=prompt,
                safety=safety,
                decision=decision,
            )
            generation_run_id = await self._runs.create_succeeded_run(
                owner_id=owner_id,
                generated_post_id=parent.generated_post_id,
                request_key=request_key,
                request_marker=request_marker,
                generated=generated,
            )
            try:
                stored = await self._storage.store(
                    GeneratedImageStorageRequest(
                        owner_id=owner_id,
                        article_id=parent.article_id,
                        generated_post_id=parent.generated_post_id,
                        source_post_version_id=parent.source_post_version_id,
                        generation_run_id=generation_run_id,
                        parent_image_id=parent_image_id,
                        result=generated,
                        output_safety_status=ImageSafetyReviewStatus.PENDING,
                    )
                )
            except Exception as exc:
                try:
                    await self._runs.mark_run_failed(
                        generation_run_id=generation_run_id,
                        generated_post_id=parent.generated_post_id,
                        safe_error_code=getattr(
                            exc,
                            "code",
                            "image_regeneration_storage_failed",
                        ),
                    )
                except ImageRegenerationRepositoryError:
                    log_event(
                        logger,
                        logging.ERROR,
                        "image_regeneration_failure_state_not_recorded",
                        generation_run_id=str(generation_run_id),
                        status="failed",
                    )
                raise

            if self._usage is not None and attempt is not None:
                await self._usage.complete_attempt(
                    attempt=attempt,
                    generation_run_id=generation_run_id,
                    model_identifier=generated.model_identifier,
                    token_usage=AITokenUsage(
                        input_tokens=generated.usage_metadata.input_tokens,
                        output_tokens=generated.usage_metadata.output_tokens,
                        total_tokens=generated.usage_metadata.total_tokens,
                    ),
                )
                attempt = None
            log_event(
                logger,
                logging.INFO,
                "image_regeneration_completed",
                image_id=str(stored.id),
                parent_image_id=str(parent_image_id),
                generation_run_id=str(generation_run_id),
                status=stored.generation_status,
                counts={"regeneration_sequence": stored.regeneration_sequence},
            )
            return self._response(stored)
        except Exception as exc:
            if self._usage is not None and attempt is not None:
                try:
                    await self._usage.fail_attempt(
                        attempt=attempt,
                        category=self._error_category(exc),
                    )
                except GenerationUsageUnavailable:
                    log_event(
                        logger,
                        logging.ERROR,
                        "image_regeneration_usage_failure_not_recorded",
                        status="failed",
                    )
            raise

    async def _generate(self, *, owner_id, prompt, safety, decision):
        try:
            generator = self._image_generator_factory()
        except OpenAIConfigurationError as exc:
            raise ImageRegenerationConfigurationError(
                code="openai_image_configuration_unavailable",
                message="Image generation is not configured on this server.",
            ) from exc

        request = OpenAIImageGenerationRequest(
            request_id=uuid4(),
            prompt=prompt,
            safety_result=safety,
            rights_decision=decision,
            safety_identifier=SecretStr(
                "nf_" + hashlib.sha256(str(owner_id).encode()).hexdigest()
            ),
        )
        try:
            return await generator.generate(request)
        finally:
            try:
                await generator.close()
            except Exception:
                log_event(
                    logger,
                    logging.WARNING,
                    "image_generator_close_failed",
                    status="failed",
                )

    @staticmethod
    def _request_key(owner_id: UUID, supplied_key: str | None) -> str:
        raw_key = supplied_key or uuid4().hex
        return hashlib.sha256(f"{owner_id}:{raw_key}".encode()).hexdigest()

    @staticmethod
    def _request_marker(
        parent_image_id: UUID,
        preferences: ImageRegenerationRequest,
    ) -> str:
        digest = hashlib.sha256(
            (
                f"{parent_image_id}:{preferences.style.value}:"
                f"{preferences.aspect_ratio.value}:{preferences.composition.value}"
            ).encode()
        ).hexdigest()
        return f"Prompt content not retained. Regeneration fingerprint: {digest}"

    @staticmethod
    def _usage_fingerprint(
        owner_id: UUID,
        supplied_key: str | None,
        request_marker: str,
        request_key: str,
    ) -> str:
        if supplied_key is not None:
            return request_key
        return hashlib.sha256(f"{owner_id}:{request_marker}".encode()).hexdigest()

    @staticmethod
    def _response(stored: StoredGeneratedImage) -> ImageRegenerationResponse:
        assert stored.parent_image_id is not None
        return ImageRegenerationResponse(
            image_id=stored.id,
            parent_image_id=stored.parent_image_id,
            generation_id=stored.generation_run_id,
            generated_post_id=stored.generated_post_id,
            regeneration_sequence=stored.regeneration_sequence,
            safety_status=stored.safety_status,
            created_at=stored.created_at,
        )

    @staticmethod
    def _error_category(exc: Exception) -> GenerationErrorCategory:
        if isinstance(exc, OpenAIImageGenerationError):
            mapping = {
                ImageGenerationErrorCategory.AUTHENTICATION: (
                    GenerationErrorCategory.AI_AUTHENTICATION_ERROR
                ),
                ImageGenerationErrorCategory.RATE_LIMIT: (
                    GenerationErrorCategory.AI_RATE_LIMIT_ERROR
                ),
                ImageGenerationErrorCategory.QUOTA: (
                    GenerationErrorCategory.AI_QUOTA_ERROR
                ),
                ImageGenerationErrorCategory.TIMEOUT: (
                    GenerationErrorCategory.AI_TIMEOUT
                ),
                ImageGenerationErrorCategory.UNAVAILABLE: (
                    GenerationErrorCategory.AI_SERVICE_UNAVAILABLE
                ),
                ImageGenerationErrorCategory.INVALID_RESPONSE: (
                    GenerationErrorCategory.AI_INVALID_RESPONSE
                ),
                ImageGenerationErrorCategory.CONFIGURATION: (
                    GenerationErrorCategory.AI_CONFIGURATION_ERROR
                ),
                ImageGenerationErrorCategory.RIGHTS_DENIED: (
                    GenerationErrorCategory.GENERATION_RIGHTS_DENIED
                ),
                ImageGenerationErrorCategory.SAFETY_DENIED: (
                    GenerationErrorCategory.GENERATION_VALIDATION_ERROR
                ),
            }
            return mapping.get(
                exc.category,
                GenerationErrorCategory.GENERATION_VALIDATION_ERROR,
            )
        if isinstance(exc, ImageRegenerationConfigurationError):
            return GenerationErrorCategory.AI_CONFIGURATION_ERROR
        if isinstance(exc, ImageRegenerationRightsDeniedError):
            return GenerationErrorCategory.GENERATION_RIGHTS_DENIED
        if isinstance(exc, ImageRegenerationNotFoundError):
            return GenerationErrorCategory.GENERATION_ARTICLE_NOT_FOUND
        if isinstance(
            exc,
            (
                GeneratedImageRepositoryError,
                ImageRegenerationRepositoryError,
                LinkedInGenerationRepositoryError,
            ),
        ):
            return GenerationErrorCategory.GENERATION_STORAGE_ERROR
        return GenerationErrorCategory.GENERATION_VALIDATION_ERROR
