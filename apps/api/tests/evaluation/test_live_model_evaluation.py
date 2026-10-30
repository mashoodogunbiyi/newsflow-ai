"""Optional live-model evaluation, excluded unless explicitly enabled."""

import asyncio
import os

import pytest

from app.evaluation import GenerationEvaluator
from app.models.ai import AIJsonSchemaFormat
from app.models.article_rights import (
    ArticleRightsDecision,
    ArticleUseOperation,
    RightsDecisionReason,
)
from app.models.generation_preferences import LinkedInGenerationPreferences
from app.models.linkedin_generation import LinkedInModelOutput
from app.services.linkedin_generation import LINKEDIN_DRAFT_JSON_SCHEMA
from app.services.openai_service import OpenAIService
from app.services.prompt_builder import LinkedInPromptBuilder
from tests.support.generation_evaluation import article_record, source_reference

LIVE_EVALUATION_ENABLED = os.getenv("RUN_LIVE_AI_EVALUATION") == "true"

pytestmark = [
    pytest.mark.live_ai,
    pytest.mark.skipif(
        not LIVE_EVALUATION_ENABLED,
        reason="Set RUN_LIVE_AI_EVALUATION=true to allow one billable request.",
    ),
]


def test_one_synthetic_article_against_the_configured_live_model() -> None:
    """Run one bounded request and print a versioned report for human review."""

    record = article_record("technology-efficiency")
    reference = source_reference(record)
    preferences = LinkedInGenerationPreferences(
        tone="professional",
        post_length="short",
    )
    decision = ArticleRightsDecision(
        article_id=record.article_id,
        operation=ArticleUseOperation.USE_FOR_AI_GENERATION,
        allowed=True,
        reason=RightsDecisionReason.PERMITTED,
        rights_version_id=reference.rights_version_id,
        attribution_required=True,
        attribution_text=reference.attribution_text,
    )
    package = LinkedInPromptBuilder().build(
        article_id=record.article_id,
        article=record.article,
        rights_decision=decision,
        preferences=preferences,
    )
    request = package.generation_request.model_copy(
        update={
            "json_schema_format": AIJsonSchemaFormat(
                name="linkedin_post_evaluation",
                schema_definition=LINKEDIN_DRAFT_JSON_SCHEMA,
            )
        }
    )

    async def generate() -> tuple[LinkedInModelOutput, str]:
        service = OpenAIService.from_settings()
        try:
            result = await service.generate_text(request)
            return LinkedInModelOutput.model_validate_json(result.text), result.model
        finally:
            await service.close()

    output, model = asyncio.run(generate())
    assert output.status == "ready", output.insufficiency_reason
    report = GenerationEvaluator().evaluate(
        case_id="optional-live-model",
        draft=output.draft,
        article_id=record.article_id,
        source_reference=reference,
        article=record.article,
        preferences=preferences,
        prompt_version=package.prompt_version,
        model_identifier=model,
    )

    print(report.model_dump_json(indent=2))
    assert report.passed is True
