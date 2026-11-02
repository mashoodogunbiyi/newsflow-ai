# NFA-72 - Content Deletion and Retention

## Decision

NewsFlow AI uses a two-stage deletion lifecycle because PostgreSQL and private
object storage cannot be changed in one atomic transaction.

1. A confirmed owner request immediately marks the saved draft deleted. Normal
   list, detail, update, history, export, and image-delivery queries can no
   longer access it.
2. Unreferenced private image objects are removed immediately when possible.
   Failed storage operations are recorded with a safe error code and retried by
   the retention worker.
3. After the configured 30-day cleanup period, the worker deletes the saved
   draft and history ledger, then redacts generated text, prompts, titles,
   idempotency evidence, and image alternative text from required operational
   records.
4. Minimal content-free deletion evidence is retained for 365 days and then
   removed by the same worker.

This staging period is an internal cleanup control, not a user-visible trash
folder. The application provides no self-service recovery after confirmation.

## API and ownership

`DELETE /api/v1/drafts/{saved_draft_id}` requires:

- an authenticated server-managed session;
- a matching CSRF token;
- a valid UUID; and
- ownership of an active saved draft.

The API derives the owner from the session. A missing draft, an already deleted
draft, and another user's draft all return the same private `404` response. A
successful request returns `204 No Content` with `Cache-Control: no-store`.

The Next.js interface calls the endpoint through
`/api/drafts/{draftId}`. That gateway forwards only the NewsFlow session and
CSRF cookies plus the CSRF header. It does not forward analytics cookies or
expose backend credentials.

## Image-reference safety

Before an image is queued for deletion, the transaction checks current image
selections and immutable history belonging to every other active saved draft.
An image still referenced by active content is preserved. An eligible image is
marked deleted before its private object is removed, so normal delivery stops
even if object storage is temporarily unavailable.

Each cleanup job has one generated-image identifier, a private storage key,
attempt count, next-attempt time, safe error code, and completion time. The
local delete operation is idempotent. A failed attempt remains retryable and
does not restore access to the deleted draft.

## Retention worker

Run one bounded cleanup cycle from `apps/api` after applying migrations:

```bash
python -m app.retention
```

The worker:

- claims due object-cleanup jobs with row locks and skip-locked concurrency;
- gives each claim a 15-minute lease so work interrupted by a crashed process
  becomes eligible for another worker;
- retries failed private-object deletions;
- waits for related cleanup jobs before redacting expired draft content;
- removes immutable saved-draft history;
- deletes the saved-content record and redacts generated text and prompt content
  in required operational tombstones; and
- expires completed content-free deletion audits.

Production deployment must schedule this command at least daily and alert on
repeated retries. Running more than one worker is safe because claims use
PostgreSQL row locks.

## Configuration

| Environment variable                    | Default | Purpose                                      |
| --------------------------------------- | ------- | -------------------------------------------- |
| `DRAFT_DELETION_RETENTION_DAYS`         | `30`    | Delay before retained draft data is redacted |
| `DELETION_AUDIT_RETENTION_DAYS`         | `365`   | Retention for content-free deletion evidence |
| `IMAGE_CLEANUP_RETRY_SECONDS`           | `300`   | Delay before a failed object cleanup retries |

Real credentials remain in the ignored `.env` file. These settings contain no
secrets and their safe examples are committed in `.env.example`.

## Data minimisation and backups

- Active saved source metadata is retained only while needed for the user's
  library and the approved source-rights record.
- Deletion audits store a SHA-256 draft identifier, lifecycle timestamps,
  owner identifier, and status. They contain no draft text, title, source
  content, prompt, storage key, or provider credential.
- Object-cleanup records are operational records and are not returned through
  the public API.
- PostgreSQL and object-storage backups cannot be changed transactionally by a
  user request. Production backups must be encrypted, access-controlled, kept
  outside the active application path, and expire through the deployment's
  documented backup schedule. Restores must reapply deletion tombstones before
  making recovered data available.
- Local Docker volumes are development persistence, not a production backup or
  recovery service.

## Failure behaviour and limitations

- A database failure before commit returns `503` and makes no successful
  deletion claim.
- An object-storage failure after commit returns successful deletion because
  active access has already ended; the safe retry record completes the physical
  cleanup later.
- A failed object cleanup prevents final redaction for its generated post until
  the object is removed, avoiding a false completed state.
- NewsFlow AI does not yet include a production object-store adapter, backup
  orchestration, legal-hold workflow, or administrator recovery interface.
- Direct LinkedIn publishing is not implemented, so deletion does not affect
  content a user manually copied or published outside NewsFlow AI.
- Live CNN access remains blocked. This lifecycle applies to synthetic or
  otherwise authorised content only.

## Automated evidence

Backend tests cover successful deletion, unauthenticated access, cross-user
masking, immediate image cleanup, retry recording, and retention-worker
completion. Frontend tests cover confirmation, cancellation, CSRF forwarding,
controlled errors, and successful return to the library. Migration tests apply,
roll back, and rebuild the deletion tables and constraints in disposable
PostgreSQL.

Run the focused checks:

```bash
cd apps/api
pytest tests/test_content_deletion.py

cd ../web
npm test -- --run __tests__/draft-deletion.test.tsx __tests__/draft-deletion-proxy.test.ts
```
