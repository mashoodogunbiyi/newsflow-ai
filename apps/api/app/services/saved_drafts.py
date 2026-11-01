"""Application workflow for durable, owner-scoped LinkedIn drafts."""

import hashlib
import json
from uuid import UUID

from app.repositories.saved_drafts import SavedDraft, SavedDraftRepository
from app.services.authorization import require_owned_resource

MAX_DRAFT_CHARACTERS = 12_000


def _validate_text(edited_text: str) -> None:
    if not edited_text.strip():
        raise ValueError("Draft text must contain visible characters.")
    if len(edited_text) > MAX_DRAFT_CHARACTERS:
        raise ValueError("Draft text exceeds the supported size.")
    if "\x00" in edited_text:
        raise ValueError("Draft text contains an unsupported character.")


class SavedDraftService:
    """Coordinate safe saves without retaining raw idempotency keys."""

    def __init__(self, repository: SavedDraftRepository) -> None:
        self._repository = repository

    async def get(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
    ) -> SavedDraft:
        return require_owned_resource(
            await self._repository.get_for_owner(
                owner_id=owner_id,
                saved_draft_id=saved_draft_id,
            )
        )

    async def create(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        title: str | None,
        edited_text: str,
        selected_image_id: UUID | None,
        idempotency_key: str,
    ) -> SavedDraft:
        _validate_text(edited_text)
        key_hash = hashlib.sha256(f"{owner_id}:{idempotency_key}".encode()).hexdigest()
        payload_hash = hashlib.sha256(
            json.dumps(
                {
                    "edited_text": edited_text,
                    "generation_id": str(generation_id),
                    "selected_image_id": (
                        str(selected_image_id)
                        if selected_image_id is not None
                        else None
                    ),
                    "title": title,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        ).hexdigest()
        return require_owned_resource(
            await self._repository.create_for_owner(
                owner_id=owner_id,
                generation_id=generation_id,
                title=title,
                edited_text=edited_text,
                selected_image_id=selected_image_id,
                save_key_hash=key_hash,
                payload_hash=payload_hash,
            )
        )

    async def update(
        self,
        *,
        owner_id: UUID,
        saved_draft_id: UUID,
        expected_version: int,
        title: str | None,
        edited_text: str,
        selected_image_id: UUID | None,
    ) -> SavedDraft:
        _validate_text(edited_text)
        return require_owned_resource(
            await self._repository.update_for_owner(
                owner_id=owner_id,
                saved_draft_id=saved_draft_id,
                expected_version=expected_version,
                title=title,
                edited_text=edited_text,
                selected_image_id=selected_image_id,
            )
        )
