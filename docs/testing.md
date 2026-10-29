# NewsFlow AI Testing Guide

## Purpose

This guide records the automated test strategy for account security and the provider-to-database article workflow, including NFA-33 synchronisation, the NFA-34 article catalogue REST API, NFA-35 ingestion observability, and the NFA-36 complete synthetic pipeline suite.

The test suite is designed to detect security regressions before a pull request is merged. It uses only synthetic users, passwords, sessions, and content.

## Test layers

| Layer | Location | Purpose |
|---|---|---|
| Backend unit and API tests | `apps/api/tests/test_*.py` | Fast tests for accounts, providers, articles, rights, synchronisation, catalogue endpoints, CSRF, safe errors, and authorisation. |
| Account-security regression tests | `apps/api/tests/test_account_security_regression.py` | One integrated in-memory journey from registration through private-content access and logout. |
| PostgreSQL integration tests | `apps/api/tests/*_integration.py` | Opt-in verification of migrations, constraints, accounts, ownership, article ingestion, provenance, rights, synchronisation, and catalogue queries. |
| Frontend authentication tests | `apps/web/__tests__` | Registration, login, logout, error, loading, session restoration, gateway, and protected-route behaviour. |
| Complete article pipeline | `apps/api/tests/test_catalogue_pipeline_e2e.py` | Safety-gated synthetic provider-to-PostgreSQL-to-REST verification, including failure, rights, logs, and concurrent ingestion. |
| Pull-request quality checks | `.github/workflows/quality.yml` | Runs backend and frontend quality checks, enforces backend coverage, and runs the isolated NFA-36 PostgreSQL suite on GitHub. |

## NFA-26 coverage

| Requirement | Automated evidence |
|---|---|
| Successful and invalid registration | `test_registration.py` and the account-security regression suite |
| Duplicate registration | `test_registration.py`, PostgreSQL registration integration, and regression suite |
| Argon2id password hashing | `test_passwords.py`, registration tests, and regression suite |
| Successful and failed login | `test_authentication.py` and regression suite |
| Session creation and secure cookies | `test_authentication.py` and PostgreSQL authentication integration |
| Session expiry, logout, and reuse prevention | Authentication tests and regression suite |
| Unauthenticated protected access | Authentication, authorisation, and regression tests |
| Cross-user read, update, delete, export, and collection filtering | `test_authorization.py`, regression suite, and PostgreSQL account-security integration |
| Client-supplied owner manipulation | Authorisation and regression tests |
| Sensitive response exclusion | Registration, authentication, authorisation, and regression tests |
| Frontend authentication behaviour | Vitest tests in `apps/web/__tests__` |
| Automated quality process | GitHub Actions quality workflow |

## Reusable isolated fixtures

`apps/api/tests/conftest.py` provides a fresh `account_security_context` for each test. It contains:

- A FastAPI `TestClient`.
- A synthetic user repository.
- A synthetic session repository.
- Synthetic user-owned posts and saved content.
- An Argon2id password hasher.
- Helpers for registration, login, browser cookies, and CSRF headers.

Each fixture is function-scoped. Accounts, sessions, cookies, and private content are discarded after each test, so one test cannot affect another and repeated runs start clean.

The `account_security_postgres` fixture is available only to the opt-in integration test. It requires a deliberately named disposable database, applies all Alembic migrations before the test, and removes the schema afterwards.

## NFA-33 synchronisation coverage

| Requirement | Automated evidence |
|---|---|
| Scheduled and manual workflows share one service | `test_article_sync.py` |
| Administrator-only manual trigger and CSRF dependency | `test_admin_article_sync.py` |
| Manual request throttling | `test_admin_article_sync.py` |
| Pagination, statistics, and incremental checkpoint | `test_article_sync.py` and PostgreSQL sync integration |
| Duplicate article and active-job prevention | Sync unit tests and PostgreSQL sync integration |
| Temporary retry and permanent failure policy | `test_article_sync.py` |
| Partial failure does not advance the checkpoint | `test_article_sync.py` |
| Expired worker recovery | `test_article_sync.py` |
| Live CNN remains disabled | Existing CNN adapter tests and source-profile checks |
| Real jobs, articles, provenance, rights, and checkpoints | `test_article_sync_integration.py` |

Run the fast NFA-33 tests from `apps/api`:

```bash
pytest tests/test_article_sync.py tests/test_admin_article_sync.py
```

## NFA-34 article catalogue coverage

| Requirement | Automated evidence |
|---|---|
| Authenticated list and detail endpoints | `test_article_catalogue.py` |
| Public response schema and internal-field exclusion | `test_article_catalogue.py` |
| Cursor pagination and query binding | Fast tests and PostgreSQL catalogue integration |
| Search, provider and publication-date filtering | Fast tests and PostgreSQL catalogue integration |
| Newest and oldest stable sorting | Fast tests and PostgreSQL catalogue integration |
| Missing, restricted, and expired record protection | Fast tests and PostgreSQL catalogue integration |
| Invalid parameter and cursor handling | `test_article_catalogue.py` |
| Parameterised handling of SQL-injection-like text | Fast tests and PostgreSQL catalogue integration |
| Controlled database failure response | `test_article_catalogue.py` |
| OpenAPI parameters, security, schemas, and responses | `test_article_catalogue.py` |

Run the focused NFA-34 tests from `apps/api`:

```bash
pytest tests/test_article_catalogue.py
```

## NFA-35 ingestion observability coverage

| Requirement | Automated evidence |
|---|---|
| Structured start, request, retry, completion, partial, and failure events | `test_article_sync.py` and `test_ingestion_observability.py` |
| Safe job IDs, counts, timings, categories, and stages | Sync and observability unit tests |
| Credential redaction and structured-field allowlist | `test_ingestion_observability.py` |
| Provider request and total job duration | `test_article_sync.py` and observability service tests |
| Job and article aggregate metrics | `test_ingestion_observability.py` |
| Provider and database failure tracking | `test_ingestion_observability.py` |
| Repeated failure, stale success, long runtime, and rejection thresholds | `test_ingestion_observability.py` |
| Protected recent-job, detail, metrics, and health APIs | `test_admin_ingestion_observability.py` |
| Observability settings and safe defaults | `test_config.py` |
| Versioned columns, constraints, indexes, rollback, and rebuild | `test_migrations_integration.py` |

Run the focused NFA-35 tests from `apps/api`:

```bash
pytest tests/test_article_sync.py \
  tests/test_ingestion_observability.py \
  tests/test_admin_ingestion_observability.py
```

## NFA-36 complete article pipeline coverage

| Requirement | Automated evidence |
|---|---|
| Reusable valid, invalid, missing-field, update, and duplicate fixtures | `tests/fixtures`, `tests/support/article_pipeline.py`, and `test_article_pipeline_fixtures.py` |
| Provider, normalisation, identity, rights, sync, and API unit coverage | Existing focused backend suites plus `test_article_sync.py` timeout coverage |
| Complete provider-to-PostgreSQL-to-REST workflow | `test_catalogue_pipeline_e2e.py` |
| Valid insert, permitted update, duplicate, repeat, and concurrent ingestion | Fixture tests and PostgreSQL end-to-end tests |
| Invalid record and database failure safety | PostgreSQL end-to-end tests |
| Provenance, rights, restricted AI use, and public-only API fields | PostgreSQL end-to-end tests |
| Manual authentication and source-authorisation enforcement | End-to-end test plus `test_admin_article_sync.py` |
| Schedule, timeout, checkpoint, interruption, and recovery policy | `test_article_sync.py` |
| Accurate statistics, metrics, structured job logs, and redaction | End-to-end test and observability suites |
| Live CNN remains inaccessible | CNN adapter tests and the end-to-end disabled-source assertion |

The full strategy, exact disposable-database command, results, and limitations are recorded in [the NFA-36 pipeline testing guide](article-pipeline-testing.md).

## Run the normal backend suite

Activate the backend virtual environment, then run from `apps/api`:

```bash
ruff check .
ruff format --check .
pytest --cov=app --cov-report=term-missing --cov-fail-under=75
```

Run only the NFA-26 security regression tests:

```bash
pytest tests/test_account_security_regression.py
```

Normal tests do not need PostgreSQL, Docker, an OpenAI key, live news content, real user information, or production credentials. External services are not contacted.

## Run the frontend authentication suite

Run from `apps/web`:

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

## Run the PostgreSQL account-security proof

This test deletes and rebuilds its target database schema. Create a separate disposable database whose name contains `newsflow_account_security_test`. Never use the normal `newsflow` development database, a shared database, staging, or production.

From `apps/api`:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_account_security_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_account_security_integration.py
```

The test proves against real PostgreSQL that:

- An owner can read their saved content.
- A second user receives no item in their collection.
- The second user cannot read, update, delete, export, or re-save the owner's content.
- Cross-user failures expose no private content.
- The protected database record remains owned, unchanged, and not deleted.

The other disposable database commands remain documented in the backend and local development guides.

## Run the PostgreSQL synchronisation proof

Create a separate disposable database whose name contains `newsflow_article_sync_test`. Never use the normal development, shared, staging, or production database.

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_article_sync_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_article_sync_integration.py
```

## Run the PostgreSQL article catalogue proof

Create a separate disposable database whose name contains `newsflow_article_catalogue_test`. Never use the normal development, shared, staging, or production database.

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_article_catalogue_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_article_catalogue_integration.py
```

## GitHub quality checks

When a pull request is opened or a commit reaches `main`, `.github/workflows/quality.yml` runs two independent jobs:

- Backend: start an isolated PostgreSQL 16 service, install Python dependencies, lint, check formatting, run Pytest with a 75 percent coverage floor, and run the NFA-36 pipeline suite against `newsflow_pipeline_test`.
- Frontend: install locked npm dependencies, lint, check formatting, check TypeScript, run Vitest, and build Next.js.

The NFA-36 workflow step receives test-only credentials and reset permission only for the short-lived `newsflow_pipeline_test` service database. Other destructive PostgreSQL modules keep their separate safety-gated database names and remain opt-in.

Do not add real credentials to workflow files. The committed workflow values are disposable CI-only values and must never be reused outside that isolated job.

## Verification record

Verified locally on 29 October 2026:

- Backend linting and formatting passed.
- The normal backend run passed 169 tests and safely skipped 11 opt-in PostgreSQL tests.
- Backend branch-aware coverage measured 77 percent, above the enforced 75 percent floor.
- The isolated NFA-36 PostgreSQL pipeline suite passed 3 tests.
- Each NFA-36 test applied all migrations through `20261029_0006` and rolled the disposable schema back afterwards.
- No test used live CNN content, real user data, or production credentials.

## Review status

- Jira issue: NFA-36
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
