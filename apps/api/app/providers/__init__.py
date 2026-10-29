"""Authorised news-source provider boundary."""

from app.providers.base import NewsProvider
from app.providers.cnn_adapter import CnnAdapterDecision, CnnSourceAdapter
from app.providers.exceptions import (
    ArticleNotFoundError,
    InvalidProviderCursorError,
    ProviderDataError,
    ProviderError,
    ProviderErrorCode,
    ProviderUnavailableError,
    SourceNotAuthorisedError,
)
from app.providers.factory import create_news_provider
from app.providers.fixture_provider import FixtureNewsProvider
from app.providers.models import (
    ArticleCategory,
    ArticleQuery,
    Attribution,
    NewsArticle,
    PermittedContent,
    ProviderCapabilities,
    ProviderPage,
    RightsMetadata,
)
from app.providers.normalisation import (
    FIXTURE_NORMALISATION_POLICY,
    ArticleFieldMapping,
    ArticleNormalisationError,
    ArticleNormalisationErrorCode,
    ArticleNormalisationPolicy,
    ArticleNormalisationService,
)
from app.providers.service import ArticleDiscoveryService

__all__ = [
    "ArticleCategory",
    "ArticleDiscoveryService",
    "ArticleFieldMapping",
    "ArticleNormalisationError",
    "ArticleNormalisationErrorCode",
    "ArticleNormalisationPolicy",
    "ArticleNormalisationService",
    "ArticleNotFoundError",
    "ArticleQuery",
    "Attribution",
    "CnnAdapterDecision",
    "CnnSourceAdapter",
    "FixtureNewsProvider",
    "FIXTURE_NORMALISATION_POLICY",
    "InvalidProviderCursorError",
    "NewsArticle",
    "NewsProvider",
    "PermittedContent",
    "ProviderCapabilities",
    "ProviderDataError",
    "ProviderError",
    "ProviderErrorCode",
    "ProviderPage",
    "ProviderUnavailableError",
    "RightsMetadata",
    "SourceNotAuthorisedError",
    "create_news_provider",
]
