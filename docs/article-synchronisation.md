# NFA-33 - Article Synchronisation

## Purpose

NFA-33 keeps the NewsFlow AI article catalogue up to date through one reusable workflow for scheduled and administrator-triggered synchronisation.

The workflow currently uses only the synthetic fixture provider. Live CNN synchronisation remains disabled because NFA-5 and ADR-001 do not authorise it.

## Plain-language explanation

Synchronisation is like checking an authorised source for new or changed article information and updating NewsFlow AI's filing cabinet.

For every run, NewsFlow AI:

1. Confirms that the source profile is enabled and approved.
2. Creates a durable job record.
3. Retrieves a validated provider page.
4. Uses the existing normalisation and validation boundary.
5. Uses the existing identity and deduplication service.
6. Stores each article, provenance event, and rights record in one article transaction.
7. Records created, updated, skipped, rejected, and retrieved counts.
8. Advances the incremental checkpoint only after complete success.

Manual and scheduled triggers call this same service, so neither path can bypass the source, validation, deduplication, provenance, or rights rules.

## Main components

| Component | Responsibility |
|---|---|
| `ArticleSyncService` | Coordinates provider pages, retries, ingestion, statistics, checkpoints, and safe failures |
| `SqlAlchemyArticleSyncRepository` | Stores jobs, schedule reservations, leases, checkpoints, and administrator checks |
| `ArticleSyncScheduler` | Runs a due job only after winning a durable PostgreSQL schedule reservation |
| `app.jobs.article_sync_job` | One-shot entry point for cron, a container job, or a managed scheduler |
| `/api/v1/admin/articles/sync` | Starts a protected manual job and returns HTTP 202 |
| `/api/v1/admin/articles/sync/{job_id}` | Returns safe job status and statistics to an administrator |

## Database model

Migration `20261029_0004` adds:

- `users.role`, restricted to `user` or `admin`.
- `article_sync_jobs`, which records trigger, status, requester, lease, checkpoints, statistics, safe errors, and timestamps.
- `article_sync_checkpoints`, which records the last successful publication position and next scheduled time for each provider.

The partial unique index `uq_article_sync_jobs_active_provider` permits only one `pending` or `running` job per provider. This works across processes and application instances.

## Job lifecycle

Supported triggers:

- `manual`
- `scheduled`

Supported statuses:

- `pending` - created but not yet claimed by a worker.
- `running` - claimed with a renewable lease.
- `completed` - all retrieved records were processed successfully.
- `partially_completed` - some work succeeded, but at least one record or later page failed.
- `failed` - no article work completed successfully.
- `interrupted` - a pending or running lease expired after a worker stopped.

Pending and running jobs always have an expiry lease. Before creating a job, the service marks expired active jobs as interrupted. The next job starts from the last fully successful checkpoint, so an interrupted job cannot make later retrieval silently skip unfinished records.

## Incremental retrieval and checkpoints

The fixture provider declares incremental retrieval support. The service supplies its saved `last_successful_publication_at` value through `ArticleQuery.published_after`.

The checkpoint advances only when the job status is `completed`. It does not advance after a failed or partially completed job. Repeating earlier records is safe because NFA-31 deduplication skips unchanged articles, while NFA-32 still preserves the required provenance for accepted ingestion attempts.

Providers that do not declare incremental retrieval receive no checkpoint filter and must use their documented, rate-compliant alternative.

## Retry and failure policy

Temporary provider errors marked as retryable receive bounded exponential backoff. Defaults are two retries after the original request, with delays of 1 and 2 seconds.

Permanent authorisation, authentication, invalid-data, and cursor failures are not repeatedly retried. Provider responses, credentials, article text, and confidential agreement details are not placed in job errors or logs.

Each article is stored through the existing atomic ingestion transaction. A later failure cannot leave a partial article that appears authorised without its required snapshot, provenance, and rights metadata.

## Manual synchronisation security

The POST endpoint requires:

- A valid HTTP-only session.
- Matching CSRF proof.
- An active account with the `admin` role.
- An enabled and approved source profile.
- No conflicting active provider job.
- The manual-trigger rate limit.

Ordinary users receive HTTP 403. A conflicting job receives HTTP 409. A disabled source fails before provider access. The endpoint creates the job and returns its identifier without holding the HTTP response open for the complete provider workflow.

For local development only, promote a test account after it has registered:

```bash
docker compose exec database sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "UPDATE users SET role = '\''admin'\'' WHERE email = '\''YOUR_EMAIL'\'';"'
```

Replace `YOUR_EMAIL` with your registered local email. Production administrator assignment must use a reviewed identity and access-management process rather than direct SQL.

## Configuration

The safe example contains:

```dotenv
ARTICLE_SYNC_INTERVAL_SECONDS=14400
ARTICLE_SYNC_PAGE_SIZE=50
ARTICLE_SYNC_MAX_RETRIES=2
ARTICLE_SYNC_RETRY_BASE_SECONDS=1
ARTICLE_SYNC_LEASE_SECONDS=300
MANUAL_SYNC_RATE_LIMIT_ATTEMPTS=2
MANUAL_SYNC_RATE_LIMIT_WINDOW_SECONDS=60
```

The default interval is four hours. Actual live-provider intervals must be reviewed against its agreement and rate limits before activation.

## Run scheduled synchronisation

Apply migrations first:

```bash
docker compose exec backend alembic upgrade head
```

Run the one-shot scheduler manually:

```bash
docker compose exec backend python -m app.jobs.article_sync_job
```

The command checks the durable schedule before doing work. Calling it again before the configured interval returns without starting another job. In deployment, invoke this command from one or more cron, container-scheduler, or managed-scheduler workers. PostgreSQL decides which invocation wins, so the design does not depend on an unreliable scheduler running inside every FastAPI web process.

## Run and inspect a manual job

After logging in as a local administrator, use the interactive API documentation at `http://localhost:8000/docs`:

- `POST /api/v1/admin/articles/sync`
- `GET /api/v1/admin/articles/sync/{job_id}`

The POST response contains the initial job identifier and status. Use the GET operation to read the durable final status and statistics.

## Automated evidence

Run the normal NFA-33 tests from `apps/api`:

```bash
pytest tests/test_article_sync.py tests/test_admin_article_sync.py
```

They cover scheduled and manual triggers, administrator enforcement, source disablement, pagination, incremental retrieval, accurate counts, retries, permanent failures, partial completion, rate limiting, duplicate-job prevention, stale-job recovery, and checkpoint safety.

The opt-in PostgreSQL proof uses an explicitly disposable database:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_article_sync_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_article_sync_integration.py
```

Never point this test at the normal development database or a shared database.

## Troubleshooting

### Source disabled

Confirm `NEWS_SOURCE_MODE=fixture` for local development and ensure the `fixture-v1` source profile exists, is enabled, and has an approval timestamp. Do not enable a live profile to work around this check.

### Job already active

Read the existing job status. A healthy running job should be allowed to finish. A worker that disappears will lose its lease and be marked interrupted on the next trigger.

### Job partially completed

Review the safe error code and rejected count. The checkpoint was not advanced. Correct the provider contract or identity issue, then run again; previously stored records will be deduplicated.

### Provider unavailable

The service performs only the configured bounded retries. If the provider remains unavailable, the job fails safely and keeps the earlier checkpoint.

### Live CNN request expected

No live CNN request is available. Obtain written authorisation, update NFA-5, record a Go decision replacing ADR-001, implement and test the approved adapter, and review its rate and retention rules first.

## Acceptance status

- Reusable synchronisation pipeline - complete.
- Scheduled one-shot mechanism with durable interval reservation - complete.
- Protected asynchronous manual trigger - complete.
- PostgreSQL jobs, leases, checkpoints, statistics, and constraints - complete.
- Incremental fixture retrieval and safe checkpoint rules - complete.
- Bounded temporary-failure retry and permanent-failure handling - complete.
- Duplicate and conflicting job prevention - complete.
- Restart interruption recovery - complete.
- Automated unit, API, migration, and PostgreSQL tests - complete.
- Live CNN integration - correctly disabled until separate authorisation and Go approval exist.

## Current limitations

FastAPI background tasks are suitable for the current single-machine development workflow, but production should run jobs through a durable queue or dedicated worker. The PostgreSQL job, lease, and checkpoint model is already designed to support that replacement. No live provider, provider credential, CNN endpoint, or OpenAI request is introduced by NFA-33.
