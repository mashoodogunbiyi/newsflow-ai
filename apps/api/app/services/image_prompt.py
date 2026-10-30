"""Rights-aware construction of safe, versioned image prompts."""

import json
from uuid import UUID

from pydantic import SecretStr

from app.models.article_rights import ArticleRightsDecision, ArticleUseOperation
from app.models.grounding import GroundingStatus
from app.models.image_prompt import (
    ImagePromptContextKind,
    ImagePromptRequest,
    ImagePromptResult,
    ImagePromptSourceReference,
)
from app.models.linkedin_generation import LinkedInDraft
from app.prompts.image_illustration import (
    IMAGE_PROMPT_VERSION,
    build_image_instructions,
)
from app.providers.models import ContentStatus, NewsArticle

PERMITTED_IMAGE_SOURCE_FIELDS = (
    "title",
    "category",
    "description",
    "permitted_content",
)
MAX_DRAFT_CONTEXT_CHARACTERS = 4_000


class ImagePromptConstructionError(RuntimeError):
    """Safe prompt-construction failure that excludes source content."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.safe_message = message
        super().__init__(message)


class ImagePromptRightsError(ImagePromptConstructionError):
    """Raised when current rights do not permit an image derivative."""


class InvalidImagePromptContextError(ImagePromptConstructionError):
    """Raised when an article and optional draft are not safely associated."""


class InsufficientImageContextError(ImagePromptConstructionError):
    """Raised rather than inventing a visual theme from inadequate information."""


class ImagePromptComposer:
    """Build trusted image instructions and separate untrusted context data."""

    def compose(
        self,
        *,
        request: ImagePromptRequest,
        article: NewsArticle,
        rights_decision: ArticleRightsDecision,
        draft: LinkedInDraft | None = None,
    ) -> ImagePromptResult:
        """Return a versioned prompt after fail-closed context and rights checks."""

        self._require_ai_rights(request.article_id, article, rights_decision)
        permitted_text = self._require_permitted_information(article)
        context_kind, generation_id, derived_fields = self._validate_draft_context(
            request=request,
            article=article,
            draft=draft,
        )
        instructions = build_image_instructions(
            style=request.style,
            aspect_ratio=request.aspect_ratio,
            composition=request.composition,
        )
        context: dict[str, object] = {
            "article": {
                "title": article.title,
                "category": article.category.value,
                "description": article.description,
                "permitted_content": permitted_text,
            }
        }
        if draft is not None:
            context["linkedin_draft"] = draft.draft

        untrusted_context = (
            "UNTRUSTED_IMAGE_CONTEXT_JSON\n"
            + json.dumps(context, ensure_ascii=False, sort_keys=True)
            + "\nEND_UNTRUSTED_IMAGE_CONTEXT_JSON"
        )
        attribution_text = (
            rights_decision.attribution_text or article.attribution.attribution_text
        )
        assert rights_decision.rights_version_id is not None
        return ImagePromptResult(
            prompt_version=IMAGE_PROMPT_VERSION,
            context_kind=context_kind,
            generation_id=generation_id,
            preferences=request,
            included_source_fields=PERMITTED_IMAGE_SOURCE_FIELDS,
            included_derived_fields=derived_fields,
            source_reference=ImagePromptSourceReference(
                article_id=request.article_id,
                title=article.title,
                source_name=article.source_name,
                canonical_url=article.url,
                attribution_text=attribution_text,
                rights_version_id=rights_decision.rights_version_id,
            ),
            trusted_instructions=SecretStr(instructions),
            untrusted_context=SecretStr(untrusted_context),
        )

    @staticmethod
    def _require_ai_rights(
        article_id: UUID,
        article: NewsArticle,
        decision: ArticleRightsDecision,
    ) -> None:
        if (
            decision.article_id != article_id
            or decision.operation != ArticleUseOperation.USE_FOR_AI_GENERATION
            or not decision.allowed
            or decision.rights_version_id is None
        ):
            raise ImagePromptRightsError(
                code="article_image_generation_not_permitted",
                message="The article is not permitted for AI illustration generation.",
            )
        if decision.attribution_required and not decision.attribution_text:
            raise ImagePromptRightsError(
                code="article_attribution_incomplete",
                message="The approved article attribution is incomplete.",
            )
        if str(article.attribution.canonical_url) != str(article.url):
            raise ImagePromptRightsError(
                code="article_source_reference_invalid",
                message="The approved article source reference is invalid.",
            )

    @staticmethod
    def _require_permitted_information(article: NewsArticle) -> str:
        permitted = article.permitted_content
        if permitted.status == ContentStatus.NOT_PERMITTED:
            raise ImagePromptRightsError(
                code="article_content_not_permitted",
                message="The article content is not permitted for AI processing.",
            )
        if permitted.status != ContentStatus.AVAILABLE or not permitted.text:
            raise InsufficientImageContextError(
                code="insufficient_image_context",
                message="More authorised source information is required.",
            )
        if (
            not permitted.ai_processing_allowed
            or not permitted.derivative_output_allowed
        ):
            raise ImagePromptRightsError(
                code="article_image_generation_not_permitted",
                message="The article is not permitted for AI illustration generation.",
            )
        return permitted.text

    @staticmethod
    def _validate_draft_context(
        *,
        request: ImagePromptRequest,
        article: NewsArticle,
        draft: LinkedInDraft | None,
    ) -> tuple[ImagePromptContextKind, UUID | None, tuple[str, ...]]:
        if draft is None:
            if request.generation_id is not None:
                raise InvalidImagePromptContextError(
                    code="linkedin_draft_context_missing",
                    message="The requested LinkedIn draft context is unavailable.",
                )
            return ImagePromptContextKind.ARTICLE, None, ()

        if (
            request.generation_id is None
            or request.generation_id != draft.generation_id
        ):
            raise InvalidImagePromptContextError(
                code="linkedin_draft_context_mismatch",
                message="The LinkedIn draft does not match the image-prompt request.",
            )
        if (
            draft.source.article_id != request.article_id
            or draft.source.title != article.title
            or draft.source.source_name != article.source_name
            or str(draft.source.source_url) != str(article.url)
        ):
            raise InvalidImagePromptContextError(
                code="linkedin_draft_source_mismatch",
                message="The LinkedIn draft does not match the approved article.",
            )
        if draft.grounding.status == GroundingStatus.REJECTED:
            raise InvalidImagePromptContextError(
                code="linkedin_draft_validation_rejected",
                message="The LinkedIn draft is not approved as image context.",
            )
        if len(draft.draft) > MAX_DRAFT_CONTEXT_CHARACTERS:
            raise InvalidImagePromptContextError(
                code="linkedin_draft_context_too_long",
                message="The LinkedIn draft is too long for image-prompt context.",
            )
        return (
            ImagePromptContextKind.LINKEDIN_DRAFT,
            draft.generation_id,
            ("linkedin_draft",),
        )
