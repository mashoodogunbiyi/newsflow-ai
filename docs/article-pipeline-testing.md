# NFA-36 Article Pipeline Test Strategy and Results

## Purpose

NFA-36 verifies that authorised article information can travel safely through the complete NewsFlow AI ingestion and catalogue pipeline. The tests cover the provider contract, normalisation, identity and deduplication, PostgreSQL persistence, provenance, rights, synchronisation, observability, and authenticated REST catalogue.

All provider records in this suite are original synthetic fixtures. The suite does not connect to CNN or any other live news provider.

## Pipeline under test

```text
Synthetic fixture provider
        |
        v
Normalisation and validation
        |
        v
Identity and deduplication
        |
        v
PostgreSQL articles and snapshots
        |
        +----> Provenance events
        |
        +----> Versioned rights
        |
        v
Synchronisation jobs, checkpoints, metrics, and logs
        |
        v
Authenticated article list and detail REST endpoints
```

## Test strategy

| Layer | Evidence | Purpose |
|---|---|---|
| Unit | `test_article_normalisation.py`, `test_article_identity.py`, `test_article_deduplication.py`, `test_article_rights.py`, `test_article_sync.py` | Check field validation, identity, rights decisions, retries, checkpoints, recovery, and statistics without external services. |
| API | `test_admin_article_sync.py`, `test_article_catalogue.py`, `test_admin_ingestion_observability.py` | Check authentication, administrator authorisation, CSRF, safe responses, public fields, filters, metrics, and health endpoints. |
| Fixture contract | `test_article_pipeline_fixtures.py` | Check the reusable valid, invalid, duplicate, update, and missing-optional-field records. |
| PostgreSQL integration and end-to-end | `test_catalogue_pipeline_e2e.py` | Run the real synthetic provider-to-REST workflow against an isolated migrated PostgreSQL database. |
| Continuous integration | `.github/workflows/quality.yml` | Run the fast backend suite with a 75 percent coverage floor and run the NFA-36 PostgreSQL pipeline suite in GitHub Actions. |

## Synthetic fixture library

The reusable files are:

- `apps/api/tests/fixtures/synthetic_articles.json`
- `apps/api/tests/fixtures/invalid_articles.json`
- `apps/api/tests/support/article_pipeline.py`

The fixture groups cover:

- Three valid fictional articles.
- A missing optional description.
- An existing article with updated permitted metadata.
- Repeated records with the same stable identity.
- A record used for controlled database failure testing.
- Missing title, invalid URL, invalid date, missing permitted content, and unsafe markup.

Every fixture uses the reserved `example.invalid` domain. Every fixture identifier starts with `fixture-`, as required by the source contract. No fixture contains CNN content, real personal information, credentials, or a usable account password.

## Isolated PostgreSQL environment

The end-to-end suite refuses to run unless both safety conditions are met:

1. `TEST_DATABASE_URL` contains the exact disposable database name `newsflow_pipeline_test`.
2. `ALLOW_DATABASE_RESET_FOR_TESTS` is explicitly set to `true`.

The fixture migrates that database from `base` to `head` before each test and returns it to `base` afterwards. It never uses the normal `newsflow` development database.

When PostgreSQL is running through this repository's Docker Compose stack, create the disposable database from the repository root:

```bash
docker compose exec database sh -lc 'createdb -U "$POSTGRES_USER" newsflow_pipeline_test'
```

Run the pipeline suite from `apps/api`, replacing the placeholders with local test-only credentials:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_pipeline_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
.venv/bin/pytest -m integration tests/test_catalogue_pipeline_e2e.py
```

Remove only the disposable database when testing is complete:

```bash
docker compose exec database sh -lc 'dropdb -U "$POSTGRES_USER" --if-exists newsflow_pipeline_test'
```

Never run the reset-enabled command against development, shared, staging, or production data.

## End-to-end assertions

The PostgreSQL suite proves that:

- An authenticated administrator can trigger manual synchronisation with the required CSRF token.
- Valid fixture records are normalised, stored, and returned through the list and detail endpoints.
- REST responses contain only the documented public article and attribution fields.
- An update changes the existing article without creating a second identity.
- Repeated and concurrent ingestion attempts do not create duplicate article or snapshot rows.
- Invalid data fails with a stable safe error and does not change article records.
- A simulated database failure does not change article records or advance the successful checkpoint.
- Article provenance and verified rights metadata are persisted.
- An article whose current rights prohibit AI processing receives a fail-closed denial.
- Synchronisation counts, provider attempts, failure categories, metrics, and checkpoints match the database results.
- Structured logs include the event and job identifier while excluding simulated credentials and restricted fixture content.
- A disabled source profile blocks the job before the provider is called.

Scheduled synchronisation, stale-job recovery, timeout retries, unauthorised manual triggers, and interrupted-job policy are exercised in the fast service and route suites. Both scheduled and manual entry points use the same `ArticleSyncService` workflow tested end to end here.

## Automation and coverage

Install the development tools from `apps/api`:

```bash
python -m pip install -e ".[dev]"
```

Run the normal backend checks:

```bash
ruff check .
ruff format --check .
pytest --cov=app --cov-report=term-missing --cov-fail-under=75
```

The coverage configuration measures branches and statements in `app`. The 75 percent minimum is an enforced project floor, not a claim that every behaviour is covered. Security-critical and pipeline behaviour also has explicit scenario assertions even when a line is already exercised by another test.

GitHub Actions uses a short-lived PostgreSQL 16 service with test-only credentials. It runs the normal coverage command first, then runs only `test_catalogue_pipeline_e2e.py` with the destructive reset flag and exact disposable database name.

## Verified results

Verified locally on 29 October 2026:

- Backend Ruff lint and format checks passed.
- Normal backend suite: 169 passed and 11 safety-gated PostgreSQL tests skipped.
- Measured backend coverage: 77 percent with branch coverage enabled.
- NFA-36 isolated PostgreSQL suite: 3 passed.
- Current database schema: all migrations through `20261029_0007` applied for each test and rolled back afterwards.
- Live CNN requests made: 0.
- Real news content, production credentials, and real personal data used: 0.

## Limitations and unresolved defects

- Live CNN integration remains blocked by NFA-8. NFA-36 proves the pipeline through synthetic provider records only.
- Eight older PostgreSQL integration modules retain their own deliberately different disposable database names and are not all run by the single NFA-36 database command.
- The suite does not perform production load, long-duration scheduler, network partition, deployment, external log destination, or alert-delivery testing.
- The pipeline tests do not call the OpenAI API because article-to-post generation is outside NFA-36.
- No unresolved defect was observed in the implemented NFA-36 scenarios after the final local run.

## Review status

- Jira issue: NFA-36
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
