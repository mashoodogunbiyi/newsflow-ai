"""Deterministic, conservative policy for news-related AI illustrations."""

import json
from datetime import datetime
from uuid import UUID

from app.models.image_safety import (
    ImageProviderSafetyCapabilities,
    ImageProviderSafetyControls,
    ImageSafetyDecision,
    ImageSafetyReasonCode,
    ImageSafetyRequest,
    ImageSafetyResult,
    RequiredImageTreatment,
    SensitiveNewsCategory,
)

IMAGE_SAFETY_POLICY_VERSION = "image_safety_v1"

SENSITIVE_CATEGORY_KEYWORDS: dict[SensitiveNewsCategory, tuple[str, ...]] = {
    SensitiveNewsCategory.ARMED_CONFLICT: (
        "armed conflict",
        "war zone",
        "warfare",
        "invasion",
        "military strike",
        "airstrike",
        "missile strike",
        "battlefield",
        "combat",
        "troops",
    ),
    SensitiveNewsCategory.TERRORISM: (
        "terrorist",
        "terror attack",
        "terrorism",
        "suicide bombing",
        "hostage attack",
    ),
    SensitiveNewsCategory.NATURAL_DISASTER: (
        "natural disaster",
        "earthquake",
        "tsunami",
        "wildfire",
        "hurricane",
        "tornado",
        "landslide",
        "major flood",
        "collapsed building",
    ),
    SensitiveNewsCategory.DEATH_OR_SERIOUS_INJURY: (
        "fatality",
        "fatalities",
        "killed",
        "death toll",
        "serious injury",
        "seriously injured",
        "casualties",
        "mass casualty",
    ),
    SensitiveNewsCategory.PUBLIC_HEALTH_EMERGENCY: (
        "public health emergency",
        "pandemic",
        "epidemic",
        "disease outbreak",
        "quarantine",
        "health crisis",
    ),
    SensitiveNewsCategory.ELECTION_OR_POLITICAL_EVENT: (
        "election",
        "ballot",
        "voting",
        "political rally",
        "campaign event",
        "parliament",
        "presidential debate",
    ),
    SensitiveNewsCategory.CRIMINAL_ALLEGATION: (
        "criminal allegation",
        "accused of",
        "charged with",
        "arrested for",
        "fraud allegation",
        "criminal trial",
        "police investigation",
    ),
}

UNCERTAINTY_MARKERS = (
    "unconfirmed",
    "unclear whether",
    "possibly involving",
    "developing report",
    "details remain uncertain",
    "classification unknown",
)

IDENTIFIABLE_PERSON_MARKERS = (
    "president ",
    "prime minister ",
    "senator ",
    "governor ",
    "mayor ",
    "candidate ",
    "minister ",
    "public figure ",
    "named person ",
    "celebrity ",
)

DOCUMENTARY_FABRICATION_MARKERS = (
    "fake photograph",
    "fake photo",
    "realistic news photograph",
    "breaking news photograph",
    "breaking news photo",
    "photographic evidence",
    "documentary evidence",
    "exact moment of",
    "make it look real",
    "make it appear authentic",
    "as if photographed",
    "on-location photograph",
)

SAFETY_OVERRIDE_MARKERS = (
    "disable safety",
    "bypass safety",
    "ignore safety",
    "turn off safety",
    "remove restrictions",
    "photorealism_allowed",
    "documentary_use_allowed",
)

REAL_PERSON_DEPICTION_MARKERS = (
    "show ",
    "depict ",
    "portray ",
    "place ",
    "make them ",
    "participating in",
    "committing",
    "saying",
)

REASON_MESSAGES = {
    ImageSafetyReasonCode.ORDINARY_CONCEPTUAL_TOPIC: (
        "The topic may proceed as a clearly designated conceptual illustration."
    ),
    ImageSafetyReasonCode.SENSITIVE_REAL_WORLD_EVENT: (
        "This sensitive topic may proceed only as a non-photorealistic conceptual "
        "illustration with human review."
    ),
    ImageSafetyReasonCode.DOCUMENTARY_FABRICATION_REQUEST: (
        "NewsFlow AI cannot create synthetic documentary or photographic evidence."
    ),
    ImageSafetyReasonCode.IDENTIFIABLE_PERSON_MISREPRESENTATION: (
        "NewsFlow AI cannot create a misleading depiction of an identifiable person."
    ),
    ImageSafetyReasonCode.SAFETY_OVERRIDE_ATTEMPT: (
        "Image safety restrictions cannot be disabled or overridden."
    ),
    ImageSafetyReasonCode.CLASSIFICATION_UNCERTAIN: (
        "The topic could not be classified confidently and requires human review."
    ),
    ImageSafetyReasonCode.PROVIDER_SAFETY_CONTROLS_UNAVAILABLE: (
        "The configured provider does not expose the required safety controls."
    ),
}


class SensitiveNewsPolicy:
    """Classify untrusted context and return a fail-closed policy decision."""

    def evaluate(
        self,
        *,
        request: ImageSafetyRequest,
        provider_capabilities: ImageProviderSafetyCapabilities,
        evaluation_id: UUID,
        evaluated_at: datetime,
    ) -> ImageSafetyResult:
        """Evaluate one composed prompt before any provider call is allowed."""

        context_text = self._extract_context_text(request)
        user_text = (
            request.user_request.get_secret_value()
            if request.user_request is not None
            else ""
        )
        categories = self._classify(context_text, user_text)
        sensitive = any(
            category in SENSITIVE_CATEGORY_KEYWORDS for category in categories
        )
        uncertain = SensitiveNewsCategory.UNCERTAIN in categories
        provider_controls = self._provider_controls(
            provider_capabilities,
            sensitive=sensitive or uncertain,
        )
        provider_controls_complete = (
            provider_controls.prompt_moderation_enabled
            and provider_controls.output_moderation_enabled
        )

        decision, reason, alternative = self._decide(
            context_text=context_text,
            user_text=user_text,
            categories=categories,
            sensitive=sensitive,
            uncertain=uncertain,
            provider_controls_complete=provider_controls_complete,
        )
        return ImageSafetyResult(
            evaluation_id=evaluation_id,
            policy_version=IMAGE_SAFETY_POLICY_VERSION,
            article_id=request.prompt.preferences.article_id,
            generation_id=request.prompt.generation_id,
            decision=decision,
            reason_code=reason,
            reason_message=REASON_MESSAGES[reason],
            sensitive_categories=categories,
            provider_call_allowed=decision
            in {
                ImageSafetyDecision.ALLOWED,
                ImageSafetyDecision.ALLOWED_WITH_RESTRICTIONS,
            },
            required_treatment=RequiredImageTreatment.CONCEPTUAL_ILLUSTRATION,
            conceptual_alternative_available=alternative,
            provider_controls=provider_controls,
            evaluated_at=evaluated_at,
        )

    @staticmethod
    def _decide(
        *,
        context_text: str | None,
        user_text: str,
        categories: tuple[SensitiveNewsCategory, ...],
        sensitive: bool,
        uncertain: bool,
        provider_controls_complete: bool,
    ) -> tuple[ImageSafetyDecision, ImageSafetyReasonCode, bool]:
        lowered_user = user_text.casefold()
        combined = f"{context_text or ''} {user_text}".casefold()
        identifiable_person = any(
            marker in combined for marker in IDENTIFIABLE_PERSON_MARKERS
        )

        if any(marker in lowered_user for marker in SAFETY_OVERRIDE_MARKERS):
            return (
                ImageSafetyDecision.REJECTED,
                ImageSafetyReasonCode.SAFETY_OVERRIDE_ATTEMPT,
                False,
            )
        if any(marker in lowered_user for marker in DOCUMENTARY_FABRICATION_MARKERS):
            return (
                ImageSafetyDecision.REJECTED,
                ImageSafetyReasonCode.DOCUMENTARY_FABRICATION_REQUEST,
                sensitive,
            )
        if (
            identifiable_person
            and sensitive
            and user_text
            and any(marker in lowered_user for marker in REAL_PERSON_DEPICTION_MARKERS)
        ):
            return (
                ImageSafetyDecision.REJECTED,
                ImageSafetyReasonCode.IDENTIFIABLE_PERSON_MISREPRESENTATION,
                False,
            )
        if not provider_controls_complete:
            return (
                (
                    ImageSafetyDecision.REJECTED
                    if sensitive
                    else ImageSafetyDecision.REVIEW_REQUIRED
                ),
                ImageSafetyReasonCode.PROVIDER_SAFETY_CONTROLS_UNAVAILABLE,
                not sensitive,
            )
        if context_text is None or uncertain:
            return (
                ImageSafetyDecision.REVIEW_REQUIRED,
                ImageSafetyReasonCode.CLASSIFICATION_UNCERTAIN,
                True,
            )
        if sensitive:
            return (
                ImageSafetyDecision.ALLOWED_WITH_RESTRICTIONS,
                ImageSafetyReasonCode.SENSITIVE_REAL_WORLD_EVENT,
                True,
            )
        assert categories == (SensitiveNewsCategory.NON_SENSITIVE,)
        return (
            ImageSafetyDecision.ALLOWED,
            ImageSafetyReasonCode.ORDINARY_CONCEPTUAL_TOPIC,
            True,
        )

    @staticmethod
    def _classify(
        context_text: str | None,
        user_text: str,
    ) -> tuple[SensitiveNewsCategory, ...]:
        if context_text is None:
            return (SensitiveNewsCategory.UNCERTAIN,)
        combined = f"{context_text} {user_text}".casefold()
        matched = {
            category
            for category, keywords in SENSITIVE_CATEGORY_KEYWORDS.items()
            if any(keyword in combined for keyword in keywords)
        }
        if matched and any(
            marker in combined for marker in IDENTIFIABLE_PERSON_MARKERS
        ):
            matched.add(SensitiveNewsCategory.IDENTIFIABLE_PERSON_SENSITIVE_EVENT)
        if any(marker in combined for marker in UNCERTAINTY_MARKERS):
            matched.add(SensitiveNewsCategory.UNCERTAIN)
        if not matched:
            return (SensitiveNewsCategory.NON_SENSITIVE,)
        return tuple(
            category for category in SensitiveNewsCategory if category in matched
        )

    @staticmethod
    def _extract_context_text(request: ImageSafetyRequest) -> str | None:
        """Read the composer output as untrusted data without retaining it."""

        raw = request.prompt.untrusted_context.get_secret_value()
        lines = raw.splitlines()
        if (
            len(lines) != 3
            or lines[0] != "UNTRUSTED_IMAGE_CONTEXT_JSON"
            or lines[2] != "END_UNTRUSTED_IMAGE_CONTEXT_JSON"
        ):
            return None
        try:
            payload = json.loads(lines[1])
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        values = list(SensitiveNewsPolicy._string_values(payload))
        return " ".join(values) if values else None

    @staticmethod
    def _string_values(value: object):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for nested in value.values():
                yield from SensitiveNewsPolicy._string_values(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from SensitiveNewsPolicy._string_values(nested)

    @staticmethod
    def _provider_controls(
        capabilities: ImageProviderSafetyCapabilities,
        *,
        sensitive: bool,
    ) -> ImageProviderSafetyControls:
        return ImageProviderSafetyControls(
            prompt_moderation_enabled=capabilities.prompt_moderation_available,
            output_moderation_enabled=capabilities.output_moderation_available,
            strict_safety_level_enabled=(
                sensitive and capabilities.strict_safety_level_available
            ),
            content_credentials_requested=(capabilities.content_credentials_available),
        )
