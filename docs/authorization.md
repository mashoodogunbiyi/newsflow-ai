# NewsFlow AI Object-Level Authorisation

## Purpose

This document records the NFA-25 rules that prevent one NewsFlow AI user from accessing another user's private content.

Authentication and authorisation solve different problems:

- Authentication confirms which user is logged in through an active server-managed session.
- Authorisation confirms that the logged-in user owns the exact record being requested.

Both checks are required. A valid login does not give a user access to every record in the database.

## Current private resources

The current protected API manages `saved_content_items`. A saved item refers to a generated post, a selected post version, and optionally a generated image.

PostgreSQL stores ownership in these places:

- `generated_posts.user_id` identifies the owner of a generated post.
- `saved_content_items.user_id` identifies the owner of a saved library item.
- The composite foreign key from `saved_content_items(generated_post_id, user_id)` to `generated_posts(id, user_id)` prevents a saved item from pointing to another user's post.
- Post-version and image foreign keys ensure that selected resources belong to the same generated post.

The existing NFA-20 migration already provides these database controls, so NFA-25 does not require a new migration.

## Ownership rules

| Operation | Required rule |
|---|---|
| Create | The owner ID comes only from the active session. The post, version, and optional image must belong to that owner. |
| List | Query by the active session's user ID and return only that user's non-deleted records. |
| Read | Match both the requested item ID and active session's user ID. |
| Update | Match both IDs and require the session-specific CSRF token. |
| Delete | Match both IDs, require CSRF, and soft-delete only the matching owned row. |
| Export | Match both IDs before reading or returning any private text. |

The API never accepts `user_id` in a content-library request. Pydantic rejects unexpected fields. The backend obtains the trusted user ID from the authenticated session and passes it into every repository method.

## Protected endpoints

| Method | Endpoint | Behaviour |
|---|---|---|
| `POST` | `/api/v1/library/items` | Save an owned generated post. |
| `GET` | `/api/v1/library/items` | List only the authenticated user's items. |
| `GET` | `/api/v1/library/items/{item_id}` | Read one owned item. |
| `PATCH` | `/api/v1/library/items/{item_id}` | Rename one owned item. |
| `DELETE` | `/api/v1/library/items/{item_id}` | Soft-delete one owned item. |
| `GET` | `/api/v1/library/items/{item_id}/export` | Export one owned item as plain text. |

Private responses use `Cache-Control: no-store` so browsers and shared caches are told not to retain them.

## Safe failure behaviour

- HTTP `401` means an active authenticated session was not supplied.
- HTTP `403` means a state-changing request failed CSRF validation.
- HTTP `404` with code `private_resource_not_found` is used for both a missing item and an item owned by another user.
- HTTP `409` means the owner has already saved the same generated post.
- HTTP `503` gives a generic storage-unavailable message without database details.

Using the same `404` response for missing and differently owned resources prevents a user from discovering whether another user's private record exists.

## Reusable implementation

Protected routes use shared authentication dependencies:

- `require_authenticated_session` for owner-scoped reads and exports.
- `require_csrf_authenticated_session` for creates, updates, and deletes.

The reusable `require_owned_resource` service check converts every empty owner-scoped repository result into the same private-resource outcome. Repository methods also require `owner_id`, making an unscoped content-library query harder to introduce accidentally.

Future APIs for generated posts, generations, post edits, images, downloads, and other private resources must follow the same pattern:

1. Resolve the active session.
2. Derive the owner ID only from that session.
3. Include the owner ID in the database query itself.
4. Require CSRF proof for a cookie-authenticated state change.
5. Return the standard private `404` when no owned row matches.
6. Add cross-user tests for every read, update, delete, download, and export path.

## Automated evidence

`apps/api/tests/test_authorization.py` verifies that:

- An unauthenticated user cannot list private content.
- Each collection contains only the authenticated user's records.
- User B cannot read, change, delete, or export User A's item.
- Cross-user attempts return the same safe `404` and expose no private text.
- The owner can read, rename, export, and delete their own item.
- A client-supplied `user_id` is rejected.
- A user cannot save another user's generated post or version.
- State-changing requests require the session-specific CSRF token.
- OpenAPI documents the protected endpoints and session-cookie security.

Run the checks from `apps/api`:

```bash
ruff check .
ruff format --check .
pytest
```

## Review status

- Jira issue: NFA-25
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
