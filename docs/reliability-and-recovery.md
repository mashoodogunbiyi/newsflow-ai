# NFA-79 - Reliability and Failure Recovery

## Outcome

NewsFlow AI now has a versioned reliability policy, bounded recovery coordination, request-correlated safe errors, dependency health checks, deterministic failure tests, and an operational recovery procedure. The controls preserve existing user content, fail closed when authority cannot be verified, and avoid uncontrolled paid provider calls.

Review date: 4 November 2026

Implementation status: Ready for review

Approval status: Pending Mashood Ogunbiyi's review

## Reliability principles

- Preserve an existing draft or image when a replacement operation fails.
- Do not report success until the required database or storage operation succeeds.
- Fail closed when authentication, ownership, source rights, or safety cannot be confirmed.
- Retry only failures that are both temporary and safe to repeat.
- Never automatically replay a paid image request when a timeout leaves the provider outcome uncertain.
- Use idempotency keys, request fingerprints, and database constraints to control duplicates.
- Keep database changes transactional and record storage cleanup as durable follow-up work.
- Return safe error categories and a request ID instead of internal exception details.
- Never log credentials, source content, draft text, prompts, private storage keys, or provider response bodies.

The executable policy is defined in `apps/api/app/core/reliability.py` as `reliability_v1`. Its values come from the same validated settings used by the application.

## Critical dependencies

| Dependency | Default timeout | Automatic retry limit | Failure behaviour | Health or recovery evidence |
|---|---:|---:|---|---|
| PostgreSQL | 5 seconds | 0 at the API boundary | Reject the operation, roll back the transaction, and preserve committed data | Startup connection check and `GET /ready` |
| OpenAI text generation | 30 seconds | 2 in the official SDK | Mark the attempt failed or interrupted and preserve source and edited content | Safe generation category, usage record, audit record, and request ID |
| OpenAI image generation | 120 seconds | 1 only for a clearly rejected rate limit | Preserve the original image and draft; do not replay an uncertain timeout | Image run, usage evidence, immutable parent image, and request ID |
| Article provider | Provider boundary plus sync lease | 2 | Mark the durable sync job failed or partial and retain the last successful checkpoint | Sync job state, protected ingestion health, metrics, and logs |
| Private image storage | Adapter-specific | 0 inline | Compensate an incomplete upload or leave durable cleanup work for reconciliation | Cleanup job totals and content-free recovery events |
| Backend API or browser network | Client-controlled | 0 automatic generation retries | Keep form inputs and edits, show a controlled error, and require a deliberate retry | Safe API envelope, `X-Request-ID`, and frontend generation state |

Timeouts and retry limits are bounded by Pydantic settings. A deployment may choose lower values within those bounds after testing. It must not add another uncoordinated retry layer at a proxy or worker because nested retries can multiply provider requests.

## Retry decisions

### Safe to retry within the configured budget

- An OpenAI text or article-provider temporary connection failure where no result was accepted.
- A provider rate limit when the provider clearly rejected the request.
- A temporary article-provider failure before a page was committed.
- A durable private-image deletion job after the configured delay.

### Do not retry automatically

- Invalid credentials, quota exhaustion, invalid input, rights denial, or safety denial.
- PostgreSQL constraint errors and invalid configuration.
- An OpenAI image timeout with an uncertain provider outcome.
- A request whose idempotency key was reused with different input.
- An operation that would bypass authentication, ownership, or source restrictions.

The user can make a deliberate retry after a controlled frontend failure. The backend still applies the current security, rights, safety, idempotency, concurrency, and usage checks.

## Failure behaviour

### OpenAI text failure

The service maps authentication, quota, rate-limit, timeout, connection, and invalid-response failures to controlled categories. It does not return provider details or prompt content. The generation workflow records failure evidence and does not create a successful saved draft from a failed response.

### OpenAI image failure

Known rate limits can be retried within the small configured budget. An application timeout cancels the local wait and is not automatically replayed because the provider might still have completed a paid request. Failed regeneration leaves the original image selected and available. Provider, storage, and usage failures cannot produce a false successful image version.

### Database unavailability or interrupted update

FastAPI startup fails if PostgreSQL cannot be reached. `GET /ready` returns a safe `503` if a bounded database check fails. Related writes use database transactions, so an exception rolls back the incomplete operation. Draft update tests confirm that validation and database failures leave the last committed text and version unchanged.

### Article-provider failure

Article synchronisation uses durable jobs, a lease, a last-successful checkpoint, and bounded exponential retry for temporary errors. Permanent or rights failures are not retried. A rejected page does not advance the checkpoint. A stale job can be recovered without allowing two active jobs for the same source.

### Browser or API network interruption

The generation interface keeps the selected article, preferences, edited text, and previous successful output in React state. It changes to a controlled error state and enables a deliberate retry. The active-request lock prevents accidental duplicate submission and stale responses cannot replace newer results.

### Private image upload and persistence

The storage workflow follows this order:

1. Validate and sanitise the provider bytes.
2. Write an unpredictable private object.
3. Save the owner, source, safety, and generation metadata in PostgreSQL.
4. If the database save fails, attempt a compensating object deletion.
5. If compensation also fails, emit `generated_image_cleanup_failed` with `orphan_reconciliation_required` and no private object key.

This prevents a database record from falsely pointing at an object that was not stored. The remaining double-failure case is recorded as a production release risk because an object-store inventory adapter is required for complete orphan discovery.

### Deletion and retention

Deleting a saved draft removes active access transactionally and creates cleanup jobs for unreferenced images. Failed object deletion is rescheduled instead of restoring user access or claiming cleanup succeeded. The bounded `ReliabilityRecoveryService` processes one batch of existing cleanup jobs and then performs eligible redaction. Its result contains counts only.

The recovery service accepts a batch limit from 1 to 500. A failed batch returns a safe recovery error, records `retry_required`, and does not log an object key. It does not delete active or still-referenced images.

## Health checks

| Check | Meaning | Public detail |
|---|---|---|
| `GET /health` | The FastAPI process can answer a request | `{"status":"ok"}` |
| `GET /ready` | Required configuration loaded and PostgreSQL answered a bounded query | `{"status":"ready","database":"connected","configuration":"valid"}` |
| Protected ingestion health | Recent article synchronisation and threshold state | Authenticated administrator only |

OpenAI and object storage are deliberately not called by public readiness checks. Calling a paid provider or exposing private infrastructure detail from a public probe would create cost, availability, and information-disclosure risks. Their status is inferred from controlled workflow outcomes, protected metrics, and recovery events.

Every HTTP response receives an unpredictable `X-Request-ID`. Expected dependency failures and unexpected API failures record the same identifier. A user can report that identifier without sending private content.

## Structured operational events

NFA-79 adds the allowlisted fields `component`, `operation`, and `recovery_status`. Reliability events use only bounded operational metadata:

| Event | Meaning | Expected response |
|---|---|---|
| `api_dependency_failure` | An expected server-side dependency failure returned a safe 5xx response | Correlate by request ID and inspect component health |
| `api_request_failed` | An unexpected server error was safely hidden | Investigate by request ID without asking for user content |
| `generated_image_cleanup_failed` | Upload persistence and compensating deletion both failed | Alert and reconcile the private object inventory |
| `storage_reconciliation_started` | One bounded cleanup batch began | Observe only |
| `storage_reconciliation_completed` | The batch completed with content-free counts | Confirm retried and redacted totals |
| `storage_reconciliation_failed` | The batch could not complete | Restore the dependency and retry the bounded batch |

Raw exception messages are not attached to unexpected API or reconciliation events. The JSON formatter also redacts common credential shapes, but redaction is a backup control rather than permission to log private content.

## Recovery procedures

### PostgreSQL is unavailable

1. Confirm `GET /health` is available and `GET /ready` returns `503`.
2. Use the response request ID to locate the safe dependency event.
3. Check PostgreSQL process health, credentials through the secret manager, network access, disk capacity, and migration status.
4. Do not bypass the database or write substitute local records.
5. Restore PostgreSQL and repeat `GET /ready`.
6. Confirm interrupted requests did not create partial records before asking a user to retry.

### OpenAI is timing out or rate limited

1. Check the safe error category, request ID, usage limits, and provider status outside the application.
2. Do not increase retry counts while an incident is active.
3. For an uncertain image timeout, wait and investigate before allowing a fresh paid request.
4. Confirm the original draft and image are still accessible.
5. Ask the user to retry deliberately only after the dependency is stable.

### Article ingestion is interrupted

1. Inspect the protected sync job and health records.
2. Confirm the last successful checkpoint was not advanced by a rejected page.
3. Allow the lease to expire or use the existing stale-job recovery path.
4. Rerun the authorised provider job. Never switch to scraping or a non-authorised source.

### Private storage cleanup fails

1. Confirm active draft access has already been removed and a cleanup job exists.
2. Restore private storage connectivity and permissions.
3. Run one bounded reconciliation batch through `ReliabilityRecoveryService.reconcile_private_storage` in the configured worker context.
4. Review only the completed, rescheduled, and redacted counts.
5. Repeat within operational limits until due jobs are cleared.
6. For `orphan_reconciliation_required`, use the approved production storage inventory process before removal. Do not guess a key or make the private bucket public.

### Browser network interruption

1. Keep the page open so current edits remain in memory.
2. Confirm the backend and network recover.
3. Use the displayed retry action once.
4. If the first request outcome is uncertain, reopen the library before generating again so an existing result can be reused.

## Automated evidence

| Scenario | Evidence |
|---|---|
| Versioned dependency policy and retry bounds | `tests/reliability/test_recovery_framework.py` |
| Safe PostgreSQL readiness failure and request correlation | `tests/reliability/test_recovery_framework.py` and `tests/test_api.py` |
| Safe unexpected API failure | `tests/reliability/test_recovery_framework.py` |
| Bounded cleanup reconciliation and safe failure logs | `tests/reliability/test_recovery_framework.py` |
| Text timeout, rate limit, authentication, quota, connection, and redaction | `tests/test_openai_service.py` |
| Image timeout, bounded rate-limit retry, duplicate request, provider failure, and response validation | `tests/test_openai_image_service.py` |
| Original image preservation after provider or storage failure | `tests/test_image_regeneration.py` |
| Storage failure, database compensation, and orphan event privacy | `tests/test_image_storage.py` |
| Interrupted draft update and database rollback | `tests/test_saved_drafts.py` |
| Partial deletion, cleanup retry, and retention ordering | `tests/test_content_deletion.py` |
| Article timeout, bounded retry, durable job, checkpoint, and database failure | `tests/test_article_sync.py` |
| Frontend timeout, network interruption, stale response, duplicate lock, and deliberate retry | `apps/web/__tests__/generation-state.test.tsx` |

All provider failures use mocks or synthetic exceptions. Routine tests do not use live CNN, OpenAI, production PostgreSQL, production user data, or production object storage.

## Verification results

Verified locally on 4 November 2026:

- The focused backend reliability and dependency-failure matrix passed 115 tests.
- The frontend timeout and network-recovery suite passed 9 tests.
- The complete deterministic backend suite passed 480 tests, skipped 16 safety-gated PostgreSQL tests, and deselected the optional live-model test.
- Branch-aware backend coverage measured 79.10 percent, above the enforced 75 percent floor.
- Ruff linting and formatting passed, the project secret scan passed, and `git diff --check` reported no whitespace errors.
- No live CNN, OpenAI, production database, production user data, or production object-storage service was used.

## Acceptance review

| Acceptance area | Status | Evidence |
|---|---|---|
| Critical dependencies and expected failures identified | Met | Versioned policy and dependency table |
| Timeouts, bounded retries, and rate limits reviewed | Met | Executable policy, validated settings, and provider tests |
| Text, image, database, storage, network, duplicate, and interruption failures tested | Met | Automated evidence matrix |
| Original content and database consistency preserved | Met | Regeneration, draft, storage, and deletion tests |
| Storage reconciliation behaviour implemented | Met with limitation | Bounded recovery coordinator and durable cleanup jobs |
| Structured safe logging and operational health checks | Met | Correlated API errors, recovery events, `/health`, and `/ready` |
| Recovery procedures documented | Met | Runbooks above |
| Unresolved risks recorded | Met | Limitations below |

## Known limitations and unresolved risks

- The local private-storage adapter is development-only. Production must supply an approved private object-storage adapter and inventory process.
- The synthetic article provider performs no network request. A future authorised live provider must define and test its HTTP connection, read, and total timeouts before activation.
- A database-save plus compensation-delete double failure can leave an unreferenced object. The content-free event is implemented, but complete orphan discovery needs the production storage inventory API and alert routing.
- Cleanup reconciliation is implemented as a reusable bounded service. A production deployment still needs an authenticated worker or scheduler to invoke it and alert on repeated failure.
- Public readiness checks PostgreSQL and configuration only. It intentionally does not make live OpenAI, article-provider, or object-storage requests.
- In-memory short-window rate limits are process-local. Multi-instance production needs a shared gateway or distributed limiter in addition to PostgreSQL usage controls.
- Local automated tests do not prove cloud network partitions, database failover, backup restoration, object-store durability, or multi-region recovery. These require staging exercises and an approved deployment platform.
- Browser network behaviour is deterministic in component and Playwright tests, but mobile network switching and long offline periods still need staging review.
- Live CNN integration remains blocked by ADR-001. Recovery must never bypass that rights decision.

These items are release controls, not reasons to weaken the current fail-closed behaviour.

