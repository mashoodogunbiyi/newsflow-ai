"""Central image-safety evaluation and content-free decision recording."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.models.image_safety import (
    ImageProviderSafetyCapabilities,
    ImageSafetyDecisionRecord,
    ImageSafetyRequest,
    ImageSafetyResult,
)
from app.policies.sensitive_news import SensitiveNewsPolicy


class ImageSafetyDecisionRecorder(Protocol):
    """Persistence boundary for safe policy metadata only."""

    def record_decision(self, record: ImageSafetyDecisionRecord) -> None:
        """Store one content-free image-safety decision."""


class ImageSafetyService:
    """Apply the application policy before a future provider is called."""

    def __init__(
        self,
        *,
        provider_capabilities: ImageProviderSafetyCapabilities,
        recorder: ImageSafetyDecisionRecorder | None = None,
        policy: SensitiveNewsPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._provider_capabilities = provider_capabilities
        self._recorder = recorder
        self._policy = policy or SensitiveNewsPolicy()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or uuid4

    def evaluate(self, request: ImageSafetyRequest) -> ImageSafetyResult:
        """Evaluate and safely record one request before provider access."""

        evaluated_at = self._clock()
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("Image safety evaluation time must include a timezone.")
        result = self._policy.evaluate(
            request=request,
            provider_capabilities=self._provider_capabilities,
            evaluation_id=self._id_factory(),
            evaluated_at=evaluated_at.astimezone(UTC),
        )
        if self._recorder is not None:
            self._recorder.record_decision(
                ImageSafetyDecisionRecord(
                    evaluation_id=result.evaluation_id,
                    policy_version=result.policy_version,
                    article_id=result.article_id,
                    generation_id=result.generation_id,
                    decision=result.decision,
                    reason_code=result.reason_code,
                    sensitive_categories=result.sensitive_categories,
                    provider_call_allowed=result.provider_call_allowed,
                    review_required=result.review_required,
                    photorealism_allowed=result.photorealism_allowed,
                    ai_generated_designation=result.ai_generated_designation,
                    evaluated_at=result.evaluated_at,
                )
            )
        return result
