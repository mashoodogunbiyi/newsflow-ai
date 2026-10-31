# Secure generated-image validation and storage

## Purpose

NFA-51 converts an NFA-50 provider result into a validated private object and a PostgreSQL metadata record. Provider bytes are untrusted until this workflow finishes. The implementation does not make generated images public and does not return filesystem paths or object keys to callers.

## Data flow

```text
NFA-50 image result
  -> verify provider length and SHA-256 metadata
  -> inspect actual image content with Pillow
  -> verify format, integrity, size, pixels, and dimensions
  -> re-encode pixels without unnecessary metadata
  -> write to private storage under a random key
  -> verify ownership and generation relationships
  -> persist PostgreSQL metadata
  -> return safe metadata without a storage key
```

If PostgreSQL persistence fails after an object is written, the service deletes the new object. If cleanup itself fails, a content-free `generated_image_cleanup_failed` event is logged with `orphan_reconciliation_required`; the storage key is not logged.

## Accepted files and limits

The validator trusts decoded content rather than a filename or extension.

| Control | Accepted value |
| --- | --- |
| Formats | PNG, JPEG, and WebP |
| MIME types | `image/png`, `image/jpeg`, and `image/webp` |
| Dimensions | `1024x1024`, `1536x1024`, and `1024x1536` |
| Maximum stored input | 10 MiB by default |
| Maximum decoded pixels | 4,000,000 by default |
| Animation | Not accepted |
| Provider metadata | Declared MIME type, byte length, and SHA-256 must match when supplied |

The provider boundary can accept a larger bounded response, but NFA-51 applies the smaller storage limit before decoding. Pillow verifies integrity, and accepted pixels are re-encoded. EXIF, comments, and other source metadata are not copied into the stored output.

## Output safety policy

The normal initial state is `pending`. The object stays private and requires human review before publication or selection in saved content. A trusted safety workflow may supply `approved`; a `blocked` result is rejected before validation or storage. Existing database rules allow only an `approved` and available image to be selected in saved content.

This technical validation does not prove that an illustration is accurate, suitable, or safe to publish. Human review remains mandatory.

## Private local storage

`PrivateImageStorage` is the provider-neutral boundary. `LocalPrivateImageStorage` is the approved development and test adapter. It:

- creates a server-generated key such as `generated-images/8d9f1c2a....png`;
- never uses a user-provided filename;
- atomically replaces a temporary upload;
- applies directory mode `0700` and file mode `0600` where the operating system supports POSIX permissions;
- exposes no public URL operation;
- rejects path traversal; and
- keeps storage keys out of the safe service result and logs.

Docker mounts the named volume `image_storage_data` at `/app/.local/image-storage`. The volume persists across `docker compose down` and is deleted only by an explicit volume-removal operation. Do not run `docker compose down --volumes` unless deleting development database and image data is intended.

The local adapter is rejected in staging and production. Deployment requires a reviewed private object-storage adapter with private-by-default access, server-side credentials, encryption, ownership-aware retrieval, and equivalent cleanup behaviour.

## PostgreSQL metadata

Migration `20261031_0011` extends `generated_images` with:

- request, user, article, article snapshot, generated post, post version, and image-generation run associations;
- the private provider and storage key;
- content MIME type, byte size, dimensions, and SHA-256;
- model, prompt version, and safety-policy version;
- safety, validation, generation, and lifecycle states; and
- AI-generated and disclosure-required flags.

Composite foreign keys prove that the owner owns the generated post, the post uses the recorded article snapshot, and the snapshot belongs to the recorded article. The existing generation foreign key and trigger prove that the run belongs to the same post and has type `image`.

## Idempotency and consistency

The NFA-50 request UUID is unique in PostgreSQL. A retry is accepted only when the owner, article, post, generation run, optional source post version, and sanitised content hash all match the existing record. A conflicting reuse is rejected.

The repository uses a PostgreSQL transaction advisory lock for the request UUID. If two backend workers race, only one row is created. The losing workflow removes its newly written object and returns the existing record.

## Configuration

The committed `.env.example` contains safe defaults:

```dotenv
IMAGE_STORAGE_BACKEND=local
IMAGE_STORAGE_LOCAL_ROOT=.local/image-storage
IMAGE_STORAGE_MAX_BYTES=10485760
IMAGE_STORAGE_MAX_PIXELS=4000000
```

Docker overrides only the local root so it points at the named volume. No credential is required for local storage. Future object-storage credentials must be backend-only environment variables and must never be committed or exposed through a `NEXT_PUBLIC_` variable.

Apply the database migration after rebuilding the backend image for the new Pillow dependency:

```bash
docker compose up --build --detach
docker compose exec backend alembic upgrade head
```

## Retention and deletion

NFA-51 provides compensation deletion for failed writes. Full user-requested deletion, retention expiry, export, and orphan reconciliation scheduling belong to E7. Until that lifecycle is implemented, generated images remain private and must not be treated as automatically publishable assets.

## Tests

Run the focused checks from the repository root:

```bash
apps/api/.venv/bin/ruff check \
  apps/api/app/core/image_storage_config.py \
  apps/api/app/models/generated_image.py \
  apps/api/app/repositories/generated_images.py \
  apps/api/app/services/generated_image_storage.py \
  apps/api/app/services/image_storage.py \
  apps/api/app/services/image_validation.py \
  apps/api/tests/test_image_storage.py \
  apps/api/tests/test_image_validation.py
apps/api/.venv/bin/ruff format --check \
  apps/api/app/core/image_storage_config.py \
  apps/api/app/models/generated_image.py \
  apps/api/app/repositories/generated_images.py \
  apps/api/app/services/generated_image_storage.py \
  apps/api/app/services/image_storage.py \
  apps/api/app/services/image_validation.py \
  apps/api/tests/test_image_storage.py \
  apps/api/tests/test_image_validation.py
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_image_validation.py \
  apps/api/tests/test_image_storage.py
```

The tests use locally generated synthetic pixels. They make no live OpenAI or CNN request and use no real user data.
