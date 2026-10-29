# NewsFlow AI API

This directory contains NewsFlow AI's Python FastAPI backend. NFA-13 to NFA-17 establish the application, PostgreSQL, configuration, Docker, and quality foundations. NFA-21 adds SQLAlchemy, Alembic migrations, and synthetic seed data. NFA-22 to NFA-26 add the secure account lifecycle, object-level authorisation, regression coverage, and automated pull-request checks. NFA-28 adds a reusable news-source interface and synthetic fixture provider. NFA-29 adds a disabled CNN adapter boundary enforced by the active No-Go decision. NFA-30 adds rights-aware article normalisation, validation, and sanitisation. NFA-31 adds stable article identity and atomic deduplication. NFA-32 adds immutable provenance, versioned rights metadata, and fail-closed usage checks.

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
NEWS_SOURCE_MODE=fixture
FRONTEND_ORIGIN=http://localhost:3000
DATABASE_URL=postgresql://your_local_user:your_local_password@localhost:5432/newsflow
DATABASE_CONNECT_TIMEOUT_SECONDS=5
REGISTRATION_RATE_LIMIT_ATTEMPTS=5
REGISTRATION_RATE_LIMIT_WINDOW_SECONDS=60
LOGIN_RATE_LIMIT_ATTEMPTS=5
LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
SESSION_LIFETIME_MINUTES=60
OPENAI_API_KEY=your_real_openai_api_key
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`DATABASE_URL` is required when the API starts. `OPENAI_API_KEY` is loaded and validated by the backend but is required only when an OpenAI-powered feature runs. This keeps the current non-AI API usable while its OpenAI integration is developed. Empty values and the committed example placeholders produce clear errors without printing secret values.

Do not add real credentials to `.env.example`, source code, browser code, documentation, Jira, screenshots, commits, or pull requests. The repository `.gitignore` excludes `.env` files while retaining the safe `.env.example` template. The OpenAI API key is server-side only and must never use a `NEXT_PUBLIC_` name because Next.js exposes variables with that prefix to browser code. This follows [OpenAI's API authentication guidance](https://developers.openai.com/api/reference/overview), which says API keys must be loaded from an environment variable or key management service on the server.

### Configuration reference

| Variable | Required | Sensitive | Purpose |
|---|---|---|---|
| `APP_ENV` | No | No | Selects `development`, `test`, `staging`, or `production`; defaults to `development`. |
| `NEWS_SOURCE_MODE` | No | No | Defaults to `disabled`; local development explicitly selects the approved `fixture` provider. |
| `FRONTEND_ORIGIN` | No | No | Exact browser origin allowed to call the API with cookies; defaults to `http://localhost:3000`. |
| `DATABASE_URL` | Yes at API startup | Yes | PostgreSQL connection string containing the database credentials. |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` | No | No | Database connection timeout from 1 to 30 seconds; defaults to 5. |
| `REGISTRATION_RATE_LIMIT_ATTEMPTS` | No | No | Maximum registration requests per client and window; defaults to 5. |
| `REGISTRATION_RATE_LIMIT_WINDOW_SECONDS` | No | No | Registration rate-limit window; defaults to 60 seconds. |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | No | No | Maximum login requests per client and window; defaults to 5. |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | No | No | Login rate-limit window; defaults to 60 seconds. |
| `SESSION_LIFETIME_MINUTES` | No | No | Absolute authenticated-session lifetime; defaults to 60 minutes. |
| `SEED_DATA_ENABLED` | No | No | Explicit safety switch for synthetic development seeding; defaults to `false`. |
| `OPENAI_API_KEY` | Yes for OpenAI features | Yes | Authenticates server-side OpenAI API requests. |
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

The initial migration creates the complete NFA-20 schema, keys, indexes, constraints, update triggers, and `pgcrypto` extension. NFA-23 migration `20261025_0002` adds the server-validated CSRF hash and session lookup indexes. NFA-32 migration `20261029_0003` adds article provenance events, versioned rights metadata, the current-rights pointer, and database constraints. To roll back the latest revision in a disposable development database:

```bash
alembic downgrade -1
```

From revision `20261025_0002`, this command removes only the NFA-23 session additions. Downgrading all the way to `base` also runs the initial downgrade and deletes all NewsFlow AI tables and their data. Never downgrade a database containing information that must be retained without a reviewed recovery plan. Future schema changes must be added as new reviewed revisions instead of editing a migration that has already been shared.

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
pytest
```

The normal test suite uses database test doubles, so it does not need real credentials, an OpenAI API key, or a running PostgreSQL server. It verifies environment loading, masked secret representations, missing-configuration errors, placeholder rejection, startup checking, liveness, readiness, safe database failure responses, generated OpenAPI documentation, standard API errors, seed safety gates, owner-scoped collections, and blocked cross-user read, update, delete, and export attempts.

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

See the [complete testing guide](../../docs/testing.md) before running any destructive integration test.

## Code quality

Install the development dependencies, including Ruff and Pytest, with `python -m pip install -e ".[dev]"`. Run the backend checks from `apps/api`:

```bash
ruff check .
ruff format --check .
pytest
```

Apply safe automatic lint fixes and formatting when needed:

```bash
ruff check --fix .
ruff format .
```

Ruff checks Python syntax errors, undefined names, import ordering, modern Python usage, and common bug patterns. Ruff also supplies the single Python formatter, avoiding competing formatting tools. Pytest covers health and readiness, safe errors, secure configuration, registration, credential verification, session expiry, cookie controls, CSRF validation, logout, rate limiting, cross-user object-level authorisation, the provider boundary, normalisation, identity, deduplication, provenance, and fail-closed rights decisions.

## Project structure

```text
apps/api/
|-- Dockerfile                  # FastAPI development image
|-- .dockerignore               # Files excluded from the image build context
|-- app/
|   |-- api/routes/health.py    # GET /health
|   |-- api/routes/auth.py      # Register, login, current-user, and logout APIs
|   |-- api/routes/library.py   # Owner-scoped saved-content APIs
|   |-- api/dependencies.py     # Shared session and CSRF route protection
|   |-- core/config.py          # Environment-based settings
|   |-- core/errors.py          # Standard JSON exception handlers
|   |-- database/connection.py  # PostgreSQL connection check
|   |-- database/seed.py        # Repeatable synthetic development fixtures
|   |-- database/sqlalchemy.py  # Async SQLAlchemy sessions
|   |-- database/tables.py      # Migration-backed application table mappings
|   |-- models/auth.py          # Registration and authentication API schemas
|   |-- models/health.py        # Health response schema
|   |-- models/library.py       # Private saved-content API schemas
|   |-- models/article_rights.py # Provenance, rights policy, and decision models
|   |-- providers/              # Provider protocol, normalisation, fixture, and disabled CNN boundary
|   |-- repositories/articles.py # Atomic article and immutable snapshot persistence
|   |-- repositories/article_rights.py # Rights versions and provenance queries
|   |-- repositories/authentication.py # Login and session persistence
|   |-- repositories/library.py # Owner-scoped saved-content persistence
|   |-- repositories/users.py   # PostgreSQL registration persistence
|   |-- security/               # Argon2id and authentication rate limiting
|   |-- services/authentication.py # Login, session, CSRF, and logout workflow
|   |-- services/article_deduplication.py # Idempotent article ingestion workflow
|   |-- services/article_rights.py # Fail-closed permission checks and updates
|   |-- services/article_identity.py # Provider ID and canonical-URL fallback rules
|   |-- services/authorization.py # Reusable owned-resource rule
|   |-- services/library.py     # Private saved-content workflow
|   |-- services/registration.py # Registration workflow
|   `-- main.py                 # FastAPI application factory and entry point
|-- migrations/                 # Alembic environment and revision files
|-- alembic.ini                 # Credential-free migration configuration
|-- tests/test_api.py           # API and readiness tests
|-- tests/conftest.py           # Reusable isolated security and PostgreSQL fixtures
|-- tests/support/              # Synthetic repositories and test safety helpers
|-- tests/test_account_security_regression.py # Full fast security journey
|-- tests/test_account_security_integration.py # Opt-in PostgreSQL ownership proof
|-- tests/test_article_normalisation.py # Article mapping, validation, sanitisation, and rights tests
|-- tests/test_article_deduplication.py # Fast identity, update, conflict, and concurrency tests
|-- tests/test_article_deduplication_integration.py # Opt-in PostgreSQL deduplication proof
|-- tests/test_authentication.py # Fast authentication and cookie tests
|-- tests/test_authentication_integration.py # Opt-in PostgreSQL auth test
|-- tests/test_authorization.py # Cross-user ownership and safe-error tests
|-- tests/test_config.py        # Environment and secret-safety tests
|-- tests/test_cnn_adapter.py   # Disabled CNN access and no-network tests
|-- tests/test_database_integration.py # Opt-in live PostgreSQL test
|-- tests/test_migrations_integration.py # Opt-in destructive migration test
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
- `ruff` provides Python linting, import checks, bug-pattern checks, and formatting.
- `hatchling` builds the installable Python package.

Application code must not read secrets directly from committed files. OpenAI credentials, database credentials, and other secrets must be provided through ignored environment variables or a managed secret store.
