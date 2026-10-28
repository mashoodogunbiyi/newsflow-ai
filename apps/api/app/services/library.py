"""Owner-scoped application workflows for saved NewsFlow AI content."""

from uuid import UUID

from app.repositories import SavedContent, SavedContentRepository
from app.services.authorization import require_owned_resource


class SavedContentService:
    """Use only the authenticated session owner for private-content access."""

    def __init__(self, repository: SavedContentRepository) -> None:
        self._repository = repository

    async def list_items(self, *, owner_id: UUID) -> list[SavedContent]:
        return await self._repository.list_for_owner(owner_id=owner_id)

    async def get_item(self, *, owner_id: UUID, item_id: UUID) -> SavedContent:
        return require_owned_resource(
            await self._repository.get_for_owner(
                owner_id=owner_id,
                item_id=item_id,
            )
        )

    async def save_item(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        selected_post_version_id: UUID,
        selected_image_id: UUID | None,
        library_title: str | None,
    ) -> SavedContent:
        return require_owned_resource(
            await self._repository.create_for_owner(
                owner_id=owner_id,
                generated_post_id=generated_post_id,
                selected_post_version_id=selected_post_version_id,
                selected_image_id=selected_image_id,
                library_title=library_title,
            )
        )

    async def update_title(
        self,
        *,
        owner_id: UUID,
        item_id: UUID,
        library_title: str | None,
    ) -> SavedContent:
        return require_owned_resource(
            await self._repository.update_title_for_owner(
                owner_id=owner_id,
                item_id=item_id,
                library_title=library_title,
            )
        )

    async def delete_item(self, *, owner_id: UUID, item_id: UUID) -> None:
        require_owned_resource(
            True
            if await self._repository.delete_for_owner(
                owner_id=owner_id,
                item_id=item_id,
            )
            else None
        )

    async def export_item(self, *, owner_id: UUID, item_id: UUID) -> str:
        item = await self.get_item(owner_id=owner_id, item_id=item_id)
        title = f"{item.library_title}\n\n" if item.library_title else ""
        return f"{title}{item.rendered_text}\n\n{item.source_attribution}\n"
