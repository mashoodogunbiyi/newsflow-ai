# NewsFlow AI API

This directory contains NewsFlow AI's Python FastAPI backend. NFA-13 to NFA-17 establish the application, PostgreSQL, configuration, Docker, and quality foundations. NFA-21 adds SQLAlchemy, Alembic migrations, and synthetic seed data. NFA-22 to NFA-26 add the secure account lifecycle, object-level authorisation, regression coverage, and automated pull-request checks. NFA-28 to NFA-32 add the fixture-first provider boundary, validation, identity, provenance, and rights controls. NFA-33 adds durable article synchronisation. NFA-34 adds the authenticated article catalogue REST API. NFA-35 adds safe structured ingestion logs, operational metrics, protected status endpoints, and configurable health indicators. NFA-36 adds reusable synthetic fixtures and a complete isolated provider-to-PostgreSQL-to-REST pipeline test. NFA-38 adds a secure, reusable, and mocked OpenAI Responses API service for future E4 generation workflows.

## Requirements

- Python 3.10 or newer. Python 3.12 is recommended and recorded in `.python-version`.
- PostgreSQL 16 or another currently supported PostgreSQL release running locally.
- A terminal opened in `apps/api`.

The current FastAPI release requires Python 3.10 or newer. Do not use the macOS system Python 3.9 environment for this application.

## Local setup

From the repository root:

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If your supported Python executable has a different name, replace `python3.12` with that executable in the virtual-environment command.

## Configure the application

Create a local PostgreSQL role and database using your preferred local PostgreSQL installation. The development database name used by this project is `newsflow`. The approved Epic E2 tables, relationships, constraints, indexes, ownership rules, and ERD are documented in [NFA-20](../../docs/jira/NFA-20.md). NFA-21 implements that baseline in Alembic migration `20261025_0001`.

From the repository root, create your ignored local configuration file:

```bash
cp .env.example .env
```

Edit only `.env` and replace the placeholders with your local values:

```dotenv
APP_ENV=development
LOG_LEVEL=INFO
LOG_FORMAT=json
NEWS_SOURCE_MODE=fixture
FRONTEND_ORIGIN=http://localhost:3000
DATABASE_URL=postgresql://your_local_user:your_local_password@localhost:5432/newsflow
DATABASE_CONNECT_TIMEOUT_SECONDS=5
REGISTRATION_RATE_LIMIT_ATTEMPTS=5
REGISTRATION_RATE_LIMIT_WINDOW_SECONDS=60
LOGIN_RATE_LIMIT_ATTEMPTS=5
LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
SESSION_LIFETIME_MINUTES=60
ARTICLE_SYNC_INTERVAL_SECONDS=14400
ARTICLE_SYNC_PAGE_SIZE=50
ARTICLE_SYNC_MAX_RETRIES=2
ARTICLE_SYNC_RETRY_BASE_SECONDS=1
ARTICLE_SYNC_LEASE_SECONDS=300
MANUAL_SYNC_RATE_LIMIT_ATTEMPTS=2
MANUAL_SYNC_RATE_LIMIT_WINDOW_SECONDS=60
INGESTION_METRICS_ENABLED=true
INGESTION_METRICS_WINDOW_HOURS=24
INGESTION_FAILURE_THRESHOLD=3
INGESTION_SUCCESS_STALE_SECONDS=21600
INGESTION_LONG_RUNNING_SECONDS=600
INGESTION_REJECTION_RATE_PERCENT=25
OPENAI_API_KEY=your_real_openai_api_key
OPENAI_MODEL=your_approved_openai_model
OPENAI_REQUEST_TIMEOUT=30
OPENAI_MAX_OUTPUT_TOKENS=800
OPENAI_MAX_RETRIES=2
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`DATABASE_URL` is required when the API starts. `OPENAI_API_KEY` and `OPENAI_MODEL` are loaded and validated by the backend but are required only when an OpenAI-powered feature runs. This keeps the non-AI API usable without provider credentials. Empty values and the committed example placeholders produce clear errors without printing secret values.

Do not add real credentials to `.env.example`, source code, browser code, documentation, Jira, screenshots, commits, or pull requests. The repository `.gitignore` excludes `.env` files while retaining the safe `.env.example` template. The OpenAI API key is server-side only and must never use a `NEXT_PUBLIC_` name because Next.js exposes variables with that prefix to browser code. This follows [OpenAI's API authentication guidance](https://developers.openai.com/api/reference/overview), which says API keys must be loaded from an environment variable or key management service on the server.

### Configuration reference

| Variable | Required | Sensitive | Purpose |
|---|---|---|---|
| `APP_ENV` | No | No | Selects `development`, `test`, `staging`, or `production`; defaults to `development`. |
| `LOG_LEVEL` | No | No | Minimum application level: `DEBUG`, `INFO`, `WARNING`, or `ERROR`; defaults to `INFO`. |
| `LOG_FORMAT` | No | No | Structured `json` or readable structured `console`; defaults to `json`. |
| `NEWS_SOURCE_MODE` | No | No | Defaults to `disabled`; local development explicitly selects the approved `fixture` provider. |
| `FRONTEND_ORIGIN` | No | No | Exact browser origin allowed to call the API with cookies; defaults to `http://localhost:3000`. |
| `DATABASE_URL` | Yes at API startup | Yes | PostgreSQL connection string containing the database credentials. |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` | No | No | Database connection timeout from 1 to 30 seconds; defaults to 5. |
| `REGISTRATION_RATE_LIMIT_ATTEMPTS` | No | No | Maximum registration requests per client and window; defaults to 5. |
| `REGISTRATION_RATE_LIMIT_WINDOW_SECONDS` | No | No | Registration rate-limit window; defaults to 60 seconds. |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | No | No | Maximum login requests per client and window; defaults to 5. |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | No | No | Login rate-limit window; defaults to 60 seconds. |
| `SESSION_LIFETIME_MINUTES` | No | No | Absolute authenticated-session lifetime; defaults to 60 minutes. |
| `ARTICLE_SYNC_INTERVAL_SECONDS` | No | No | Durable scheduled interval; defaults to four hours. |
| `ARTICLE_SYNC_PAGE_SIZE` | No | No | Provider page size from 1 to 100; defaults to 50. |
| `ARTICLE_SYNC_MAX_RETRIES` | No | No | Extra attempts for retryable provider failures; defaults to 2. |
| `ARTICLE_SYNC_RETRY_BASE_SECONDS` | No | No | Initial exponential-backoff delay; defaults to 1 second. |
| `ARTICLE_SYNC_LEASE_SECONDS` | No | No | Active worker lease duration; defaults to 300 seconds. |
| `MANUAL_SYNC_RATE_LIMIT_ATTEMPTS` | No | No | Manual triggers per administrator and window; defaults to 2. |
| `MANUAL_SYNC_RATE_LIMIT_WINDOW_SECONDS` | No | No | Manual trigger rate-limit window; defaults to 60 seconds. |
| `INGESTION_METRICS_ENABLED` | No | No | Enables ingestion aggregate calculation; defaults to `true`. |
| `INGESTION_METRICS_WINDOW_HOURS` | No | No | Default metrics window from 1 to 168 hours; defaults to 24. |
| `INGESTION_FAILURE_THRESHOLD` | No | No | Consecutive failures before critical health; defaults to 3. |
| `INGESTION_SUCCESS_STALE_SECONDS` | No | No | Maximum time since a successful sync; defaults to 21600 seconds. |
| `INGESTION_LONG_RUNNING_SECONDS` | No | No | Active-job runtime warning threshold; defaults to 600 seconds. |
| `INGESTION_REJECTION_RATE_PERCENT` | No | No | Recent rejection-rate warning threshold; defaults to 25 percent. |
| `SEED_DATA_ENABLED` | No | No | Explicit safety switch for synthetic development seeding; defaults to `false`. |
| `OPENAI_API_KEY` | Yes for OpenAI features | Yes | Authenticates server-side OpenAI API requests. |
| `OPENAI_MODEL` | Yes for OpenAI features | No | Selects an approved model without hard-coding it in service code. |
| `OPENAI_REQUEST_TIMEOUT` | No | No | OpenAI request timeout from 1 to 300 seconds; defaults to 30. |
| `OPENAI_MAX_OUTPUT_TOKENS` | No | No | Maximum generated output from 1 to 100000 tokens; defaults to 800. |
| `OPENAI_MAX_RETRIES` | No | No | Extra SDK attempts for eligible temporary failures from 0 to 5; defaults to 2. |
| `NEXT_PUBLIC_API_BASE_URL` | No | No | Public URL used by the frontend to reach the backend. Never place credentials here. |

Operating rules:

- Local development uses the ignored repository-root `.env` file.
- Deployed environments must inject secrets through their environment or a managed secret store instead of committing a file.
- Application code accesses credentials through `Settings`; it must not read or hard-code credentials elsewhere.
- Logs, API responses, exception messages, tests, screenshots, and Jira evidence must not contain secret values.
- If a secret is exposed, revoke or rotate it immediately, remove it from active files, and treat Git-history cleanup as a separate incident response task.

## Run the API

Activate the virtual environment, then run:

```bash
fastapi dev app/main.py
```

Keep that terminal running while using these local addresses:

- Health check: `http://127.0.0.1:8000/health`
- Database readiness: `http://127.0.0.1:8000/ready`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Alternative ReDoc documentation: `http://127.0.0.1:8000/redoc`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

The links work only while the local FastAPI development server is running. They are not public deployment URLs.

The health check returns:

```json
{
  "status": "ok"
}
```

The readiness check runs `SELECT 1` against PostgreSQL and returns:

```json
{
  "status": "ready",
  "database": "connected"
}
```

The API checks PostgreSQL during startup. It stops with a safe configuration or connection error when `DATABASE_URL` is missing, invalid, or unreachable. If PostgreSQL becomes unavailable while the API is running, `/ready` returns HTTP `503` without exposing credentials or driver details. `/health` remains a liveness check and does not query the database.

## Register a user

The registration endpoint is:

```text
POST /api/v1/auth/register
```

Example request:

```json
{
  "email": "example@email.com",
  "password": "ExampleSecurePassword123!"
}
```

Example HTTP `201` response:

```json
{
  "id": "generated-user-id",
  "email": "example@email.com",
  "message": "Account created successfully"
}
```

The password must contain 12 to 128 characters with at least one uppercase letter, one lowercase letter, one number, and one non-whitespace symbol. Common passwords are rejected. Passwords are never trimmed, logged by the registration code, saved, or returned. The backend stores only a uniquely salted Argon2id hash using 19 MiB memory, two iterations, and one degree of parallelism.

Email addresses are trimmed, validated with `email-validator`, and stored in lowercase. PostgreSQL constraint `uq_users_email` provides the final duplicate-account guarantee, including concurrent requests. Duplicate registration returns HTTP `409`; invalid input returns `422`; temporary storage failure returns `503` without database details.

Try the endpoint through Swagger UI at `http://127.0.0.1:8000/docs`, or run:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"example@email.com","password":"ExampleSecurePassword123!"}'
```

The in-process limiter allows five registration requests per client per 60 seconds by default and returns HTTP `429` with `Retry-After` when exceeded. It counts invalid requests as well as valid ones. A deployed multi-instance application must also enforce registration limits at a trusted reverse proxy, API gateway, or shared rate-limit store because in-memory counters are not shared between processes.

Production registration traffic must use HTTPS so credentials are encrypted in transit. Configure TLS and trusted proxy handling at the deployment boundary before exposing this endpoint publicly.

## Log in and manage a session

NFA-23 provides these endpoints:

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/logout
```

Login accepts the registered email and password. Unknown accounts and incorrect passwords both return HTTP `401` with the same `Invalid email address or password.` message, which avoids revealing whether an email is registered. Passwords are verified against their Argon2id hashes and are never stored again, logged by the authentication code, or returned.

A successful login creates two independent random values:

- `newsflow_session` is the session identifier. It is sent in an HTTP-only cookie, so browser JavaScript cannot read it.
- `newsflow_csrf` is a CSRF token that the frontend reads and sends in the `X-CSRF-Token` header for state-changing authenticated requests such as logout.

Only SHA-256 hashes of these random values are stored in PostgreSQL. The CSRF hash is tied to the same server-side session, so a different token is rejected. Both cookies use `SameSite=Lax`, `Path=/`, and the configured absolute expiry. The session cookie is also `HttpOnly`. Cookies receive the `Secure` attribute automatically in staging and production, where HTTPS is required; local development and tests can use HTTP on localhost.

Credentialed browser requests are accepted only from the exact `FRONTEND_ORIGIN` configured for the environment. The default is `http://localhost:3000`. CORS allows credentials and the `X-CSRF-Token` header without using a wildcard origin. Deploy the frontend and API on the same site, such as two subdomains of one HTTPS domain, to retain the `SameSite=Lax` protection.

The default session lifetime is 60 minutes. The `/me` endpoint accepts only an active, non-revoked, non-expired session belonging to an active user. Logout requires both cookies and the matching `X-CSRF-Token` header, sets `revoked_at` in PostgreSQL, and expires both browser cookies. An expired or logged-out session receives HTTP `401` from protected endpoints.

With the backend running and a user registered, this terminal example preserves the cookies in a temporary `cookies.txt` file:

```bash
curl -c cookies.txt -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"example@email.com","password":"ExampleSecurePassword123!"}'

curl -b cookies.txt http://127.0.0.1:8000/api/v1/auth/me

CSRF_TOKEN=$(awk '$6 == "newsflow_csrf" { print $7 }' cookies.txt)
curl -b cookies.txt -X POST http://127.0.0.1:8000/api/v1/auth/logout \
  -H "X-CSRF-Token: ${CSRF_TOKEN}"
```

Delete `cookies.txt` after the check because it contains local session credentials. Browser frontend code must send requests with credentials enabled and copy the `newsflow_csrf` cookie into the `X-CSRF-Token` header for protected state-changing requests.

Login is limited to five attempts per client per 60 seconds by default. As with registration, a deployed multi-instance application must also enforce abuse controls at a trusted proxy, API gateway, or shared rate-limit store. Configure trusted proxy handling before relying on a client IP supplied through deployment infrastructure.

## Access private saved content

NFA-25 provides owner-scoped endpoints under `/api/v1/library/items` for creating, listing, reading, renaming, soft-deleting, and exporting saved content. An endpoint never trusts an owner supplied by a browser. The owner comes from the active session, and repository queries match both the resource ID and session user ID.

Read and export requests require the HTTP-only session cookie. Create, update, and delete requests also require the matching `newsflow_csrf` value in the `X-CSRF-Token` header. A missing item and another user's item both produce the same safe HTTP `404` response. This prevents record identifiers from revealing private data.

The API request schemas do not contain `user_id`, and unexpected fields are rejected. The original NFA-20 migration already includes the composite ownership foreign key, so this feature does not add or change a database migration. See [the object-level authorisation guide](../../docs/authorization.md) for the complete rules and evidence.

## Use the news-source provider interface

NFA-28 defines a typed `NewsProvider` protocol with two asynchronous operations:

- `fetch_articles(query)` discovers a validated page of permitted articles.
- `fetch_article(source_item_id)` retrieves one validated article.

The common `NewsArticle` model follows the approved NFA-6 contract. It contains article metadata, permitted content, attribution, rights, and provenance rather than allowing provider-specific response fields into application services.

The current `FixtureNewsProvider` maps original synthetic records with internal names such as `headline` and `published_at` into the common model. It makes no network requests and uses only `example.invalid` URLs. It supports opaque cursor pagination and a `published_after` filter.

Select the fixture provider explicitly through local configuration:

```dotenv
NEWS_SOURCE_MODE=fixture
```

If no source mode is supplied directly to `Settings`, it defaults to `disabled`. The provider factory then raises `SOURCE_NOT_AUTHORISED` without attempting access. No live or CNN setting exists. See the [complete provider integration guide](../../docs/source-provider-interface.md).

Run the focused tests from `apps/api`:

```bash
pytest tests/test_source_provider.py
```

### Disabled CNN adapter

`CnnSourceAdapter` implements the provider protocol but does not implement a live service. Its list and detail methods immediately raise `SOURCE_NOT_AUTHORISED`. It has no endpoint, HTTP client, authentication mechanism, credentials, response parser, pagination rules, timeout, or retry configuration because none has been authorised or documented.

The adapter records the non-secret NFA-5 authorisation decision and NFA-8 architecture decision. Automated tests replace the HTTP request method with a failure and prove that it is never called. A `cnn` source mode remains invalid, and proposed CNN environment variables are ignored rather than enabling access.

Run the focused safety tests:

```bash
pytest tests/test_cnn_adapter.py
```

See the [NFA-29 CNN adapter record](../../docs/cnn-adapter.md) for the blocked acceptance criteria and future activation requirements.

### Normalise provider article data

NFA-30 sends every synthetic fixture record through `ArticleNormalisationService` before the provider returns a `NewsArticle`. The service works at the provider boundary, before future database storage or application use.

The active policy:

- Reads only the approved synthetic fixture fields.
- Maps provider-specific names such as `headline` and `link` into the standard article model.
- Converts timezone-aware timestamps to UTC.
- Normalises Unicode and whitespace without inventing missing facts.
- Rejects raw, encoded, or incomplete HTML-like markup and unsupported control characters.
- Accepts only HTTPS URLs on the policy's approved `example.invalid` host.
- Supplies attribution, provenance, and rights values from trusted policy configuration.
- Returns stable, safe errors without repeating restricted provider content.

The final Pydantic `NewsArticle` model provides a second contract-validation layer. Extra provider fields, such as images, internal notes, or unlicensed full text, are not copied into that model.

Run the focused tests:

```bash
pytest tests/test_article_normalisation.py
pytest tests/test_source_provider.py tests/test_cnn_adapter.py
```

See the [complete article normalisation guide](../../docs/article-normalisation.md) for the allowlist, processing rules, errors, tests, and future-provider requirements.

### Persist articles without duplicates

NFA-31 applies identity after NFA-30 has normalised the article. A stable provider item ID is preferred. If the provider ID is missing, the synthetic profile creates a deterministic `fixture-url-` identifier from the SHA-256 hash of the canonical URL. Titles are never used as identity.

`SqlAlchemyArticleRepository` persists one stable `articles` row and immutable `article_snapshots` rows. It uses the existing NFA-20 uniqueness constraints for `(source_profile_id, source_item_id)` and `canonical_url`. Atomic PostgreSQL conflict handling prevents two concurrent workers from creating duplicates.

An ingestion operation reports:

- `created` when a new article and first snapshot are inserted.
- `updated` when permitted metadata changes and a new snapshot becomes current.
- `skipped` when the normalised permitted content already matches the current snapshot.

Updates preserve the stable article ID and every earlier snapshot, including snapshots linked to generated content. A later retrieval timestamp by itself is skipped. Conflicting identifiers and URLs fail safely instead of being merged automatically.

Run the fast NFA-31 tests:

```bash
pytest tests/test_article_deduplication.py
```

See the [article identity and deduplication guide](../../docs/article-identity-and-deduplication.md) for the complete strategy, transaction flow, constraints, test evidence, and limitations.

### Verify article provenance and rights

NFA-32 extends ingestion so every created, updated, and skipped article retrieval writes an immutable provenance event. It records the source profile, permitted external identifier, canonical URL, publication and retrieval times, data-contract version, integration reference, and non-secret authorisation reference.

Article permissions are stored as immutable versions. The `articles.current_rights_version_id` pointer selects the policy used for new checks without deleting earlier audit evidence. `ArticleRightsService` checks display, storage, AI generation, export, and retention operations. It denies missing, unverified, revoked, expired, disabled-source, or ungranted use by default. AI generation requires both AI-processing and derivative-output permission.

Run the focused tests:

```bash
pytest tests/test_article_rights.py tests/test_article_deduplication.py
```

See the [article provenance and rights guide](../../docs/article-provenance-and-rights.md) for the model, constraints, update rules, integration-test command, and limitations.

### Synchronise the article catalogue

NFA-33 coordinates the existing provider, normalisation, deduplication, provenance, and rights components through one shared `ArticleSyncService`. PostgreSQL records every job's trigger, status, requester, lease, checkpoint, counts, safe error, and timestamps.

Manual synchronisation is available only to an authenticated administrator with CSRF proof:

```text
POST /api/v1/admin/articles/sync
GET  /api/v1/admin/articles/sync/{job_id}
```

The POST operation returns HTTP 202 with a durable job ID. It cannot bypass source enablement, active-job locking, or the manual rate limit. Ordinary users receive HTTP 403.

Run the schedule-aware one-shot worker from the repository root:

```bash
docker compose exec backend python -m app.jobs.article_sync_job
```

PostgreSQL grants only one due schedule reservation and one active provider job, even when multiple processes invoke the command. Failed, partial, or interrupted jobs keep the last fully successful incremental checkpoint.

Run the fast tests:

```bash
pytest tests/test_article_sync.py tests/test_admin_article_sync.py
```

See the [article synchronisation guide](../../docs/article-synchronisation.md) for administrator setup, configuration, job states, retries, recovery, scheduled deployment, testing, and troubleshooting.

### Browse the article catalogue

NFA-34 provides two read-only endpoints for authenticated users:

```text
GET /api/articles
GET /api/articles/{article_id}
```

The list endpoint supports `limit`, opaque `cursor`, `search`, `provider`, `published_from`, `published_to`, and `sort` parameters. `sort` accepts `newest` or `oldest`, and the maximum page size is 100.

SQLAlchemy reads only current PostgreSQL snapshots whose article is active, source is enabled, and current rights permit display. Missing, restricted, expired, unverified, and disabled-source detail records all return the same HTTP 404. Public responses contain title, description, canonical URL, provider, publication date, category, and required attribution. They exclude stored article text, internal rights versions, agreement references, provider IDs, snapshots, and audit records.

Use Swagger UI at `http://127.0.0.1:8000/docs` to inspect the `Article catalogue` section after logging in. See the [article catalogue API guide](../../docs/article-catalogue-api.md) for the complete contract, cursor behaviour, rights rules, errors, migration, and test evidence.

### Monitor article ingestion

NFA-35 extends each existing synchronisation job with cumulative provider-request duration, a stable error category, and a failure stage. It emits structured start, request, retry, completion, partial-completion, and failure events without article content, provider payloads, URLs, credentials, or traceback details.

Authenticated administrators can inspect ingestion operations through:

```text
GET /api/admin/sync/jobs
GET /api/admin/sync/jobs/{job_id}
GET /api/admin/sync/metrics
GET /api/admin/sync/health
```

The health response detects repeated failures, stale successful synchronisation, long-running jobs, and high rejection rates using environment-configured thresholds. Use `LOG_FORMAT=json` for log collection or `LOG_FORMAT=console` for readable local output. See the [ingestion observability guide](../../docs/ingestion-observability.md) for fields, metrics, configuration, operational response, tests, and limitations.

### Generate text through the OpenAI service

NFA-38 adds `OpenAIService` as the single backend boundary for future text generation. It uses the official asynchronous OpenAI Python SDK and the Responses API. The model, request timeout, maximum output tokens, and bounded SDK retry budget come from validated environment settings.

The service returns generated text, model and request identifiers, and available token usage through provider-neutral Pydantic models. It maps authentication, rate-limit, timeout, connection, service, request, incomplete-response, and output-limit failures to safe application errors. Logs exclude API keys, prompts, instructions, generated output, raw responses, and provider error details.

No public FastAPI generation endpoint is included in NFA-38. A later E4 workflow must authenticate and authorise the user, apply NFA-32 rights checks, supply only permitted article information, enforce user-level limits, and then call this internal service. See the [OpenAI integration guide](../../docs/openai-integration.md) for configuration, usage, error policy, security controls, tests, and limitations.

## Run with Docker Compose

NFA-16 adds a backend development image and runs it with the frontend and PostgreSQL from the root `compose.yaml` file. From the repository root:

```bash
cp .env.example .env
docker compose up --build
```

Replace the PostgreSQL placeholders in `.env` before starting. Compose supplies a container-specific database URL that uses `database` as the PostgreSQL hostname. The backend waits for PostgreSQL to become healthy, performs its own startup connection check, and then exposes its health and readiness endpoints on `http://localhost:8000`.

Use `docker compose down` for a normal shutdown. The PostgreSQL named volume remains available for the next startup. See the [complete Docker development guide](../../infrastructure/docker/README.md) for configuration, service checks, logs, persistence, and troubleshooting.

## Database migrations and seed data

Alembic is the selected migration tool. SQLAlchemy supplies the migration types and the asynchronous registration repository, while the readiness check uses Psycopg directly. Both read `DATABASE_URL` through the same validated settings class, so no password is stored in `alembic.ini`.

From `apps/api`, with the virtual environment active and PostgreSQL running:

```bash
alembic current
alembic upgrade head
alembic history
```

The initial migration creates the complete NFA-20 schema, keys, indexes, constraints, update triggers, and `pgcrypto` extension. NFA-23 migration `20261025_0002` adds the server-validated CSRF hash and session lookup indexes. NFA-32 migration `20261029_0003` adds article provenance events and versioned rights. NFA-33 migration `20261029_0004` adds administrator roles, synchronisation jobs, leases, checkpoints, statistics, and concurrency constraints. NFA-34 migration `20261029_0005` adds the stable catalogue ordering index. NFA-35 migration `20261029_0006` adds provider failure counts, provider duration, failure category, failure stage, and operational query indexes. To roll back the latest revision in a disposable development database:

```bash
alembic downgrade -1
```

From revision `20261029_0006`, this command removes the NFA-35 observability fields and indexes. A second downgrade removes the NFA-34 catalogue ordering index, and a third removes the NFA-33 synchronisation tables and administrator-role column. Downgrading all the way to `base` deletes all NewsFlow AI tables and their data. Never downgrade a database containing information that must be retained without a reviewed recovery plan. Future schema changes must be added as new reviewed revisions instead of editing a migration that has already been shared.

Development seeding is deliberately disabled by default. It runs only when `APP_ENV` is `development` or `test` and `SEED_DATA_ENABLED=true` is explicitly supplied:

```bash
SEED_DATA_ENABLED=true python -m app.database.seed
```

The script inserts deterministic fictional records, uses the reserved `example.invalid` domain, creates a disabled account with no usable password, and contains no CNN content or credentials. It uses fixed identifiers and conflict-safe inserts, so running the command again does not create duplicate fixtures. It refuses to run in staging or production.

With Docker Compose running, use:

```bash
docker compose exec backend alembic upgrade head
docker compose exec -e SEED_DATA_ENABLED=true backend python -m app.database.seed
```

## Run the tests

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=75
```

The normal test suite uses database and OpenAI test doubles, so it does not need real credentials, an OpenAI API key, a live provider request, or a running PostgreSQL server. It verifies environment loading, masked secret representations, missing-configuration errors, placeholder rejection, startup checking, liveness, readiness, safe database failure responses, generated OpenAPI documentation, standard API errors, seed safety gates, owner-scoped collections, blocked cross-user operations, and the NFA-38 OpenAI success, usage, cost-control, error, retry, and redaction behaviours.

Run the focused NFA-38 tests with:

```bash
pytest tests/test_config.py tests/test_openai_service.py
```

NFA-26 provides shared, function-scoped fixtures in `tests/conftest.py` and a complete regression journey in `tests/test_account_security_regression.py`. Run that focused suite with:

```bash
pytest tests/test_account_security_regression.py
```

Every test receives fresh synthetic accounts, sessions, cookies, resources, and repository state. No normal test contacts a live service or modifies the development database.

To prove the connection against your configured local PostgreSQL database, run the opt-in integration test without placing the URL in Git:

```bash
TEST_DATABASE_URL="$DATABASE_URL" pytest -m integration tests/test_database_integration.py
```

The migration integration test is intentionally destructive and requires a separate disposable database whose name contains `newsflow_migration_test`. It verifies upgrade from empty, expected tables, connectivity, two identical seed runs, complete rollback, and a final rebuild:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_migration_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_migrations_integration.py
```

Never point this test at the normal development database or any shared database.

The registration integration test requires a separate disposable database whose name contains `newsflow_registration_test`. It verifies real PostgreSQL insertion, lowercase email storage, Argon2id hashing, and uniqueness enforcement:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_registration_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_registration_integration.py
```

The authentication integration test requires a separate disposable database whose name contains `newsflow_authentication_test`. It verifies registration, login, hashed token persistence, current-user access, CSRF-protected logout, revocation, and expiry rejection:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_authentication_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_authentication_integration.py
```

The NFA-26 ownership integration test requires a separate disposable database whose name contains `newsflow_account_security_test`. It proves owner filtering and cross-user denial through the real SQLAlchemy and PostgreSQL repositories:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_account_security_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_account_security_integration.py
```

The NFA-31 integration test requires a separate disposable database whose name contains `newsflow_article_deduplication_test`. It verifies the existing article uniqueness constraints, idempotent ingestion, immutable metadata updates, preserved snapshot relationships, similar titles, and concurrent insert protection:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_article_deduplication_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_article_deduplication_integration.py
```

The NFA-33 integration test requires a separate disposable database whose name contains `newsflow_article_sync_test`. It verifies real job, administrator, checkpoint, article, provenance, rights, statistics, incremental, and active-job constraints:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_article_sync_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_article_sync_integration.py
```

The NFA-34 integration test requires a separate disposable database whose name contains `newsflow_article_catalogue_test`. It verifies PostgreSQL pagination, search, provider and date filters, sorting, restricted-record exclusion, SQL-injection-like input, and the ordering index:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_article_catalogue_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_article_catalogue_integration.py
```

The NFA-36 pipeline suite requires a separate disposable database named `newsflow_pipeline_test`. It verifies the full synthetic provider, normalisation, deduplication, PostgreSQL, provenance, rights, synchronisation, observability, and REST API workflow. It also proves invalid-input safety, database-failure safety, source blocking, restricted AI use, and concurrent deduplication:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_pipeline_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_catalogue_pipeline_e2e.py
```

See the [NFA-36 article pipeline testing guide](../../docs/article-pipeline-testing.md) for the fixture design, safety gates, verified results, and limitations.

See the [complete testing guide](../../docs/testing.md) before running any destructive integration test.

## Code quality

Install the development dependencies, including Ruff and Pytest, with `python -m pip install -e ".[dev]"`. Run the backend checks from `apps/api`:

```bash
ruff check .
ruff format --check .
pytest --cov=app --cov-report=term-missing --cov-fail-under=75
```

Apply safe automatic lint fixes and formatting when needed:

```bash
ruff check --fix .
ruff format .
```

Ruff checks Python syntax errors, undefined names, import ordering, modern Python usage, and common bug patterns. Ruff also supplies the single Python formatter, avoiding competing formatting tools. Pytest covers health, configuration, accounts, sessions, authorisation, provider boundaries, normalisation, identity, provenance, rights, synchronisation, the article catalogue API, ingestion observability, the NFA-36 complete synthetic pipeline, and the mocked NFA-38 OpenAI boundary. Pytest-cov measures branch-aware backend coverage and enforces the documented 75 percent floor.

## Project structure

```text
apps/api/
|-- Dockerfile                  # FastAPI development image
|-- .dockerignore               # Files excluded from the image build context
|-- app/
|   |-- api/routes/health.py    # GET /health
|   |-- api/routes/auth.py      # Register, login, current-user, and logout APIs
|   |-- api/routes/library.py   # Owner-scoped saved-content APIs
|   |-- api/routes/article_sync.py # Protected manual sync and job-status APIs
|   |-- api/routes/ingestion_observability.py # Protected jobs, metrics, and health APIs
|   |-- api/routes/articles.py  # Authenticated article list and detail APIs
|   |-- api/dependencies.py     # Shared session and CSRF route protection
|   |-- core/ai_config.py       # Validated OpenAI settings object
|   |-- core/config.py          # Environment-based settings
|   |-- core/errors.py          # Standard JSON exception handlers
|   |-- core/logging_config.py  # Structured formatting and credential redaction
|   |-- database/connection.py  # PostgreSQL connection check
|   |-- database/seed.py        # Repeatable synthetic development fixtures
|   |-- database/sqlalchemy.py  # Async SQLAlchemy sessions
|   |-- database/tables.py      # Migration-backed application table mappings
|   |-- models/auth.py          # Registration and authentication API schemas
|   |-- models/health.py        # Health response schema
|   |-- models/library.py       # Private saved-content API schemas
|   |-- models/article_rights.py # Provenance, rights policy, and decision models
|   |-- models/article_sync.py  # Job, checkpoint, status, and statistics models
|   |-- models/ingestion_observability.py # Metrics and health response schemas
|   |-- models/article_catalogue.py # Catalogue query and public response schemas
|   |-- models/ai.py            # Masked generation input and structured result
|   |-- jobs/article_sync_job.py # One-shot durable scheduled-job entry point
|   |-- providers/              # Provider protocol, normalisation, fixture, and disabled CNN boundary
|   |-- repositories/articles.py # Atomic article and immutable snapshot persistence
|   |-- repositories/article_rights.py # Rights versions and provenance queries
|   |-- repositories/article_sync.py # Jobs, leases, checkpoints, and admin checks
|   |-- repositories/article_catalogue.py # Rights-aware article catalogue queries
|   |-- repositories/authentication.py # Login and session persistence
|   |-- repositories/library.py # Owner-scoped saved-content persistence
|   |-- repositories/users.py   # PostgreSQL registration persistence
|   |-- security/               # Argon2id and authentication rate limiting
|   |-- services/authentication.py # Login, session, CSRF, and logout workflow
|   |-- services/article_deduplication.py # Idempotent article ingestion workflow
|   |-- services/article_rights.py # Fail-closed permission checks and updates
|   |-- services/article_sync.py # Scheduled and manual synchronisation workflow
|   |-- services/ingestion_observability.py # Metrics and health derivation
|   |-- services/article_catalogue.py # Public fields, visibility, and cursor rules
|   |-- services/article_identity.py # Provider ID and canonical-URL fallback rules
|   |-- services/authorization.py # Reusable owned-resource rule
|   |-- services/library.py     # Private saved-content workflow
|   |-- services/openai_service.py # Secure reusable Responses API boundary
|   |-- services/registration.py # Registration workflow
|   `-- main.py                 # FastAPI application factory and entry point
|-- migrations/                 # Alembic environment and revision files
|-- alembic.ini                 # Credential-free migration configuration
|-- tests/test_api.py           # API and readiness tests
|-- tests/conftest.py           # Reusable isolated security and PostgreSQL fixtures
|-- tests/fixtures/             # Reusable valid and invalid synthetic article records
|-- tests/support/              # Synthetic repositories, fixture loaders, and database safety helpers
|-- tests/test_account_security_regression.py # Full fast security journey
|-- tests/test_account_security_integration.py # Opt-in PostgreSQL ownership proof
|-- tests/test_article_normalisation.py # Article mapping, validation, sanitisation, and rights tests
|-- tests/test_article_deduplication.py # Fast identity, update, conflict, and concurrency tests
|-- tests/test_article_deduplication_integration.py # Opt-in PostgreSQL deduplication proof
|-- tests/test_article_sync.py # Fast scheduled, manual, retry, and checkpoint tests
|-- tests/test_admin_article_sync.py # Protected manual sync API tests
|-- tests/test_admin_ingestion_observability.py # Protected operations API tests
|-- tests/test_ingestion_observability.py # Logging, metrics, and health tests
|-- tests/test_article_sync_integration.py # Opt-in PostgreSQL sync workflow proof
|-- tests/test_article_catalogue.py # Fast authenticated catalogue API tests
|-- tests/test_article_catalogue_integration.py # Opt-in PostgreSQL catalogue proof
|-- tests/test_article_pipeline_fixtures.py # Synthetic pipeline fixture contract tests
|-- tests/test_catalogue_pipeline_e2e.py # Complete isolated PostgreSQL pipeline proof
|-- tests/test_authentication.py # Fast authentication and cookie tests
|-- tests/test_authentication_integration.py # Opt-in PostgreSQL auth test
|-- tests/test_authorization.py # Cross-user ownership and safe-error tests
|-- tests/test_config.py        # Environment and secret-safety tests
|-- tests/test_cnn_adapter.py   # Disabled CNN access and no-network tests
|-- tests/test_database_integration.py # Opt-in live PostgreSQL test
|-- tests/test_migrations_integration.py # Opt-in destructive migration test
|-- tests/test_openai_service.py # Mocked OpenAI success, failure, usage, and security tests
|-- tests/test_passwords.py      # Argon2id hashing tests
|-- tests/test_rate_limit.py     # Registration abuse-control tests
|-- tests/test_registration.py   # Registration API tests
|-- tests/test_registration_integration.py # Opt-in PostgreSQL registration test
|-- tests/test_seed.py          # Seed safety and fixture tests
|-- tests/test_source_provider.py # Provider mapping, errors, pagination, and replacement
|-- .python-version             # Recommended Python runtime
|-- pyproject.toml              # Application and development dependencies
`-- README.md                   # Backend setup and operating guide
```

## Error response format

Expected HTTP errors, validation errors, and unexpected server errors use one top-level `error` object. For example, an unknown route returns:

```json
{
  "error": {
    "code": "http_404",
    "message": "Not Found"
  }
}
```

Unexpected exceptions are logged on the server, while clients receive a generic message that does not expose internal implementation details.

## Dependencies

Dependencies are declared in `pyproject.toml`:

- `fastapi[standard-no-fastapi-cloud-cli]` provides FastAPI, the Uvicorn development server, and the standard local development dependencies without adding deployment tooling.
- `psycopg[binary]` provides the PostgreSQL driver and asynchronous connection support.
- `SQLAlchemy[asyncio]` supplies asynchronous PostgreSQL sessions and migration types.
- `Alembic` versions, applies, and rolls back PostgreSQL schema changes.
- `argon2-cffi` hashes passwords using Argon2id with a unique random salt.
- `email-validator` validates registration email addresses through Pydantic.
- `pydantic-settings` validates environment-based application settings and masks the database URL and OpenAI API key as secret values.
- `httpx2` supports Starlette's test client used by FastAPI.
- `pytest` runs the automated tests.
- `pytest-cov` measures branch-aware backend coverage and enforces the CI floor.
- `ruff` provides Python linting, import checks, bug-pattern checks, and formatting.
- `hatchling` builds the installable Python package.

Application code must not read secrets directly from committed files. OpenAI credentials, database credentials, and other secrets must be provided through ignored environment variables or a managed secret store.
