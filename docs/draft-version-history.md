# NFA-70 - Saved Draft Version History

## Purpose

NewsFlow AI keeps an immutable history of meaningful changes to each private saved LinkedIn draft. A user can inspect earlier text, source attribution, title, and selected image without replacing the current draft. Restoration is supported and always appends a new current version.

## Versioning policy

A history entry is created in the same PostgreSQL transaction as each meaningful saved-state change:

- `initial_save` - the first durable save, linked to its source text-generation run.
- `manual_edit` - the user changes the draft text.
- `text_regeneration` - saved text exactly matches a verified AI post version for the same generated post; the associated generation run is recorded.
- `image_selection` - the selected image changes to an original generated image.
- `image_regeneration` - the selected image changes to an immutable child image with a recorded parent.
- `metadata_update` - the library title changes without a text or image change.
- `version_restoration` - an earlier history entry is restored as a new current version.

A request that does not change the saved state creates no history entry. If text and image change in one request, the text change is the primary change type and the selected image reference is still captured in the same snapshot.

The history `version_number` follows the saved draft's optimistic concurrency version. A stale update or restoration receives `409 draft_version_conflict` and writes nothing.

## Storage model

Migration `20261102_0014` creates `saved_draft_versions`. Each row records:

- The saved draft, owner, and generated post.
- The immutable post-version reference.
- The optional immutable image and generation-run references.
- The version number, change type, title, restoration link, and timestamp.

Text remains in `post_versions`; image bytes remain in private image storage. The history ledger stores references instead of copying large image files. Composite foreign keys bind every entry to the correct owner and generated post. The unique draft-and-version constraint prevents duplicate version numbers.

Historical rows have no update or delete API. Database foreign keys use restrictive deletion, and application code only appends entries.

## API contract

All endpoints require the existing HTTP-only authenticated session. Responses use `Cache-Control: private, no-store`.

```text
GET  /api/v1/drafts/{draft_id}/versions
GET  /api/v1/drafts/{draft_id}/versions/{version_id}
POST /api/v1/drafts/{draft_id}/versions/{version_id}/restore
```

The collection is bounded to 100 entries per page and ordered by descending version number. Retrieval returns permitted source and image metadata, but never owner IDs, private storage keys, provider prompts, credentials, or internal paths.

Restoration requires CSRF proof and the current `expected_version`. The backend copies the selected historical post state into a new immutable post version, updates the current saved draft, and appends a `version_restoration` ledger entry. It never changes the selected historical row. A deleted or no-longer-permitted image cannot be restored.

No direct `PUT`, `PATCH`, or `DELETE` route exists for a history entry.

## Authorisation and retention

Every query includes both the authenticated owner and draft ID. Another user's entry, an unknown entry, and a deleted parent draft all return the same private `404` response.

History remains accessible only while its parent saved draft is active. Soft-deleting a saved draft immediately makes its history unavailable through the API. Physical deletion and long-term retention follow the content-retention work planned under T7.6. Until that policy is implemented, restrictive foreign keys prevent private history from becoming detached or silently destroyed.

## Frontend behaviour

The saved-draft page displays history newest first with version number, UTC timestamp, current marker, change label, and a bounded text preview. Each link opens a read-only historical detail page that preserves the permitted source and selected private image. The current editor remains separate, so reviewing history cannot overwrite local or saved work.

## Verification

Backend tests cover newest-first retrieval, selected-version retrieval, owner isolation, unavailable direct modification, append-only restoration, and stale restoration conflicts. Frontend tests cover runtime contract validation, history rendering, labels, links, and controlled failure handling.

Run:

```bash
cd apps/api
.venv/bin/pytest -q tests/test_saved_drafts.py tests/test_draft_version_history.py
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests

cd ../web
npm test
npm run lint
npm run typecheck
npm run format:check
```

PostgreSQL migration and integration checks require the isolated test database described in `docs/development-setup.md`.
