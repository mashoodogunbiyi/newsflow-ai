"""NFA-32 provenance and fail-closed article-rights tests."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.models.article_rights import (
    ArticleProvenanceRecord,
    ArticleRightsPolicy,
    ArticleRightsRecord,
    ArticleUseOperation,
    RightsDecisionReason,
    RightsVerificationStatus,
)
from app.repositories.article_rights import CurrentArticleRights
from app.services.article_rights import ArticleRightsDeniedError, ArticleRightsService

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


def run(coroutine):
    """Run one asynchronous service call."""

    return asyncio.run(coroutine)


def policy(**changes: object) -> ArticleRightsPolicy:
    """Build one verified synthetic rights policy."""

    values: dict[str, object] = {
        "verification_status": RightsVerificationStatus.VERIFIED,
        "storage_allowed": True,
        "display_allowed": True,
        "ai_processing_allowed": True,
        "derivative_output_allowed": True,
        "redistribution_allowed": False,
        "attribution_required": True,
        "attribution_text": "Source: synthetic NewsFlow AI fixture.",
        "retention_rule": "development-only",
        "retention_expires_at": NOW + timedelta(days=30),
        "authorisation_reference": "NFA-SRC-AUTH-001",
        "source_contract_version": "1.0",
        "rights_last_verified_at": NOW - timedelta(days=1),
        "effective_from": NOW - timedelta(days=1),
    }
    values.update(changes)
    return ArticleRightsPolicy.model_validate(values)


def record(article_id: UUID, **changes: object) -> ArticleRightsRecord:
    """Build a persisted rights record."""

    values = policy(**changes).model_dump()
    return ArticleRightsRecord(
        id=uuid4(),
        article_id=article_id,
        version_number=1,
        superseded_at=None,
        **values,
    )


@dataclass
class InMemoryRightsRepository:
    """Small repository fake that preserves rights history and provenance."""

    current: dict[UUID, CurrentArticleRights] = field(default_factory=dict)
    history: dict[UUID, list[ArticleRightsRecord]] = field(default_factory=dict)
    provenance: dict[UUID, list[ArticleProvenanceRecord]] = field(default_factory=dict)

    async def get_current(self, article_id: UUID) -> CurrentArticleRights | None:
        return self.current.get(article_id)

    async def update_rights(
        self,
        *,
        article_id: UUID,
        policy: ArticleRightsPolicy,
    ) -> ArticleRightsRecord | None:
        previous = self.current.get(article_id)
        version = 1 if previous is None else previous.record.version_number + 1
        updated = ArticleRightsRecord(
            id=uuid4(),
            article_id=article_id,
            version_number=version,
            superseded_at=None,
            **policy.model_dump(),
        )
        self.history.setdefault(article_id, []).append(updated)
        self.current[article_id] = CurrentArticleRights(updated, True)
        return updated

    async def list_provenance(
        self,
        article_id: UUID,
    ) -> tuple[ArticleProvenanceRecord, ...]:
        return tuple(self.provenance.get(article_id, []))


def service_with(
    rights: ArticleRightsRecord | None,
    *,
    source_enabled: bool = True,
) -> tuple[ArticleRightsService, InMemoryRightsRepository, UUID]:
    article_id = rights.article_id if rights is not None else uuid4()
    repository = InMemoryRightsRepository()
    if rights is not None:
        repository.current[article_id] = CurrentArticleRights(
            rights,
            source_enabled,
        )
        repository.history[article_id] = [rights]
    return ArticleRightsService(repository), repository, article_id


def test_verified_rights_allow_display_and_return_attribution() -> None:
    article_id = uuid4()
    service, _, _ = service_with(record(article_id))

    decision = run(
        service.can_use_article(
            article_id=article_id,
            operation=ArticleUseOperation.DISPLAY_METADATA,
            checked_at=NOW,
        )
    )

    assert decision.allowed is True
    assert decision.reason == RightsDecisionReason.PERMITTED
    assert decision.attribution_text == "Source: synthetic NewsFlow AI fixture."


@pytest.mark.parametrize(
    ("rights", "source_enabled", "reason"),
    [
        (None, True, RightsDecisionReason.MISSING_RIGHTS),
        (
            record(
                uuid4(),
                verification_status=RightsVerificationStatus.UNVERIFIED,
                storage_allowed=False,
                display_allowed=False,
                ai_processing_allowed=False,
                derivative_output_allowed=False,
                redistribution_allowed=False,
                rights_last_verified_at=None,
            ),
            True,
            RightsDecisionReason.UNVERIFIED_RIGHTS,
        ),
        (record(uuid4()), False, RightsDecisionReason.SOURCE_DISABLED),
        (
            record(
                uuid4(),
                retention_expires_at=NOW - timedelta(hours=1),
                effective_from=NOW - timedelta(days=2),
            ),
            True,
            RightsDecisionReason.EXPIRED_RIGHTS,
        ),
    ],
)
def test_unsafe_rights_states_fail_closed(
    rights: ArticleRightsRecord | None,
    source_enabled: bool,
    reason: RightsDecisionReason,
) -> None:
    service, _, article_id = service_with(rights, source_enabled=source_enabled)

    decision = run(
        service.can_use_article(
            article_id=article_id,
            operation=ArticleUseOperation.USE_FOR_AI_GENERATION,
            checked_at=NOW,
        )
    )

    assert decision.allowed is False
    assert decision.reason == reason


def test_ai_requires_processing_and_derivative_permissions() -> None:
    article_id = uuid4()
    restricted = record(
        article_id,
        ai_processing_allowed=False,
        derivative_output_allowed=False,
    )
    service, _, _ = service_with(restricted)

    decision = run(
        service.can_use_article(
            article_id=article_id,
            operation=ArticleUseOperation.USE_FOR_AI_GENERATION,
            checked_at=NOW,
        )
    )

    assert decision.allowed is False
    assert decision.reason == RightsDecisionReason.OPERATION_RESTRICTED


def test_rights_update_creates_a_new_version_used_immediately() -> None:
    article_id = uuid4()
    service, repository, _ = service_with(record(article_id))
    revoked = policy(
        verification_status=RightsVerificationStatus.REVOKED,
        storage_allowed=False,
        display_allowed=False,
        ai_processing_allowed=False,
        derivative_output_allowed=False,
        redistribution_allowed=False,
        rights_last_verified_at=None,
        effective_from=NOW,
        retention_expires_at=None,
    )

    updated = run(service.update_rights(article_id=article_id, policy=revoked))
    decision = run(
        service.can_use_article(
            article_id=article_id,
            operation=ArticleUseOperation.DISPLAY_METADATA,
            checked_at=NOW,
        )
    )

    assert updated is not None
    assert updated.version_number == 2
    assert len(repository.history[article_id]) == 2
    assert decision.reason == RightsDecisionReason.REVOKED_RIGHTS


def test_provenance_can_be_retrieved_for_the_article() -> None:
    article_id = uuid4()
    service, repository, _ = service_with(record(article_id))
    evidence = ArticleProvenanceRecord(
        id=uuid4(),
        article_id=article_id,
        source_profile_id=uuid4(),
        provider_id="fixture-v1",
        external_article_id="synthetic-001",
        canonical_url="https://example.invalid/synthetic-001",
        published_at=NOW - timedelta(hours=2),
        retrieved_at=NOW - timedelta(hours=1),
        source_integration_id="fixture-v1",
        source_contract_version="1.0",
        authorisation_reference="NFA-SRC-AUTH-001",
        ingestion_action="created",
    )
    repository.provenance[article_id] = [evidence]

    assert run(service.provenance_for_article(article_id)) == (evidence,)


def test_required_operation_raises_safe_denial() -> None:
    service, _, article_id = service_with(None)

    with pytest.raises(ArticleRightsDeniedError, match="not permitted"):
        run(
            service.require_article_use(
                article_id=article_id,
                operation=ArticleUseOperation.RETAIN_ARTICLE,
                checked_at=NOW,
            )
        )


def test_logs_contain_decision_metadata_but_not_article_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    article_id = uuid4()
    service, _, _ = service_with(record(article_id))

    with caplog.at_level(logging.INFO):
        run(
            service.can_use_article(
                article_id=article_id,
                operation=ArticleUseOperation.DISPLAY_METADATA,
                checked_at=NOW,
            )
        )

    assert str(article_id) in caplog.text
    assert "synthetic NewsFlow AI fixture" not in caplog.text


@pytest.mark.parametrize(
    "changes",
    [
        {
            "verification_status": RightsVerificationStatus.UNVERIFIED,
            "rights_last_verified_at": None,
        },
        {
            "derivative_output_allowed": True,
            "ai_processing_allowed": False,
        },
        {"attribution_required": True, "attribution_text": None},
    ],
)
def test_invalid_rights_policies_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        policy(**changes)
