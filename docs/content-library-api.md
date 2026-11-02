# NFA-68 - Content Library REST API

## Outcome

NewsFlow AI now provides a secure REST API for an authenticated user to create, list, retrieve, and update their saved LinkedIn drafts. The API builds on NFA-67's transactional persistence and immutable version history instead of introducing a second content store.

## Endpoint contract

The project uses its established versioned backend prefix, so the implemented routes are under `/api/v1/drafts`.

| Method | Route | Purpose | CSRF proof |
| --- | --- | --- | --- |
| `POST` | `/api/v1/drafts` | Save one reviewed generation in the user's library. | Required |
| `GET` | `/api/v1/drafts` | List a bounded page of the user's saved drafts. | Not required |
| `GET` | `/api/v1/drafts/{saved_draft_id}` | Retrieve one owned saved draft. | Not required |
| `PATCH` | `/api/v1/drafts/{saved_draft_id}` | Update only the supplied editable fields. | Required |
| `PUT` | `/api/v1/drafts/{saved_draft_id}` | Replace the complete editable state using the NFA-67 contract. | Required |

Deletion is deliberately not part of NFA-68. It remains a later E7 task.

## Authentication and object authorisation

- Every endpoint requires the server-managed HTTP-only session cookie.
- Write endpoints also require the session's matching CSRF proof.
- The backend derives the owner ID only from the authenticated session. A client cannot submit or override it.
- Every read and write query includes that owner ID.
- A missing UUID and a UUID belonging to another user both return the same `private_resource_not_found` response.
- Collection queries cannot return another user's records.
- Responses use private, no-store caching and never expose owner IDs, password data, database hashes, private storage keys, credentials, prompts, or restricted source content.

## Create and duplicate behaviour

`POST /api/v1/drafts` accepts the generation UUID, reviewed draft text, an optional private title, and an optional approved image UUID. It requires an `Idempotency-Key` header.

The existing NFA-67 rules remain authoritative:

- The generation must be successful and owned by the active user.
- The original AI version and exact source-generation lineage remain immutable.
- The reviewed text is stored as a manual version.
- A selected image must be owned by the same user, linked to the same post, available, safety-approved, validation-passed, completed, and not deleted.
- Replaying the same idempotency key and payload returns the existing record.
- Reusing the key for different content returns `idempotency_key_conflict`.
- Attempting to save the same generated post twice returns `draft_already_saved`.

## List, pagination, and sorting

```text
GET /api/v1/drafts?page=1&page_size=20
```

| Query parameter | Default | Allowed values |
| --- | ---: | --- |
| `page` | `1` | Integer of at least `1` |
| `page_size` | `20` | Integer from `1` to `100` |

The sort is fixed as `updated_at_desc`. The database orders by `updated_at` from newest to oldest and then by draft UUID from highest to lowest as a deterministic tie-breaker. A later page therefore has a stable definition for the same underlying data snapshot.

Example collection shape:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total_items": 0,
  "total_pages": 0,
  "sort": "updated_at_desc"
}
```

Requesting a valid page beyond the available results returns an empty `items` list while preserving the correct total. Invalid pagination is rejected with HTTP 422.

## Retrieve and update

`GET /api/v1/drafts/{saved_draft_id}` returns the current owner-safe representation.

`PATCH /api/v1/drafts/{saved_draft_id}` requires `expected_version` and at least one of:

- `title`
- `edited_text`
- `selected_image_id`

Only supplied fields change. Omitted fields retain their current values. Draft text cannot be null, blank, contain a NUL character, or exceed 12,000 characters. A stale `expected_version` returns `draft_version_conflict`, requiring the client to refresh before trying again. The repository performs the authoritative version check inside the write transaction, including when two updates race.

The existing `PUT` endpoint remains available for clients that send the complete editable state.

## Response data

Each saved draft response contains:

- Saved-draft, generated-post, current-version, and optional selected-image UUIDs.
- Private title, reviewed text, tone, length, saved status, optimistic version, and timestamps.
- Permitted source reference: article UUID, title, URL, and attribution.
- Non-secret generation reference: generation UUID, original post-version UUID, model identifier, prompt version, and creation time.
- If selected, safe image metadata: image UUID, alt text, approved MIME type, dimensions, AI-generated flag, and disclosure requirement.

Image bytes still use NFA-53's authenticated delivery endpoints. The content-library response never includes a storage key, filesystem path, unrestricted URL, integrity hash, or user-supplied filename.

## Status and error behaviour

| Condition | HTTP status | Safe code or behaviour |
| --- | ---: | --- |
| Created successfully | 201 | Owner-safe saved draft |
| Read, list, or update succeeds | 200 | Owner-safe record or collection |
| Authentication missing or expired | 401 | `authentication_required` |
| CSRF proof missing or invalid on a write | 403 | `csrf_validation_failed` |
| Resource missing or not owned | 404 | `private_resource_not_found` |
| Duplicate saved post | 409 | `draft_already_saved` |
| Idempotency key has another payload | 409 | `idempotency_key_conflict` |
| Optimistic version is stale | 409 | `draft_version_conflict` |
| UUID, body, or pagination is invalid | 422 | Standard safe validation response |
| Persistence is unavailable | 503 | `draft_persistence_unavailable` |

Errors do not reveal whether another user owns a record and do not include database details, source text, draft text, private image locations, or credentials.

## OpenAPI documentation

FastAPI publishes the collection and item operations in the local OpenAPI document and interactive API documentation:

- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Swagger UI: `http://localhost:8000/docs`

The operation descriptions document authentication, pagination limits, stable ordering, partial updates, and expected failure statuses.

## Verification

Run the focused API and service suite from the repository root:

```bash
apps/api/.venv/bin/pytest -q apps/api/tests/test_saved_drafts.py
```

The 9 tests cover authentication, owner-only listing, stable pagination, totals, safe image metadata, invalid parameters and UUIDs, partial updates, retained omitted fields, stale conflicts, cross-user masking, OpenAPI documentation, idempotency, duplicates, validation, and safe persistence failures.

The isolated PostgreSQL proof applies all migrations, inserts synthetic permitted data, saves and updates a draft, lists paginated owner-scoped results, verifies safe image metadata, rejects a stale write, inspects immutable versions, and rolls the schema back:

```bash
cd apps/api
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_saved_draft_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_saved_draft_integration.py
```

Never run the reset-enabled command against a development, shared, staging, or production database.

The NFA-68 local verification completed with:

- 9 focused saved-draft tests passed.
- 1 safety-gated PostgreSQL integration test passed.
- 431 backend tests passed, 14 safety-gated tests were skipped, and the optional live-model test was deselected.
- Branch-aware backend coverage was 79.50 percent, above the enforced 75 percent floor.
- Ruff linting and formatting checks passed.

## Limitations and next steps

- NFA-68 provides the backend content-library contract. The frontend library screen will consume it in a separate task.
- Deletion, restore, export, and bulk operations are not included.
- Offset pagination is appropriate for the current MVP. A reviewed cursor contract can replace it later if the library becomes large or highly concurrent.
- Saved drafts are private application content and are never published to LinkedIn automatically.
- Live CNN access remains blocked by ADR-001 until explicit authorisation and a Go decision exist.
