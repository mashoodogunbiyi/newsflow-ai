"""Authenticated, rights-aware LinkedIn draft generation orchestration."""

import hashlib
import logging
import re
from collections.abc import Callable
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.core.config import OpenAIConfigurationError
from app.core.logging_config import log_event
from app.models.ai import AIJsonSchemaFormat, AITextGenerationRequest
from app.models.article_rights import ArticleUseOperation
from app.models.generation_preferences import (
    LinkedInGenerationPreferences,
    LinkedInPromptPackage,
)
from app.models.generation_usage import GenerationErrorCategory
from app.models.grounding import GroundingStatus
from app.models.linkedin_generation import (
    LinkedInDraft,
    LinkedInDraftSourceReference,
    LinkedInModelOutput,
)
from app.prompts.linkedin_post import LINKEDIN_LENGTH_SPECIFICATIONS
from app.repositories.linkedin_generation import (
    LinkedInGenerationArticle,
    LinkedInGenerationRepository,
    LinkedInGenerationRepositoryError,
)
from app.services.article_rights import ArticleRightsService
from app.services.authorization import require_owned_resource
from app.services.generation_usage import (
    GenerationUsageService,
    GenerationUsageUnavailable,
)
from app.services.generation_validator import GenerationGroundingValidator
from app.services.openai_service import (
    OpenAIAuthenticationFailure,
    OpenAIInvalidResponseError,
    OpenAIQuotaFailure,
    OpenAIRateLimitFailure,
    OpenAIServiceError,
    OpenAITimeoutFailure,
    OpenAIUnavailableFailure,
)
from app.services.prompt_builder import (
    ArticlePromptRightsError,
    InsufficientSourceInformationError,
    LinkedInPromptBuilder,
)

logger = logging.getLogger(__name__)
WORD_PATTERN = re.compile(r"\b[\w'-]+\b", re.UNICODE)

LINKEDIN_DRAFT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["ready", "insufficient_source_information"],
        },
        "draft": {"type": "string"},
        "insufficiency_reason": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
    "required": ["status", "draft", "insufficiency_reason"],
    "additionalProperties": False,
}


class AITextGenerator(Protocol):
    """Small provider boundary used by this workflow and isolated tests."""

    async def generate_text(
        self,
        request: AITextGenerationRequest,
    ): ...

    async def close(self) -> None: ...


AITextGeneratorFactory = Callable[[], AITextGenerator]


class LinkedInGenerationError(RuntimeError):
    """Safe base failure for the generation application service."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.safe_message = message
        super().__init__(message)


class GenerationArticleNotFoundError(LinkedInGenerationError):
    """Raised when an article is absent or not available to the catalogue user."""


class GenerationRightsDeniedError(LinkedInGenerationError):
    """Raised before provider access when current rights deny AI processing."""


class GenerationInsufficientSourceError(LinkedInGenerationError):
    """Raised when authorised source information cannot support the draft."""


class InvalidGeneratedDraftError(LinkedInGenerationError):
    """Raised when the model output is empty, malformed, or outside limits."""


class GenerationProviderConfigurationError(LinkedInGenerationError):
    """Raised when the server-side OpenAI integration is not configured."""


class LinkedInGenerationService:
    """Coordinate article, rights, prompt, OpenAI, validation, and persistence."""

    def __init__(
        self,
        *,
        repository: LinkedInGenerationRepository,
        rights: ArticleRightsService,
        openai_factory: AITextGeneratorFactory,
        usage: GenerationUsageService | None = None,
        prompt_builder: LinkedInPromptBuilder | None = None,
        grounding_validator: GenerationGroundingValidator | None = None,
    ) -> None:
        self._repository = repository
        self._rights = rights
        self._openai_factory = openai_factory
        self._usage = usage
        self._prompt_builder = prompt_builder or LinkedInPromptBuilder()
        self._grounding_validator = (
            grounding_validator or GenerationGroundingValidator()
        )

    async def generate_draft(
        self,
        *,
        owner_id: UUID,
        article_id: UUID,
        preferences: LinkedInGenerationPreferences,
        idempotency_key: str | None = None,
    ) -> LinkedInDraft:
        """Return a private human-review draft without publishing it anywhere."""

        source = await self._repository.get_article(article_id)
        if source is None:
            raise GenerationArticleNotFoundError(
                code="generation_article_not_found",
                message="The selected article was not found.",
            )

        access_decision = await self._rights.can_use_article(
            article_id=article_id,
            operation=ArticleUseOperation.DISPLAY_METADATA,
        )
        if not access_decision.allowed:
            raise GenerationArticleNotFoundError(
                code="generation_article_not_found",
                message="The selected article was not found.",
            )

        decision = await self._rights.can_use_article(
            article_id=article_id,
            operation=ArticleUseOperation.USE_FOR_AI_GENERATION,
        )
        if not decision.allowed:
            raise GenerationRightsDeniedError(
                code="article_ai_generation_not_permitted",
                message="The selected article is not permitted for AI generation.",
            )

        try:
            package = self._prompt_builder.build(
                article_id=article_id,
                article=source.article,
                rights_decision=decision,
                preferences=preferences,
            )
        except ArticlePromptRightsError as exc:
            raise GenerationRightsDeniedError(
                code=exc.code,
                message=exc.safe_message,
            ) from exc
        except InsufficientSourceInformationError as exc:
            raise GenerationInsufficientSourceError(
                code=exc.code,
                message=exc.safe_message,
            ) from exc

        request_marker = self._request_marker(
            article_id=article_id,
            preferences=preferences,
            prompt_version=package.prompt_version,
        )
        request_key = self._request_key(owner_id, idempotency_key)
        existing = await self._repository.get_draft_by_request_key(
            owner_id=owner_id,
            request_key=request_key,
            request_marker=request_marker,
        )
        if existing is not None:
            return existing

        attempt = None
        if self._usage is not None:
            attempt = await self._usage.start_attempt(
                owner_id=owner_id,
                request_fingerprint=request_key,
            )

        try:
            draft = await self._generate_new_draft(
                owner_id=owner_id,
                source=source,
                package=package,
                preferences=preferences,
                request_key=request_key,
                request_marker=request_marker,
            )
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
                        "generation_usage_failure_not_recorded",
                        status="failed",
                        error_category=self._error_category(exc).value,
                    )
            raise

        if self._usage is not None and attempt is not None:
            await self._usage.complete_attempt(
                attempt=attempt,
                generation_run_id=draft.generation_id,
                model_identifier=draft.model_identifier,
                token_usage=draft.token_usage,
            )
        return draft

    async def _generate_new_draft(
        self,
        *,
        owner_id: UUID,
        source: LinkedInGenerationArticle,
        package: LinkedInPromptPackage,
        preferences: LinkedInGenerationPreferences,
        request_key: str,
        request_marker: str,
    ) -> LinkedInDraft:
        """Call the provider, validate its result, and persist one new draft."""

        generation_request = package.generation_request.model_copy(
            update={
                "json_schema_format": AIJsonSchemaFormat(
                    name="linkedin_post_draft",
                    schema_definition=LINKEDIN_DRAFT_JSON_SCHEMA,
                )
            }
        )
        try:
            generator = self._openai_factory()
        except OpenAIConfigurationError as exc:
            raise GenerationProviderConfigurationError(
                code="openai_configuration_unavailable",
                message="AI generation is not configured on this server.",
            ) from exc

        try:
            generated = await generator.generate_text(generation_request)
        finally:
            await generator.close()

        try:
            output = LinkedInModelOutput.model_validate_json(generated.text)
        except ValidationError as exc:
            raise InvalidGeneratedDraftError(
                code="invalid_generated_draft",
                message="The AI service returned an invalid draft response.",
            ) from exc
        if output.status == "insufficient_source_information":
            raise GenerationInsufficientSourceError(
                code="insufficient_source_information",
                message="More authorised source information is required.",
            )

        word_count = len(WORD_PATTERN.findall(output.draft))
        length = LINKEDIN_LENGTH_SPECIFICATIONS[preferences.post_length]
        if not length.minimum_words <= word_count <= length.maximum_words:
            raise InvalidGeneratedDraftError(
                code="generated_draft_length_invalid",
                message="The generated draft is outside the requested length limits.",
            )

        reference = package.article_reference
        source_reference = LinkedInDraftSourceReference(
            article_id=reference.article_id,
            title=reference.title,
            source_name=reference.source_name,
            source_url=reference.canonical_url,
            attribution_text=reference.attribution_text,
            rights_version_id=reference.rights_version_id,
        )
        grounding = self._grounding_validator.validate(
            draft=output.draft,
            article_id=source.article_id,
            source_reference=source_reference,
            article=source.article,
        )
        log_event(
            logger,
            logging.INFO,
            "linkedin_draft_grounding_evaluated",
            status=grounding.status.value,
            counts={
                "checked_claims": grounding.checked_claim_count,
                "validation_warnings": len(grounding.warnings),
            },
        )
        if grounding.status == GroundingStatus.REJECTED:
            raise InvalidGeneratedDraftError(
                code="grounding_validation_rejected",
                message=(
                    "The generated draft failed automated grounding checks and "
                    "was not saved."
                ),
            )

        draft = await self._repository.save_draft(
            owner_id=owner_id,
            source=source,
            source_reference=source_reference,
            preferences=preferences,
            prompt_version=package.prompt_version,
            request_key=request_key,
            request_marker=request_marker,
            generated=generated,
            draft_text=output.draft,
            word_count=word_count,
            grounding=grounding,
        )
        log_event(
            logger,
            logging.INFO,
            "linkedin_draft_generated",
            model=generated.model,
            request_id=generated.request_id,
            status="draft",
            counts=generated.usage.model_dump(exclude_none=True),
        )
        return draft

    async def get_draft(self, *, owner_id: UUID, draft_id: UUID) -> LinkedInDraft:
        """Return one private draft only when it belongs to the session owner."""

        return require_owned_resource(
            await self._repository.get_draft_for_owner(
                owner_id=owner_id,
                draft_id=draft_id,
            )
        )

    @staticmethod
    def _request_key(owner_id: UUID, supplied_key: str | None) -> str:
        raw_key = supplied_key or uuid4().hex
        return hashlib.sha256(f"{owner_id}:{raw_key}".encode()).hexdigest()

    @staticmethod
    def _request_marker(
        *,
        article_id: UUID,
        preferences: LinkedInGenerationPreferences,
        prompt_version: str,
    ) -> str:
        fingerprint = hashlib.sha256(
            (
                f"{article_id}:{preferences.tone.value}:"
                f"{preferences.post_length.value}:{prompt_version}"
            ).encode()
        ).hexdigest()
        return f"Prompt content not retained. Request fingerprint: {fingerprint}"

    @staticmethod
    def _error_category(exc: Exception) -> GenerationErrorCategory:
        if isinstance(exc, OpenAIAuthenticationFailure):
            return GenerationErrorCategory.AI_AUTHENTICATION_ERROR
        if isinstance(exc, OpenAIRateLimitFailure):
            return GenerationErrorCategory.AI_RATE_LIMIT_ERROR
        if isinstance(exc, OpenAIQuotaFailure):
            return GenerationErrorCategory.AI_QUOTA_ERROR
        if isinstance(exc, OpenAITimeoutFailure):
            return GenerationErrorCategory.AI_TIMEOUT
        if isinstance(exc, OpenAIUnavailableFailure):
            return GenerationErrorCategory.AI_SERVICE_UNAVAILABLE
        if isinstance(exc, OpenAIInvalidResponseError):
            return GenerationErrorCategory.AI_INVALID_RESPONSE
        if isinstance(exc, GenerationProviderConfigurationError):
            return GenerationErrorCategory.AI_CONFIGURATION_ERROR
        if isinstance(
            exc,
            (
                InvalidGeneratedDraftError,
                GenerationInsufficientSourceError,
                OpenAIServiceError,
            ),
        ):
            return GenerationErrorCategory.GENERATION_VALIDATION_ERROR
        if isinstance(exc, LinkedInGenerationRepositoryError):
            return GenerationErrorCategory.GENERATION_STORAGE_ERROR
        return GenerationErrorCategory.GENERATION_UNEXPECTED_ERROR
