"""Deterministic validation of generated drafts against permitted source fields."""

import re
import unicodedata
from collections.abc import Iterable
from uuid import UUID

from app.models.grounding import (
    GroundingResult,
    GroundingStatus,
    GroundingWarning,
    GroundingWarningCode,
)
from app.models.linkedin_generation import LinkedInDraftSourceReference
from app.providers.models import ContentStatus, NewsArticle

GROUNDING_POLICY_VERSION = "grounding_v1"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.IGNORECASE)
NUMBER_PATTERN = re.compile(
    r"(?<![\w])(?:[$\u00a3\u20ac])?\d[\d,]*(?:\.\d+)?%?(?![\w])"
)
QUOTE_PATTERN = re.compile(r'["\u201c](.{2,}?)["\u201d]')
DATE_PATTERN = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+\d{1,2}(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)
ENTITY_PATTERN = re.compile(
    r"\b(?:[A-Z][a-z]{2,}|[A-Z]{2,})(?:\s+(?:[A-Z][a-z]{2,}|[A-Z]{2,})){1,3}\b"
)
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")
OPINION_PATTERN = re.compile(
    r"\b(?:i think|i believe|in my view|in my opinion|my view|my take|"
    r"this may|this might|this could|it may|it might|it could|perhaps|"
    r"we should|professionals should consider)\b",
    re.IGNORECASE,
)
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "will",
    "with",
}

WARNING_DETAILS = {
    GroundingWarningCode.EMPTY_DRAFT: (
        "structure",
        "blocking",
        "The generated draft is empty.",
    ),
    GroundingWarningCode.SOURCE_REFERENCE_MISMATCH: (
        "source_reference",
        "blocking",
        "The draft source reference does not match the trusted article record.",
    ),
    GroundingWarningCode.INSUFFICIENT_GROUNDING_CONTEXT: (
        "insufficient_context",
        "blocking",
        "The permitted source information is insufficient for grounding checks.",
    ),
    GroundingWarningCode.UNSUPPORTED_NUMERICAL_CLAIM: (
        "unsupported_claim",
        "review",
        "A numerical claim was not found in the permitted source information.",
    ),
    GroundingWarningCode.UNSUPPORTED_QUOTATION: (
        "unsupported_claim",
        "blocking",
        "A direct quotation was not found in the permitted source information.",
    ),
    GroundingWarningCode.UNSUPPORTED_DATE_CLAIM: (
        "unsupported_claim",
        "review",
        "A date claim was not found in the permitted source information.",
    ),
    GroundingWarningCode.UNSUPPORTED_NAMED_ENTITY: (
        "unsupported_claim",
        "review",
        "A named entity was not found in the permitted source information.",
    ),
    GroundingWarningCode.UNSUPPORTED_FACTUAL_ASSERTION: (
        "unsupported_claim",
        "review",
        "A factual assertion has limited support in the permitted source information.",
    ),
}


class GenerationGroundingValidator:
    """Apply explainable checks without fetching content or calling another model."""

    def validate(
        self,
        *,
        draft: str,
        article_id: UUID,
        source_reference: LinkedInDraftSourceReference,
        article: NewsArticle,
    ) -> GroundingResult:
        """Return safe warnings derived only from the supplied permitted fields."""

        warning_codes: list[GroundingWarningCode] = []
        cleaned_draft = self._normalise(draft)
        if not cleaned_draft:
            warning_codes.append(GroundingWarningCode.EMPTY_DRAFT)

        if source_reference.article_id != article_id or str(
            source_reference.source_url
        ) != str(article.url):
            warning_codes.append(GroundingWarningCode.SOURCE_REFERENCE_MISMATCH)

        source_text = self._source_text(article)
        source_terms = self._content_terms(source_text)
        grounding_detail = " ".join(
            value
            for value in (article.description, article.permitted_content.text)
            if value
        )
        has_permitted_context = (
            article.permitted_content.status == ContentStatus.AVAILABLE
            and article.permitted_content.ai_processing_allowed
            and article.permitted_content.derivative_output_allowed
            and len(self._content_terms(grounding_detail)) >= 8
        )
        if not has_permitted_context:
            warning_codes.append(GroundingWarningCode.INSUFFICIENT_GROUNDING_CONTEXT)

        checked_claims = 0
        if cleaned_draft and has_permitted_context:
            warning_codes.extend(self._check_quotes(cleaned_draft, source_text))
            warning_codes.extend(self._check_numbers(cleaned_draft, source_text))
            warning_codes.extend(self._check_dates(cleaned_draft, source_text))

            for sentence in self._sentences(cleaned_draft):
                if self._is_commentary(sentence):
                    continue
                claim_terms = self._content_terms(sentence)
                if len(claim_terms) < 4:
                    continue
                checked_claims += 1
                warning_codes.extend(self._check_entities(sentence, source_text))
                supported_terms = claim_terms & source_terms
                if len(supported_terms) / len(claim_terms) < 0.35:
                    warning_codes.append(
                        GroundingWarningCode.UNSUPPORTED_FACTUAL_ASSERTION
                    )

        warnings = tuple(self._warning(code) for code in dict.fromkeys(warning_codes))
        blocking = any(warning.severity == "blocking" for warning in warnings)
        status = (
            GroundingStatus.REJECTED
            if blocking
            else GroundingStatus.REVIEW_REQUIRED
            if warnings
            else GroundingStatus.PASSED_AUTOMATED_CHECKS
        )
        return GroundingResult(
            status=status,
            warnings=warnings,
            policy_version=GROUNDING_POLICY_VERSION,
            checked_claim_count=checked_claims,
        )

    @staticmethod
    def _source_text(article: NewsArticle) -> str:
        content_is_permitted = (
            article.permitted_content.status == ContentStatus.AVAILABLE
            and article.permitted_content.ai_processing_allowed
            and article.permitted_content.derivative_output_allowed
        )
        permitted_text = (
            article.permitted_content.text if content_is_permitted else None
        )
        values: Iterable[str | None] = (
            article.title,
            article.source_name,
            article.publication_date.isoformat(),
            (
                f"{article.publication_date.strftime('%B')} "
                f"{article.publication_date.day}, "
                f"{article.publication_date.year}"
            ),
            article.category.value,
            article.description if content_is_permitted else None,
            permitted_text,
        )
        return " ".join(value for value in values if value)

    @classmethod
    def _check_quotes(
        cls,
        draft: str,
        source_text: str,
    ) -> list[GroundingWarningCode]:
        normalised_source = cls._normalise(source_text).casefold()
        for match in QUOTE_PATTERN.finditer(draft):
            quotation = cls._normalise(match.group(1)).casefold()
            if quotation and quotation not in normalised_source:
                return [GroundingWarningCode.UNSUPPORTED_QUOTATION]
        return []

    @classmethod
    def _check_numbers(
        cls,
        draft: str,
        source_text: str,
    ) -> list[GroundingWarningCode]:
        source_numbers = {
            cls._normalise_number(value)
            for value in NUMBER_PATTERN.findall(source_text)
        }
        if any(
            cls._normalise_number(value) not in source_numbers
            for value in NUMBER_PATTERN.findall(draft)
        ):
            return [GroundingWarningCode.UNSUPPORTED_NUMERICAL_CLAIM]
        return []

    @classmethod
    def _check_dates(
        cls,
        draft: str,
        source_text: str,
    ) -> list[GroundingWarningCode]:
        normalised_source = cls._normalise(source_text).casefold()
        if any(
            cls._normalise(value).casefold() not in normalised_source
            for value in DATE_PATTERN.findall(draft)
        ):
            return [GroundingWarningCode.UNSUPPORTED_DATE_CLAIM]
        return []

    @classmethod
    def _check_entities(
        cls,
        sentence: str,
        source_text: str,
    ) -> list[GroundingWarningCode]:
        normalised_source = cls._normalise(source_text).casefold()
        entities = ENTITY_PATTERN.findall(sentence)
        if any(
            cls._normalise(entity).casefold() not in normalised_source
            for entity in entities
        ):
            return [GroundingWarningCode.UNSUPPORTED_NAMED_ENTITY]
        return []

    @staticmethod
    def _is_commentary(sentence: str) -> bool:
        stripped = sentence.strip()
        return (
            not stripped
            or stripped.startswith("#")
            or stripped.endswith("?")
            or OPINION_PATTERN.search(stripped) is not None
        )

    @staticmethod
    def _sentences(value: str) -> tuple[str, ...]:
        return tuple(
            part.strip() for part in SENTENCE_PATTERN.split(value) if part.strip()
        )

    @staticmethod
    def _content_terms(value: str) -> set[str]:
        return {
            token.casefold()
            for token in TOKEN_PATTERN.findall(value)
            if token.casefold() not in STOP_WORDS and len(token) > 1
        }

    @staticmethod
    def _normalise(value: str) -> str:
        return " ".join(unicodedata.normalize("NFC", value).split())

    @staticmethod
    def _normalise_number(value: str) -> str:
        return value.casefold().replace(",", "").lstrip("$\u00a3\u20ac")

    @staticmethod
    def _warning(code: GroundingWarningCode) -> GroundingWarning:
        category, severity, message = WARNING_DETAILS[code]
        return GroundingWarning(
            code=code,
            category=category,
            severity=severity,
            message=message,
        )
