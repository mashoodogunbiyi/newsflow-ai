"""Rights-aware construction of source-grounded LinkedIn prompts."""

import json
from uuid import UUID

from pydantic import SecretStr

from app.models.ai import AITextGenerationRequest
from app.models.article_rights import ArticleRightsDecision, ArticleUseOperation
from app.models.generation_preferences import (
    LinkedInArticleReference,
    LinkedInGenerationPreferences,
    LinkedInPromptPackage,
)
from app.prompts.linkedin_post import (
    LINKEDIN_PROMPT_VERSION,
    build_linkedin_instructions,
)
from app.providers.models import ContentStatus, NewsArticle

PERMITTED_AI_SOURCE_FIELDS = (
    "title",
    "source_name",
    "publication_date",
    "category",
    "description",
    "permitted_content",
)


class PromptConstructionError(RuntimeError):
    """Safe prompt-building failure that never contains article content."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.safe_message = message
        super().__init__(message)


class ArticlePromptRightsError(PromptConstructionError):
    """Raised when current rights do not permit AI derivative generation."""


class InsufficientSourceInformationError(PromptConstructionError):
    """Raised when no authorised factual content can ground a post."""


class LinkedInPromptBuilder:
    """Build one versioned request from an approved article and rights decision."""

    def build(
        self,
        *,
        article_id: UUID,
        article: NewsArticle,
        rights_decision: ArticleRightsDecision,
        preferences: LinkedInGenerationPreferences,
    ) -> LinkedInPromptPackage:
        """Return separated trusted instructions, untrusted input, and reference."""

        self._require_ai_rights(article_id, article, rights_decision)
        permitted_text = self._require_permitted_information(article)
        instructions, length = build_linkedin_instructions(
            tone=preferences.tone,
            post_length=preferences.post_length,
        )
        source_data = {
            "title": article.title,
            "source_name": article.source_name,
            "publication_date": article.publication_date.isoformat(),
            "category": article.category.value,
            "description": article.description,
            "permitted_content": permitted_text,
        }
        untrusted_input = (
            "UNTRUSTED_ARTICLE_DATA_JSON\n"
            + json.dumps(source_data, ensure_ascii=False, sort_keys=True)
            + "\nEND_UNTRUSTED_ARTICLE_DATA_JSON"
        )
        attribution_text = (
            rights_decision.attribution_text or article.attribution.attribution_text
        )
        assert rights_decision.rights_version_id is not None
        reference = LinkedInArticleReference(
            article_id=article_id,
            source_item_id=article.source_item_id,
            title=article.title,
            source_name=article.source_name,
            publication_date=article.publication_date,
            canonical_url=article.url,
            attribution_text=attribution_text,
            rights_version_id=rights_decision.rights_version_id,
        )
        return LinkedInPromptPackage(
            prompt_version=LINKEDIN_PROMPT_VERSION,
            preferences=preferences,
            included_source_fields=PERMITTED_AI_SOURCE_FIELDS,
            article_reference=reference,
            generation_request=AITextGenerationRequest(
                input_text=SecretStr(untrusted_input),
                instructions=SecretStr(instructions),
                max_output_tokens=length.max_output_tokens,
            ),
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
            raise ArticlePromptRightsError(
                code="article_ai_generation_not_permitted",
                message="The article is not permitted for AI draft generation.",
            )
        if decision.attribution_required and not decision.attribution_text:
            raise ArticlePromptRightsError(
                code="article_attribution_incomplete",
                message="The approved article attribution is incomplete.",
            )

    @staticmethod
    def _require_permitted_information(article: NewsArticle) -> str:
        permitted = article.permitted_content
        if permitted.status == ContentStatus.NOT_PERMITTED:
            raise ArticlePromptRightsError(
                code="article_content_not_permitted",
                message="The article content is not permitted for AI processing.",
            )
        if permitted.status != ContentStatus.AVAILABLE or not permitted.text:
            raise InsufficientSourceInformationError(
                code="insufficient_source_information",
                message="More authorised source information is required.",
            )
        if (
            not permitted.ai_processing_allowed
            or not permitted.derivative_output_allowed
        ):
            raise ArticlePromptRightsError(
                code="article_ai_generation_not_permitted",
                message="The article is not permitted for AI draft generation.",
            )
        return permitted.text
