# Secure image regeneration workflow

## Purpose

NFA-52 allows an authenticated user to request a new AI illustration from an existing private image. A regeneration is a new generation attempt and a new stored object. It never overwrites the selected image.

The workflow reuses the approved NFA-48 prompt composer, NFA-49 sensitive-news policy, NFA-50 OpenAI image boundary, and NFA-51 validation and private-storage services.

## API contract

```http
POST /api/images/{image_id}/regenerate
Cookie: newsflow_session=<HTTP-only session cookie>
X-CSRF-Token: <matching CSRF token>
Idempotency-Key: nfa52-example-001
Content-Type: application/json
```

`Idempotency-Key` is optional, must contain 8 to 128 approved characters, and should be supplied by the frontend for every submitted form. Reusing the same key with the same request returns the already completed image version without another provider call. Reusing it with different preferences returns `409`.

Example request:

```json
{
  "style": "minimalist_illustration",
  "aspect_ratio": "landscape",
  "composition": "focal_point_left"
}
```

Supported values are deliberately bounded:

| Field | Values |
| --- | --- |
| `style` | `editorial_illustration`, `minimalist_illustration`, `abstract_technology`, `professional_infographic_style` |
| `aspect_ratio` | `landscape`, `square`, `portrait` |
| `composition` | `balanced`, `focal_point_left`, `focal_point_right` |

Extra fields and unsupported values return `422`. The API does not accept free-form instructions, safety overrides, photorealism controls, public filenames, storage locations, model names, or provider credentials.

Example `201` response:

```json
{
  "image_id": "52000000-0000-4000-8000-000000000010",
  "parent_image_id": "52000000-0000-4000-8000-000000000008",
  "generation_id": "52000000-0000-4000-8000-000000000011",
  "generated_post_id": "52000000-0000-4000-8000-000000000005",
  "regeneration_sequence": 1,
  "status": "completed",
  "safety_status": "pending",
  "is_ai_generated": true,
  "review_required": true,
  "created_at": "2026-10-31T18:00:00Z"
}
```

Responses use `Cache-Control: private, no-store`. They never contain image bytes, prompts, provider URLs, private storage keys, article content, credentials, or another user's identifiers.

## Workflow

```text
authenticated POST and CSRF proof
  -> apply per-user burst limit
  -> load the selected image through an owner-scoped query
  -> load its private LinkedIn draft and current article snapshot
  -> recheck current AI-processing and derivative-output rights
  -> compose a new versioned prompt from controlled preferences
  -> reapply the sensitive-news policy
  -> check persistent idempotency and shared usage limits
  -> call the backend-only OpenAI image service
  -> create a new image generation run
  -> validate and sanitise returned image bytes
  -> store a new private object
  -> persist the child image and parent relationship
  -> record usage and return safe metadata
```

The original image is read but never updated. Provider or storage failure therefore leaves the original available.

## Ownership and privacy

The route requires the server-managed session cookie and matching CSRF header. The selected image query includes the authenticated user ID. A missing image and an image owned by someone else both return the same `404` response, so the endpoint does not disclose whether another user's private image exists.

The linked draft is loaded with the same owner ID. The database also verifies that the child image, post, article snapshot, generation run, and optional source post version all belong to one consistent context.

## Rights and safety revalidation

Regeneration is a new derivative operation. It does not inherit a permanent permission from the first image. Immediately before provider access, the service checks the current article rights version for `use_for_ai_generation`.

The NFA-49 policy then reclassifies the approved article and draft context. Only `allowed` and `allowed_with_restrictions` decisions can reach OpenAI. Uncertain context, missing required moderation controls, documentary-fabrication requests, and unsafe person depictions remain blocked. The output is always designated as AI-generated, stored with safety status `pending`, and marked for human review.

## Image versions

Migration `20261031_0012` adds:

- `parent_image_id`, a same-draft foreign key to the exact image selected for regeneration;
- `regeneration_sequence`, a draft-scoped integer allocated under a PostgreSQL advisory transaction lock;
- a unique constraint for each draft and sequence;
- parent-not-self and non-negative-sequence checks; and
- an index for later image-history retrieval.

An initial image has no parent. Every successful regeneration names its exact parent and receives the next sequence for the draft. This supports a version chain without duplicating image bytes in PostgreSQL. Full history and library presentation remain E7 work.

## Limits and duplicate protection

The endpoint reuses the existing per-user burst limiter. The service also reserves a shared PostgreSQL usage attempt, which enforces daily and concurrent limits across backend processes.

Persistent idempotency uses the image generation run for the same generated post. The database stores only a content-free request fingerprint, not the prompt or article text. Active identical submissions are stopped by the shared usage reservation. Completed submissions with the same client key return the existing private child image.

When no idempotency key is supplied, a later matching request is treated as an intentional request for another version. The frontend should therefore generate and retain one key for each form submission and reuse it only when retrying that submission.

## Failure responses

| Status | Meaning |
| --- | --- |
| `401` | No valid authenticated session |
| `403` | CSRF, current rights, or image safety denied the operation |
| `404` | The private image or its owned generation context was not found |
| `409` | Idempotency conflict or an identical request is already active |
| `422` | Unsupported preferences or invalid associated prompt context |
| `429` | Burst, daily, or concurrent generation limit exceeded |
| `502` | Provider output or image validation failed |
| `503` | Provider configuration, database, usage tracking, or private storage unavailable |
| `504` | OpenAI image request timed out |

Provider errors are converted to stable, content-free messages. No raw provider response, prompt, filesystem path, storage key, SQL detail, or secret is returned.

If provider generation fails, no generation run or image is reported as successful. If a provider result exists but validation or storage fails, the generation run is changed to `failed`, the safe error code is recorded, no successful image row is created, and NFA-51 removes any newly uploaded object when database persistence fails.

## Database update

Apply the migration after updating the branch:

```bash
docker compose up --build --detach
docker compose exec backend alembic upgrade head
```

Do not use `docker compose down --volumes` unless deleting the development database and stored image files is intentional.

## Automated verification

Run the focused checks from the repository root:

```bash
apps/api/.venv/bin/ruff check \
  apps/api/app/api/routes/image_regeneration.py \
  apps/api/app/models/image_regeneration.py \
  apps/api/app/repositories/image_regeneration.py \
  apps/api/app/services/image_regeneration.py \
  apps/api/tests/test_image_regeneration.py
apps/api/.venv/bin/ruff format --check \
  apps/api/app/api/routes/image_regeneration.py \
  apps/api/app/models/image_regeneration.py \
  apps/api/app/repositories/image_regeneration.py \
  apps/api/app/services/image_regeneration.py \
  apps/api/tests/test_image_regeneration.py
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_image_regeneration.py \
  apps/api/tests/test_image_storage.py \
  apps/api/tests/test_image_validation.py \
  apps/api/tests/test_openai_image_service.py \
  apps/api/tests/test_image_prompt.py \
  apps/api/tests/test_image_safety.py
```

The tests use synthetic article data, mocked OpenAI results, and private in-memory records. They cover success, original preservation, authentication, owner isolation, rights denial, safety denial, invalid preferences, provider failure, storage failure, version relationships, usage limits, duplicate submission, and the public API response. They do not contact CNN or OpenAI and do not spend provider credits.

## Limitations

NFA-52 implements the backend regeneration operation and version metadata. It does not add:

- the frontend regenerate button or preference controls;
- private image download or display endpoints;
- full visual image history and version selection;
- user deletion, retention expiry, or orphan reconciliation scheduling;
- deployment object storage; or
- automatic publishing.

Those behaviours require later reviewed tasks. Live CNN integration remains blocked until an authorised access method and a Go decision exist.
