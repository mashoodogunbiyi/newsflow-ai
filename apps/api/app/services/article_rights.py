"""Fail-closed article rights verification and update workflow."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.models.article_rights import (
    ArticleProvenanceRecord,
    ArticleRightsDecision,
    ArticleRightsPolicy,
    ArticleRightsRecord,
    ArticleUseOperation,
    RightsDecisionReason,
    RightsVerificationStatus,
)
from app.repositories.article_rights import ArticleRightsRepository

logger = logging.getLogger(__name__)


class ArticleRightsDeniedError(RuntimeError):
    """Raised when a caller requires an operation that is not permitted."""

    def __init__(self, decision: ArticleRightsDecision) -> None:
        self.decision = decision
        super().__init__("The requested article operation is not permitted.")


class ArticleRightsService:
    """Evaluate current versioned rights before article use."""

    def __init__(self, repository: ArticleRightsRepository) -> None:
        self._repository = repository

    async def can_use_article(
        self,
        *,
        article_id: UUID,
        operation: ArticleUseOperation,
        checked_at: datetime | None = None,
    ) -> ArticleRightsDecision:
        """Return a safe and observable permission decision."""

        now = checked_at or datetime.now(UTC)
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("checked_at must include a timezone.")
        now = now.astimezone(UTC)
        current = await self._repository.get_current(article_id)
        if current is None:
            return self._decision(
                article_id=article_id,
                operation=operation,
                allowed=False,
                reason=RightsDecisionReason.MISSING_RIGHTS,
            )

        rights = current.record
        if not current.source_enabled:
            return self._from_rights(
                rights,
                operation,
                allowed=False,
                reason=RightsDecisionReason.SOURCE_DISABLED,
            )
        if rights.verification_status == RightsVerificationStatus.REVOKED:
            return self._from_rights(
                rights,
                operation,
                allowed=False,
                reason=RightsDecisionReason.REVOKED_RIGHTS,
            )
        if (
            rights.verification_status != RightsVerificationStatus.VERIFIED
            or rights.rights_last_verified_at is None
            or rights.effective_from > now
        ):
            return self._from_rights(
                rights,
                operation,
                allowed=False,
                reason=RightsDecisionReason.UNVERIFIED_RIGHTS,
            )
        if (
            rights.retention_expires_at is not None
            and rights.retention_expires_at <= now
        ):
            return self._from_rights(
                rights,
                operation,
                allowed=False,
                reason=RightsDecisionReason.EXPIRED_RIGHTS,
            )
        if (
            operation == ArticleUseOperation.DISPLAY_METADATA
            and rights.attribution_required
            and not rights.attribution_text
        ):
            return self._from_rights(
                rights,
                operation,
                allowed=False,
                reason=RightsDecisionReason.ATTRIBUTION_INCOMPLETE,
            )

        permitted = {
            ArticleUseOperation.DISPLAY_METADATA: rights.display_allowed,
            ArticleUseOperation.STORE_METADATA: rights.storage_allowed,
            ArticleUseOperation.USE_FOR_AI_GENERATION: (
                rights.ai_processing_allowed and rights.derivative_output_allowed
            ),
            ArticleUseOperation.EXPORT_SOURCE_INFORMATION: (
                rights.redistribution_allowed
            ),
            ArticleUseOperation.RETAIN_ARTICLE: rights.storage_allowed,
        }[operation]
        return self._from_rights(
            rights,
            operation,
            allowed=permitted,
            reason=(
                RightsDecisionReason.PERMITTED
                if permitted
                else RightsDecisionReason.OPERATION_RESTRICTED
            ),
        )

    async def require_article_use(
        self,
        *,
        article_id: UUID,
        operation: ArticleUseOperation,
        checked_at: datetime | None = None,
    ) -> ArticleRightsDecision:
        """Return an allowed decision or raise a content-free denial."""

        decision = await self.can_use_article(
            article_id=article_id,
            operation=operation,
            checked_at=checked_at,
        )
        if not decision.allowed:
            raise ArticleRightsDeniedError(decision)
        return decision

    async def update_rights(
        self,
        *,
        article_id: UUID,
        policy: ArticleRightsPolicy,
    ) -> ArticleRightsRecord | None:
        """Create a new immutable rights version and make it current."""

        return await self._repository.update_rights(
            article_id=article_id,
            policy=policy,
        )

    async def provenance_for_article(
        self,
        article_id: UUID,
    ) -> tuple[ArticleProvenanceRecord, ...]:
        """Return non-secret provenance in retrieval order."""

        return await self._repository.list_provenance(article_id)

    def _from_rights(
        self,
        rights: ArticleRightsRecord,
        operation: ArticleUseOperation,
        *,
        allowed: bool,
        reason: RightsDecisionReason,
    ) -> ArticleRightsDecision:
        return self._decision(
            article_id=rights.article_id,
            operation=operation,
            allowed=allowed,
            reason=reason,
            rights_version_id=rights.id,
            attribution_required=rights.attribution_required,
            attribution_text=rights.attribution_text,
        )

    @staticmethod
    def _decision(
        *,
        article_id: UUID,
        operation: ArticleUseOperation,
        allowed: bool,
        reason: RightsDecisionReason,
        rights_version_id: UUID | None = None,
        attribution_required: bool = False,
        attribution_text: str | None = None,
    ) -> ArticleRightsDecision:
        decision = ArticleRightsDecision(
            article_id=article_id,
            operation=operation,
            allowed=allowed,
            reason=reason,
            rights_version_id=rights_version_id,
            attribution_required=attribution_required,
            attribution_text=attribution_text,
        )
        logger.info(
            "article_rights_decision article_id=%s operation=%s allowed=%s "
            "reason=%s rights_version_id=%s",
            article_id,
            operation.value,
            allowed,
            reason.value,
            rights_version_id,
        )
        return decision
