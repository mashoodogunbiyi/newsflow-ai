"""PostgreSQL article reads and owner-scoped LinkedIn draft persistence."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.sqlalchemy import SqlAlchemyDatabase
from app.database.tables import (
    ArticleSnapshotTable,
    ArticleTable,
    GeneratedPostTable,
    GenerationRunTable,
    PostVersionHashtagTable,
    PostVersionTable,
    SourceProfileTable,
)
from app.models.ai import AITextGenerationResult, AITokenUsage
from app.models.generation_preferences import LinkedInGenerationPreferences
from app.models.linkedin_generation import (
    LinkedInDraft,
    LinkedInDraftSourceReference,
)
from app.providers.models import NewsArticle

CATEGORY_VALUES = {
    "technology": "Technology",
    "business": "Business",
    "world_news": "World News",
    "science": "Science",
    "other": "Other",
}

CATEGORY_HASHTAGS = {
    "Technology": "#Technology",
    "Business": "#Business",
    "World News": "#WorldNews",
    "Science": "#Science",
    "Other": "#News",
}


class LinkedInGenerationRepositoryError(RuntimeError):
    """Raised when generation persistence fails without leaking database details."""


class LinkedInGenerationIdempotencyConflict(RuntimeError):
    """Raised when one idempotency key is reused for different inputs."""


@dataclass(frozen=True)
class LinkedInGenerationArticle:
    """Current immutable source snapshot used by the generation workflow."""

    article_id: UUID
    snapshot_id: UUID
    article: NewsArticle


class LinkedInGenerationRepository(Protocol):
    """Persistence operations required by the generation application service."""

    async def get_article(
        self,
        article_id: UUID,
    ) -> LinkedInGenerationArticle | None: ...

    async def get_draft_by_request_key(
        self,
        *,
        owner_id: UUID,
        request_key: str,
        request_marker: str,
    ) -> LinkedInDraft | None: ...

    async def save_draft(
        self,
        *,
        owner_id: UUID,
        source: LinkedInGenerationArticle,
        source_reference: LinkedInDraftSourceReference,
        preferences: LinkedInGenerationPreferences,
        prompt_version: str,
        request_key: str,
        request_marker: str,
        generated: AITextGenerationResult,
        draft_text: str,
        word_count: int,
    ) -> LinkedInDraft: ...

    async def get_draft_for_owner(
        self,
        *,
        owner_id: UUID,
        draft_id: UUID,
    ) -> LinkedInDraft | None: ...


class SqlAlchemyLinkedInGenerationRepository:
    """Read current source data and save private drafts in one transaction."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    async def get_article(
        self,
        article_id: UUID,
    ) -> LinkedInGenerationArticle | None:
        statement = (
            select(
                ArticleTable.id.label("article_id"),
                ArticleTable.current_snapshot_id.label("snapshot_id"),
                ArticleTable.source_item_id,
                SourceProfileTable.profile_key.label("source_profile"),
                ArticleSnapshotTable.contract_version,
                ArticleSnapshotTable.source_name,
                ArticleSnapshotTable.title,
                ArticleSnapshotTable.publication_date,
                ArticleSnapshotTable.category,
                ArticleSnapshotTable.description,
                ArticleSnapshotTable.canonical_url,
                ArticleSnapshotTable.permitted_content_status,
                ArticleSnapshotTable.permitted_content_type,
                ArticleSnapshotTable.permitted_content_text,
                ArticleSnapshotTable.ai_processing_allowed,
                ArticleSnapshotTable.derivative_output_allowed,
                ArticleSnapshotTable.attribution_display_name,
                ArticleSnapshotTable.attribution_text,
                ArticleSnapshotTable.byline,
                ArticleSnapshotTable.copyright_notice,
                ArticleSnapshotTable.rights_decision_ref,
                ArticleSnapshotTable.access_method,
                ArticleSnapshotTable.storage_allowed,
                ArticleSnapshotTable.display_allowed,
                ArticleSnapshotTable.rights_expires_at,
                ArticleSnapshotTable.retention_rule,
                ArticleSnapshotTable.retrieved_at,
                ArticleSnapshotTable.source_modified_at,
            )
            .join(
                ArticleSnapshotTable,
                and_(
                    ArticleSnapshotTable.id == ArticleTable.current_snapshot_id,
                    ArticleSnapshotTable.article_id == ArticleTable.id,
                ),
            )
            .join(
                SourceProfileTable,
                SourceProfileTable.id == ArticleTable.source_profile_id,
            )
            .where(
                ArticleTable.id == article_id,
                ArticleTable.status == "active",
                SourceProfileTable.status == "enabled",
            )
        )
        try:
            async with self._database.session() as session:
                row = (await session.execute(statement)).one_or_none()
        except SQLAlchemyError as exc:
            raise LinkedInGenerationRepositoryError(
                "The selected article could not be read."
            ) from exc
        if row is None:
            return None

        try:
            article = NewsArticle.model_validate(
                {
                    "contract_version": row.contract_version,
                    "source_profile": row.source_profile,
                    "source_item_id": row.source_item_id,
                    "source_name": row.source_name,
                    "title": row.title,
                    "publication_date": row.publication_date,
                    "category": CATEGORY_VALUES[row.category],
                    "description": row.description,
                    "url": row.canonical_url,
                    "permitted_content": {
                        "status": row.permitted_content_status,
                        "content_type": row.permitted_content_type,
                        "text": row.permitted_content_text,
                        "ai_processing_allowed": row.ai_processing_allowed,
                        "derivative_output_allowed": (row.derivative_output_allowed),
                    },
                    "attribution": {
                        "display_name": row.attribution_display_name,
                        "canonical_url": row.canonical_url,
                        "attribution_text": row.attribution_text,
                        "byline": row.byline,
                        "copyright_notice": row.copyright_notice,
                    },
                    "rights": {
                        "decision_id": row.rights_decision_ref,
                        "access_method": row.access_method,
                        "storage_allowed": row.storage_allowed,
                        "display_allowed": row.display_allowed,
                        "expires_at": row.rights_expires_at,
                        "retention_rule": row.retention_rule,
                    },
                    "retrieved_at": row.retrieved_at,
                    "modified_at": row.source_modified_at,
                }
            )
        except (KeyError, ValidationError) as exc:
            raise LinkedInGenerationRepositoryError(
                "The stored article is not valid for generation."
            ) from exc
        return LinkedInGenerationArticle(
            article_id=row.article_id,
            snapshot_id=row.snapshot_id,
            article=article,
        )

    async def get_draft_by_request_key(
        self,
        *,
        owner_id: UUID,
        request_key: str,
        request_marker: str,
    ) -> LinkedInDraft | None:
        try:
            async with self._database.session() as session:
                return await self._draft_by_request_key(
                    session,
                    owner_id=owner_id,
                    request_key=request_key,
                    request_marker=request_marker,
                )
        except LinkedInGenerationIdempotencyConflict:
            raise
        except SQLAlchemyError as exc:
            raise LinkedInGenerationRepositoryError(
                "The generation request could not be checked."
            ) from exc

    async def save_draft(
        self,
        *,
        owner_id: UUID,
        source: LinkedInGenerationArticle,
        source_reference: LinkedInDraftSourceReference,
        preferences: LinkedInGenerationPreferences,
        prompt_version: str,
        request_key: str,
        request_marker: str,
        generated: AITextGenerationResult,
        draft_text: str,
        word_count: int,
    ) -> LinkedInDraft:
        now = datetime.now(UTC)
        draft_id = uuid4()
        generation_id = uuid4()
        version_id = uuid4()
        try:
            async with self._database.session() as session:
                async with session.begin():
                    lock_key = f"{owner_id}:{request_key}"
                    await session.execute(
                        select(
                            func.pg_advisory_xact_lock(
                                func.hashtextextended(lock_key, 0)
                            )
                        )
                    )
                    existing = await self._draft_by_request_key(
                        session,
                        owner_id=owner_id,
                        request_key=request_key,
                        request_marker=request_marker,
                    )
                    if existing is not None:
                        return existing

                    session.add(
                        GeneratedPostTable(
                            id=draft_id,
                            user_id=owner_id,
                            article_snapshot_id=source.snapshot_id,
                            status="draft",
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    session.add(
                        GenerationRunTable(
                            id=generation_id,
                            generated_post_id=draft_id,
                            article_rights_version_id=(
                                source_reference.rights_version_id
                            ),
                            generation_type="post",
                            status="succeeded",
                            idempotency_key=request_key,
                            provider="openai",
                            model=generated.model,
                            prompt_template_version=prompt_version,
                            prompt_text=request_marker,
                            provider_request_id=(
                                generated.request_id or generated.response_id
                            ),
                            attempt_count=1,
                            input_tokens=generated.usage.input_tokens,
                            output_tokens=generated.usage.output_tokens,
                            started_at=now,
                            completed_at=now,
                        )
                    )
                    session.add(
                        PostVersionTable(
                            id=version_id,
                            generated_post_id=draft_id,
                            generation_run_id=generation_id,
                            previous_version_id=None,
                            version_number=1,
                            origin="ai",
                            tone=preferences.tone.value,
                            length_option=preferences.post_length.value,
                            audience="general_professionals",
                            hook=self._hook(draft_text),
                            summary=draft_text,
                            insight=None,
                            call_to_action=None,
                            rendered_text=draft_text,
                            source_attribution=(source_reference.attribution_text),
                            word_count=word_count,
                            is_current=True,
                            created_by_user_id=owner_id,
                            created_at=now,
                        )
                    )
                    category_hashtag = CATEGORY_HASHTAGS[source.article.category.value]
                    for position, hashtag in enumerate(
                        ("#NewsFlowAI", "#ProfessionalInsights", category_hashtag),
                        start=1,
                    ):
                        session.add(
                            PostVersionHashtagTable(
                                post_version_id=version_id,
                                position=position,
                                hashtag=hashtag,
                            )
                        )
        except LinkedInGenerationIdempotencyConflict:
            raise
        except SQLAlchemyError as exc:
            raise LinkedInGenerationRepositoryError(
                "The generated draft could not be stored."
            ) from exc

        return LinkedInDraft(
            draft_id=draft_id,
            generation_id=generation_id,
            owner_id=owner_id,
            draft=draft_text,
            source=source_reference,
            tone=preferences.tone,
            length=preferences.post_length,
            prompt_version=prompt_version,
            model_identifier=generated.model,
            token_usage=generated.usage,
            created_at=now,
        )

    async def get_draft_for_owner(
        self,
        *,
        owner_id: UUID,
        draft_id: UUID,
    ) -> LinkedInDraft | None:
        try:
            async with self._database.session() as session:
                row = (
                    await session.execute(
                        self._draft_statement().where(
                            GeneratedPostTable.id == draft_id,
                            GeneratedPostTable.user_id == owner_id,
                        )
                    )
                ).one_or_none()
        except SQLAlchemyError as exc:
            raise LinkedInGenerationRepositoryError(
                "The generated draft could not be read."
            ) from exc
        return None if row is None else self._draft_from_row(row)

    async def _draft_by_request_key(
        self,
        session: AsyncSession,
        *,
        owner_id: UUID,
        request_key: str,
        request_marker: str,
    ) -> LinkedInDraft | None:
        row = (
            await session.execute(
                self._draft_statement().where(
                    GeneratedPostTable.user_id == owner_id,
                    GenerationRunTable.idempotency_key == request_key,
                )
            )
        ).one_or_none()
        if row is None:
            return None
        if row.request_marker != request_marker:
            raise LinkedInGenerationIdempotencyConflict(
                "The idempotency key has already been used for another request."
            )
        return self._draft_from_row(row)

    @staticmethod
    def _draft_statement():
        return (
            select(
                GeneratedPostTable.id.label("draft_id"),
                GeneratedPostTable.user_id.label("owner_id"),
                GenerationRunTable.id.label("generation_id"),
                GenerationRunTable.article_rights_version_id.label("rights_version_id"),
                GenerationRunTable.prompt_template_version.label("prompt_version"),
                GenerationRunTable.prompt_text.label("request_marker"),
                GenerationRunTable.model.label("model_identifier"),
                GenerationRunTable.input_tokens,
                GenerationRunTable.output_tokens,
                GenerationRunTable.created_at,
                PostVersionTable.rendered_text.label("draft"),
                PostVersionTable.tone,
                PostVersionTable.length_option,
                PostVersionTable.source_attribution,
                ArticleTable.id.label("article_id"),
                ArticleSnapshotTable.title,
                ArticleSnapshotTable.source_name,
                ArticleSnapshotTable.canonical_url,
            )
            .join(
                GenerationRunTable,
                GenerationRunTable.generated_post_id == GeneratedPostTable.id,
            )
            .join(
                PostVersionTable,
                and_(
                    PostVersionTable.generated_post_id == GeneratedPostTable.id,
                    PostVersionTable.generation_run_id == GenerationRunTable.id,
                    PostVersionTable.is_current.is_(True),
                ),
            )
            .join(
                ArticleSnapshotTable,
                ArticleSnapshotTable.id == GeneratedPostTable.article_snapshot_id,
            )
            .join(
                ArticleTable,
                ArticleTable.id == ArticleSnapshotTable.article_id,
            )
            .where(
                GeneratedPostTable.deleted_at.is_(None),
                GeneratedPostTable.status == "draft",
                GenerationRunTable.status == "succeeded",
            )
        )

    @staticmethod
    def _draft_from_row(row: object) -> LinkedInDraft:
        input_tokens = row.input_tokens
        output_tokens = row.output_tokens
        total_tokens = (
            None
            if input_tokens is None or output_tokens is None
            else input_tokens + output_tokens
        )
        return LinkedInDraft(
            draft_id=row.draft_id,
            generation_id=row.generation_id,
            owner_id=row.owner_id,
            draft=row.draft,
            source=LinkedInDraftSourceReference(
                article_id=row.article_id,
                title=row.title,
                source_name=row.source_name,
                source_url=row.canonical_url,
                attribution_text=row.source_attribution,
                rights_version_id=row.rights_version_id,
            ),
            tone=row.tone,
            length=row.length_option,
            prompt_version=row.prompt_version,
            model_identifier=row.model_identifier,
            token_usage=AITokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
            created_at=row.created_at,
        )

    @staticmethod
    def _hook(draft_text: str) -> str:
        return next(
            (line.strip() for line in draft_text.splitlines() if line.strip()),
            draft_text,
        )
