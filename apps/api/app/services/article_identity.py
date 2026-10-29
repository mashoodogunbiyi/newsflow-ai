"""Stable provider-scoped article identity without using article titles."""

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlsplit

IDENTITY_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


class ArticleIdentityStrategy(str, Enum):
    """Document how an external article identity was selected."""

    PROVIDER_ITEM_ID = "provider_item_id"
    CANONICAL_URL_SHA256 = "canonical_url_sha256"


class ArticleIdentityError(ValueError):
    """Raised when a stable identity cannot be produced safely."""


@dataclass(frozen=True)
class ArticleIdentity:
    """Provider-scoped identity used by normalisation and persistence."""

    provider_id: str
    external_article_id: str
    canonical_url: str
    strategy: ArticleIdentityStrategy


class ArticleIdentityService:
    """Prefer a stable provider ID and otherwise derive one from the canonical URL."""

    def resolve(
        self,
        *,
        provider_id: str,
        canonical_url: str,
        external_article_id: str | None,
        fallback_prefix: str = "url-sha256-",
    ) -> ArticleIdentity:
        """Return one stable identity without inspecting mutable article text."""

        clean_provider_id = provider_id.strip()
        if not clean_provider_id:
            raise ArticleIdentityError("The source provider identity is required.")

        self._require_canonical_https_url(canonical_url)
        if external_article_id is not None and external_article_id.strip():
            clean_external_id = external_article_id.strip()
            strategy = ArticleIdentityStrategy.PROVIDER_ITEM_ID
        else:
            digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
            clean_external_id = f"{fallback_prefix}{digest}"
            strategy = ArticleIdentityStrategy.CANONICAL_URL_SHA256

        if len(clean_external_id) > 200 or not IDENTITY_VALUE_PATTERN.fullmatch(
            clean_external_id
        ):
            raise ArticleIdentityError(
                "The external article identity has an invalid format."
            )

        return ArticleIdentity(
            provider_id=clean_provider_id,
            external_article_id=clean_external_id,
            canonical_url=canonical_url,
            strategy=strategy,
        )

    @staticmethod
    def _require_canonical_https_url(canonical_url: str) -> None:
        try:
            parsed = urlsplit(canonical_url)
            _ = parsed.port
        except ValueError as exc:
            raise ArticleIdentityError(
                "A canonical HTTPS URL is required for article identity."
            ) from exc
        if (
            parsed.scheme != "https"
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ArticleIdentityError(
                "A canonical HTTPS URL is required for article identity."
            )
