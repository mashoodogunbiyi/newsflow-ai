# NFA-67 - LinkedIn Draft Persistence

## Outcome

NewsFlow AI can now save and update an authenticated user's reviewed LinkedIn draft in PostgreSQL while preserving its source article, original AI generation, selected approved image, ownership, and version history.

The implementation extends the existing `generated_posts`, `generation_runs`, `post_versions`, `generated_images`, and `saved_content_items` records. It does not create a second draft table or overwrite the original AI output.

## Data model

| Record | Purpose |
| --- | --- |
| `generation_runs` | Retains the exact successful AI generation, model, and prompt-template version that started the draft. |
| `post_versions` | Retains immutable AI and manual text versions. A user text edit creates a new row linked through `previous_version_id`. |
| `generated_images` | Retains private image ownership, post association, validation, safety, and availability state. |
| `saved_content_items` | Points to the current saved text version and optional selected image for one owned generated post. |

Migration `20261101_0013_saved_draft_persistence.py` adds:

- `source_generation_id` to preserve the exact original generation.
- `version` for optimistic concurrency control.
- SHA-256 `save_key_hash` and `save_payload_hash` values for safe idempotent retries.
- A source-generation foreign key, positive-version constraint, hash validation, and owner-scoped unique save-key index.

Raw idempotency keys are not stored. The hashes do not contain draft text, article text, credentials, or restricted source content.

## Version rules

The original AI version remains immutable with `origin = "ai"` and its `generation_run_id`.

The first durable save creates a manual version containing the exact text reviewed by the user. A later text update:

1. Locks the owned saved item.
2. Confirms the client's `expected_version` is current.
3. Marks the previous text version as no longer current.
4. Adds a new `origin = "manual"` version linked to the previous version.
5. Updates the saved item to select the new version.

A title-only or image-only update changes the saved item but does not duplicate the text version. An update that changes nothing returns the existing record without increasing its version.

## API contract

All responses use `Cache-Control: no-store`. Writes require an authenticated HTTP-only session cookie and valid CSRF proof.

### Save a draft

```text
POST /api/v1/drafts
Idempotency-Key: nfa67-save-001
```

```json
{
  "generation_id": "00000000-0000-4000-8000-000000000001",
  "title": "Optional private library title",
  "edited_text": "The complete human-reviewed LinkedIn draft.",
  "selected_image_id": null
}
```

The idempotency key must contain 8 to 128 letters, numbers, dots, underscores, colons, or ASCII hyphens. Repeating the same key and payload returns the same saved record. Reusing that key for different content returns a conflict. A different key cannot create a second active saved item for the same generated post.

### Read a draft

```text
GET /api/v1/drafts/{saved_draft_id}
```

The query includes the authenticated owner. A missing record and another user's record both return the same safe not-found response.

### Update a draft

```text
PUT /api/v1/drafts/{saved_draft_id}
```

```json
{
  "expected_version": 1,
  "title": "Reviewed title",
  "edited_text": "The complete updated LinkedIn draft.",
  "selected_image_id": null
}
```

The request supplies the full editable state and the version last read by the client. If another update has already increased the version, the request returns `draft_version_conflict` instead of silently overwriting newer work.

## Validation and authorisation

- Draft text must contain visible characters and cannot exceed 12,000 characters.
- NUL characters and unknown request properties are rejected.
- A generation must be a successful post generation owned by the active user.
- An optional image must belong to the same user and generated post.
- A selected image must be available, safety-approved, validation-passed, generation-completed, and not deleted.
- A missing, inaccessible, differently owned, or invalid associated resource returns the same safe `private_resource_not_found` result.
- Owner identifiers, database hashes, credentials, internal storage keys, prompts, and restricted source text are excluded from responses.

## Transaction and failure behaviour

Each create or update is one database transaction. Text-version creation, hashtag copying, selected-version changes, saved-item changes, and generated-post status changes either commit together or roll back together.

| Condition | HTTP status | Safe code |
| --- | ---: | --- |
| Missing authentication | 401 | `authentication_required` |
| Failed CSRF check | 403 | `csrf_validation_failed` |
| Invalid input | 422 | `validation_error` |
| Missing or inaccessible private resource | 404 | `private_resource_not_found` |
| Existing saved draft | 409 | `draft_already_saved` |
| Idempotency key reused for another payload | 409 | `idempotency_key_conflict` |
| Stale update version | 409 | `draft_version_conflict` |
| Database unavailable or transaction failure | 503 | `draft_persistence_unavailable` |

Database details, draft text, source text, and secrets are not placed in public errors.

## Verification

Fast tests use an isolated repository double and cover:

- Authentication and bounded input validation.
- Source, generation, selected-image, and timestamp preservation.
- Idempotent replay, changed-payload conflict, and duplicate prevention.
- Manual text-version updates and original-generation preservation.
- Stale update rejection and cross-user isolation.
- Invalid image rejection and transaction-failure response handling.

Run them from the repository root:

```bash
apps/api/.venv/bin/pytest -q apps/api/tests/test_saved_drafts.py
```

The PostgreSQL test applies every migration to a deliberately named disposable database, performs a real save and update, rejects a stale write, inspects all immutable versions, and then removes the schema:

```bash
cd apps/api
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_saved_draft_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_saved_draft_integration.py
```

Never point this command at the normal development, shared, staging, or production database. GitHub Actions creates the isolated database and runs this proof automatically.

## Limitations and next steps

- NFA-67 provides backend persistence. The E7 frontend save controls, content-library screen, copy, export, and deletion workflows remain separate tasks.
- The update endpoint uses full replacement for the editable title, text, and selected-image state. Clients must refresh after a version conflict.
- Saved drafts remain private application content and are never published to LinkedIn automatically.
- Live CNN integration remains blocked by ADR-001 until explicit authorisation and a Go decision exist.
