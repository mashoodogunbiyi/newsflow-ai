"""Safe provider selection from validated application configuration."""

from app.core.config import Settings
from app.providers.base import NewsProvider
from app.providers.exceptions import SourceNotAuthorisedError
from app.providers.fixture_provider import FixtureNewsProvider


def create_news_provider(settings: Settings) -> NewsProvider:
    """Create only an explicitly enabled and approved provider."""

    if settings.news_source_mode == "fixture":
        return FixtureNewsProvider()
    raise SourceNotAuthorisedError
