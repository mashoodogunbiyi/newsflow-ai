# Secure generated-image delivery

## Purpose

NFA-53 allows an authenticated NewsFlow AI user to retrieve metadata, preview, and download an image they own. It builds on NFA-51 private storage and the NFA-25 owner-authorisation pattern. The API never returns a filesystem path, storage key, storage credential, integrity digest, or unrestricted public URL.

## Selected delivery architecture

NewsFlow AI currently uses backend delivery:

```text
Authenticated browser request
  -> FastAPI resolves the server-managed session
  -> PostgreSQL owner-scoped image lookup
  -> private storage read using the database key
  -> stored length and SHA-256 integrity check
  -> FastAPI returns approved image bytes
```

This is suitable for the bounded development images currently supported by the application. It keeps authorisation centralised and works with the approved local private-storage adapter.

The application does not create signed URLs in this architecture. Therefore, no public or temporary object link can expire or be reused. Session expiration is enforced by the existing authentication dependency on every request. A future private object-storage adapter may use signed URLs only after the backend verifies ownership. Such URLs must identify one object, expire after a short configured period, disclose no storage credential, use private cache rules, and be covered by expiration tests.

## API contract

All endpoints require the HTTP-only `newsflow_session` cookie. A missing, expired, or revoked session returns `401`. These read-only endpoints do not require a CSRF token because they do not change server state.

### Read image metadata

```http
GET /api/images/{image_id}
```

Example response:

```json
{
  "image_id": "53000000-0000-4000-8000-000000000003",
  "generation_id": "53000000-0000-4000-8000-000000000009",
  "generated_post_id": "53000000-0000-4000-8000-000000000008",
  "article_id": "53000000-0000-4000-8000-000000000006",
  "parent_image_id": "53000000-0000-4000-8000-000000000010",
  "regeneration_sequence": 2,
  "mime_type": "image/png",
  "width": 1536,
  "height": 1024,
  "file_size_bytes": 3145728,
  "model_identifier": "configured-image-model",
  "prompt_version": "image_prompt_v1",
  "safety_policy_version": "image_safety_v1",
  "safety_status": "approved",
  "validation_status": "passed",
  "generation_status": "completed",
  "is_ai_generated": true,
  "ai_disclosure_required": true,
  "created_at": "2026-10-31T20:00:00Z"
}
```

The response preserves AI designation, provenance identifiers, safety state, validation state, model identifier, prompt version, and version relationship. It excludes owner identity, storage provider, storage key, hash, and internal article-snapshot identifiers.

### Preview image content

```http
GET /api/images/{image_id}/content
```

The response body contains the approved PNG, JPEG, or WebP bytes. `Content-Type` comes from validated stored metadata. `Content-Disposition` is `inline` with a server-generated filename so a browser can preview the image without accepting an arbitrary filename.

### Download image content

```http
GET /api/images/{image_id}/download
```

The response contains the same integrity-checked bytes with an attachment header such as:

```http
Content-Disposition: attachment; filename="newsflow-ai-image-53000000-0000-4000-8000-000000000003.png"
```

The filename uses only the validated image UUID and MIME-derived extension. A user-supplied filename is never accepted.

## Authorisation and private failure behaviour

The API uses the authenticated session's user UUID as the owner identifier. It never trusts an owner supplied in a path, query, or request body. The repository query requires all of the following:

- the requested image UUID matches;
- the database `user_id` matches the authenticated user;
- the image is not deleted; and
- the image status is `available`.

A missing image and another user's image both return the same `404 private_resource_not_found` response. This prevents a caller from using the API to discover another user's image identifiers.

## Private storage and path safety

The client supplies only an image UUID. After authorisation, the service reads the server-controlled storage key from PostgreSQL. The local adapter resolves that key below its configured private root and rejects traversal outside that root. Storage keys and underlying exception paths are not included in HTTP responses or operational events.

Before delivery, the service compares both the byte length and SHA-256 digest with the immutable metadata recorded by NFA-51. Missing, unreadable, or modified objects return a controlled `503 image_delivery_unavailable` response. A content-free operational event records the provider request UUID and safe error category for investigation.

## Content and caching headers

Metadata, preview, and download responses use:

```http
Cache-Control: private, no-store, max-age=0
Pragma: no-cache
Vary: Cookie
X-Content-Type-Options: nosniff
```

The binary responses also include the validated `Content-Type`, calculated `Content-Length`, and safe `Content-Disposition`. These rules prevent shared caching and content-type guessing. The application currently permits only `image/png`, `image/jpeg`, and `image/webp`.

## Error contract

| Status | Code | Meaning |
| --- | --- | --- |
| `401` | `authentication_required` | The session is missing, expired, revoked, or invalid. |
| `404` | `private_resource_not_found` | The image is missing, deleted, unavailable, or owned by someone else. |
| `422` | `validation_error` | The path value is not a valid image UUID. |
| `503` | `image_delivery_unavailable` | Database access, private storage, or integrity verification is unavailable. |

Errors never reveal whether a different user owns the identifier, the private storage root, object key, credential, or traceback.

## Frontend integration notes

The E6 and E7 frontend should:

- call these endpoints with browser credentials included;
- use the metadata endpoint to display the AI-generated label and review state;
- use the content endpoint as the protected preview source;
- use the download endpoint for explicit user downloads;
- handle `401` by returning the user to login;
- treat `404` as unavailable without guessing ownership; and
- show a retryable safe message for `503`.

The frontend must not copy image bytes into browser storage, create its own permanent public URL, remove the AI-generated designation, or assume that preview means approval for publication.

## Tests

Run the focused checks from the repository root:

```bash
apps/api/.venv/bin/ruff check \
  apps/api/app/api/routes/image_delivery.py \
  apps/api/app/models/image_delivery.py \
  apps/api/app/services/image_delivery.py \
  apps/api/app/services/image_storage.py \
  apps/api/tests/test_image_delivery.py
apps/api/.venv/bin/ruff format --check \
  apps/api/app/api/routes/image_delivery.py \
  apps/api/app/models/image_delivery.py \
  apps/api/app/services/image_delivery.py \
  apps/api/app/services/image_storage.py \
  apps/api/tests/test_image_delivery.py
apps/api/.venv/bin/pytest -q apps/api/tests/test_image_delivery.py
```

The tests cover authenticated metadata, preview, download, owner isolation, missing records, missing objects, modified content, path traversal, approved MIME types, private caching, safe filenames, AI metadata, and OpenAPI documentation. They use synthetic bytes and make no live CNN or OpenAI request.

## Current limitations

- The local private-storage adapter is permitted only in development and test.
- A reviewed production object-storage adapter is still required before deployment.
- Byte delivery currently reads the bounded image into backend memory before creating the response.
- HTTP range requests and content-distribution-network integration are not implemented.
- Signed URLs are deliberately not issued by the selected backend-delivery architecture.
- Human review and publication approval remain separate workflows.
