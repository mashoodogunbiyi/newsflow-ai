"""Reusable loaders and builders for the synthetic generation evaluation suite."""

import json
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.generation_preferences import LinkedInPostLength, LinkedInTone
from app.models.linkedin_generation import LinkedInDraftSourceReference
from app.providers.models import NewsArticle

FIXTURE_DIRECTORY = Path(__file__).parents[1] / "fixtures"
ARTICLE_DATASET_PATH = FIXTURE_DIRECTORY / "evaluation_articles.json"
CASE_DATASET_PATH = FIXTURE_DIRECTORY / "expected_generation_cases.json"
RIGHTS_VERSION_ID = UUID("44000000-0000-4000-8000-000000000099")


class SyntheticArticleRecord(BaseModel):
    """One validated synthetic article and its stable evaluation identifier."""

    evaluation_id: str = Field(pattern=r"^[a-z0-9-]+$")
    article_id: UUID
    article: NewsArticle

    model_config = ConfigDict(extra="forbid", frozen=True)


class SyntheticArticleDataset(BaseModel):
    """Versioned collection of original non-CNN evaluation articles."""

    dataset_version: Literal["newsflow-synthetic-evaluation-v1"]
    description: str
    articles: tuple[SyntheticArticleRecord, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)


class MockGenerationCase(BaseModel):
    """One stored provider response used for deterministic regression checks."""

    case_id: str = Field(pattern=r"^[a-z0-9-]+$")
    article_fixture: str
    tone: LinkedInTone
    length: LinkedInPostLength
    prompt_version: str
    model_identifier: str
    draft: str
    expected_pass: bool

    model_config = ConfigDict(extra="forbid", frozen=True)


class MockGenerationDataset(BaseModel):
    """Versioned deterministic generation cases."""

    dataset_version: Literal["linkedin-generation-regression-v1"]
    description: str
    cases: tuple[MockGenerationCase, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)


def load_article_dataset() -> SyntheticArticleDataset:
    """Load and validate the reusable fictional article fixture collection."""

    return SyntheticArticleDataset.model_validate_json(
        ARTICLE_DATASET_PATH.read_text(encoding="utf-8")
    )


def load_generation_dataset() -> MockGenerationDataset:
    """Load and validate mocked output cases without accessing OpenAI."""

    return MockGenerationDataset.model_validate_json(
        CASE_DATASET_PATH.read_text(encoding="utf-8")
    )


def article_record(evaluation_id: str) -> SyntheticArticleRecord:
    """Return one stable fixture record by its human-readable identifier."""

    for item in load_article_dataset().articles:
        if item.evaluation_id == evaluation_id:
            return item
    raise KeyError(f"Unknown synthetic evaluation article: {evaluation_id}")


def generation_case(case_id: str) -> MockGenerationCase:
    """Return one stored mocked generation case."""

    for item in load_generation_dataset().cases:
        if item.case_id == case_id:
            return item
    raise KeyError(f"Unknown generation evaluation case: {case_id}")


def source_reference(record: SyntheticArticleRecord) -> LinkedInDraftSourceReference:
    """Create the trusted reference that would normally be built by the backend."""

    article = record.article
    return LinkedInDraftSourceReference(
        article_id=record.article_id,
        title=article.title,
        source_name=article.source_name,
        source_url=article.url,
        attribution_text=article.attribution.attribution_text,
        rights_version_id=RIGHTS_VERSION_ID,
    )


def assert_dataset_contains_no_live_content() -> None:
    """Fail if a fixture stops using the reserved synthetic source boundary."""

    raw_text = ARTICLE_DATASET_PATH.read_text(encoding="utf-8")
    parsed = json.loads(raw_text)
    for record in parsed["articles"]:
        article = record["article"]
        assert article["source_name"] == "NewsFlow AI Synthetic Desk"
        assert article["url"].startswith("https://example.invalid/")
