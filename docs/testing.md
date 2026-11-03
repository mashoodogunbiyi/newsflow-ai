# NewsFlow AI Testing Guide

## Purpose

This guide records the automated test strategy for account security, the provider-to-database article workflow, and the backend AI boundary, including NFA-33 synchronisation, the NFA-34 article catalogue REST API, NFA-35 ingestion observability, the NFA-36 complete synthetic pipeline suite, the mocked NFA-38 OpenAI integration, NFA-39 grounded prompt construction, NFA-40 private LinkedIn draft generation, the NFA-41 frontend-facing generation REST API, NFA-42 deterministic factual-grounding validation, NFA-43 generation operations, the NFA-44 AI evaluation and regression framework, NFA-45 generation monitoring and audit, the NFA-46 joined E4 acceptance workflow, NFA-48 safe image-prompt composition, NFA-49 sensitive-news image safety, the mocked NFA-50 OpenAI image boundary, NFA-51 secure image validation and storage, NFA-52 immutable regeneration, NFA-53 private delivery, the NFA-54 complete E5 image-workflow suite, the NFA-61 reusable frontend generation lifecycle, the NFA-62 LinkedIn draft editor, the NFA-63 combined content preview, the NFA-64 image generation controls, the NFA-65 responsive and accessibility review, and the NFA-73 joined saved-content lifecycle.

The test suite is designed to detect security regressions before a pull request is merged. It uses only synthetic users, passwords, sessions, and content.

## Test layers

| Layer                             | Location                                                                                    | Purpose                                                                                                                                                                                                            |
| --------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Backend unit and API tests        | `apps/api/tests/test_*.py`                                                                  | Fast tests for accounts, providers, articles, rights, synchronisation, catalogue endpoints, OpenAI integration, grounded prompts, generation orchestration, CSRF, safe errors, and authorisation.                  |
| Account-security regression tests | `apps/api/tests/test_account_security_regression.py`                                        | One integrated in-memory journey from registration through private-content access and logout.                                                                                                                      |
| PostgreSQL integration tests      | `apps/api/tests/*_integration.py`                                                           | Opt-in verification of migrations, constraints, accounts, ownership, article ingestion, provenance, rights, synchronisation, and catalogue queries.                                                                |
| Frontend interface tests          | `apps/web/__tests__`                                                                        | Registration, login, logout, session restoration, workspace protection, responsive navigation state, reusable UI, generation transitions, draft editing, private image preview, loading, and safe error behaviour. |
| Complete article pipeline         | `apps/api/tests/test_catalogue_pipeline_e2e.py`                                             | Safety-gated synthetic provider-to-PostgreSQL-to-REST verification, including failure, rights, logs, and concurrent ingestion.                                                                                     |
| Pull-request quality checks       | `.github/workflows/quality.yml`                                                             | Runs backend and frontend quality checks, enforces backend coverage, and runs isolated NFA-36 and NFA-54 PostgreSQL suites on GitHub.                                                                              |
| AI generation evaluation          | `apps/api/tests/evaluation`                                                                 | Uses synthetic articles and mocked outputs to score generation properties and detect prompt regressions without external requests.                                                                                 |
| Generation monitoring and audit   | `apps/api/tests/test_generation_audit.py` and `test_admin_generation_monitoring.py`         | Checks lifecycle correlation, duration, metrics, token aggregation, retention, safe records, and administrator-only inspection.                                                                                    |
| Complete E5 image workflow        | `apps/api/tests/test_image_workflow_acceptance.py` and `test_image_workflow_integration.py` | Joins the mocked prompt-to-provider-to-storage-to-delivery path, regeneration, PostgreSQL metadata, versioning, and owner isolation.                                                                               |

## NFA-26 coverage

| Requirement                                                       | Automated evidence                                                                     |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Successful and invalid registration                               | `test_registration.py` and the account-security regression suite                       |
| Duplicate registration                                            | `test_registration.py`, PostgreSQL registration integration, and regression suite      |
| Argon2id password hashing                                         | `test_passwords.py`, registration tests, and regression suite                          |
| Successful and failed login                                       | `test_authentication.py` and regression suite                                          |
| Session creation and secure cookies                               | `test_authentication.py` and PostgreSQL authentication integration                     |
| Session expiry, logout, and reuse prevention                      | Authentication tests and regression suite                                              |
| Unauthenticated protected access                                  | Authentication, authorisation, and regression tests                                    |
| Cross-user read, update, delete, export, and collection filtering | `test_authorization.py`, regression suite, and PostgreSQL account-security integration |
| Client-supplied owner manipulation                                | Authorisation and regression tests                                                     |
| Sensitive response exclusion                                      | Registration, authentication, authorisation, and regression tests                      |
| Frontend authentication behaviour                                 | Vitest tests in `apps/web/__tests__`                                                   |
| Automated quality process                                         | GitHub Actions quality workflow                                                        |

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

| Requirement                                              | Automated evidence                                     |
| -------------------------------------------------------- | ------------------------------------------------------ |
| Scheduled and manual workflows share one service         | `test_article_sync.py`                                 |
| Administrator-only manual trigger and CSRF dependency    | `test_admin_article_sync.py`                           |
| Manual request throttling                                | `test_admin_article_sync.py`                           |
| Pagination, statistics, and incremental checkpoint       | `test_article_sync.py` and PostgreSQL sync integration |
| Duplicate article and active-job prevention              | Sync unit tests and PostgreSQL sync integration        |
| Temporary retry and permanent failure policy             | `test_article_sync.py`                                 |
| Partial failure does not advance the checkpoint          | `test_article_sync.py`                                 |
| Expired worker recovery                                  | `test_article_sync.py`                                 |
| Live CNN remains disabled                                | Existing CNN adapter tests and source-profile checks   |
| Real jobs, articles, provenance, rights, and checkpoints | `test_article_sync_integration.py`                     |

Run the fast NFA-33 tests from `apps/api`:

```bash
pytest tests/test_article_sync.py tests/test_admin_article_sync.py
```

## NFA-34 article catalogue coverage

| Requirement                                          | Automated evidence                              |
| ---------------------------------------------------- | ----------------------------------------------- |
| Authenticated list and detail endpoints              | `test_article_catalogue.py`                     |
| Public response schema and internal-field exclusion  | `test_article_catalogue.py`                     |
| Cursor pagination and query binding                  | Fast tests and PostgreSQL catalogue integration |
| Search, provider and publication-date filtering      | Fast tests and PostgreSQL catalogue integration |
| Newest and oldest stable sorting                     | Fast tests and PostgreSQL catalogue integration |
| Missing, restricted, and expired record protection   | Fast tests and PostgreSQL catalogue integration |
| Invalid parameter and cursor handling                | `test_article_catalogue.py`                     |
| Parameterised handling of SQL-injection-like text    | Fast tests and PostgreSQL catalogue integration |
| Controlled database failure response                 | `test_article_catalogue.py`                     |
| OpenAPI parameters, security, schemas, and responses | `test_article_catalogue.py`                     |

Run the focused NFA-34 tests from `apps/api`:

```bash
pytest tests/test_article_catalogue.py
```

## NFA-35 ingestion observability coverage

| Requirement                                                               | Automated evidence                                           |
| ------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Structured start, request, retry, completion, partial, and failure events | `test_article_sync.py` and `test_ingestion_observability.py` |
| Safe job IDs, counts, timings, categories, and stages                     | Sync and observability unit tests                            |
| Credential redaction and structured-field allowlist                       | `test_ingestion_observability.py`                            |
| Provider request and total job duration                                   | `test_article_sync.py` and observability service tests       |
| Job and article aggregate metrics                                         | `test_ingestion_observability.py`                            |
| Provider and database failure tracking                                    | `test_ingestion_observability.py`                            |
| Repeated failure, stale success, long runtime, and rejection thresholds   | `test_ingestion_observability.py`                            |
| Protected recent-job, detail, metrics, and health APIs                    | `test_admin_ingestion_observability.py`                      |
| Observability settings and safe defaults                                  | `test_config.py`                                             |
| Versioned columns, constraints, indexes, rollback, and rebuild            | `test_migrations_integration.py`                             |

Run the focused NFA-35 tests from `apps/api`:

```bash
pytest tests/test_article_sync.py \
  tests/test_ingestion_observability.py \
  tests/test_admin_ingestion_observability.py
```

## NFA-36 complete article pipeline coverage

| Requirement                                                                 | Automated evidence                                                                             |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Reusable valid, invalid, missing-field, update, and duplicate fixtures      | `tests/fixtures`, `tests/support/article_pipeline.py`, and `test_article_pipeline_fixtures.py` |
| Provider, normalisation, identity, rights, sync, and API unit coverage      | Existing focused backend suites plus `test_article_sync.py` timeout coverage                   |
| Complete provider-to-PostgreSQL-to-REST workflow                            | `test_catalogue_pipeline_e2e.py`                                                               |
| Valid insert, permitted update, duplicate, repeat, and concurrent ingestion | Fixture tests and PostgreSQL end-to-end tests                                                  |
| Invalid record and database failure safety                                  | PostgreSQL end-to-end tests                                                                    |
| Provenance, rights, restricted AI use, and public-only API fields           | PostgreSQL end-to-end tests                                                                    |
| Manual authentication and source-authorisation enforcement                  | End-to-end test plus `test_admin_article_sync.py`                                              |
| Schedule, timeout, checkpoint, interruption, and recovery policy            | `test_article_sync.py`                                                                         |
| Accurate statistics, metrics, structured job logs, and redaction            | End-to-end test and observability suites                                                       |
| Live CNN remains inaccessible                                               | CNN adapter tests and the end-to-end disabled-source assertion                                 |

The full strategy, exact disposable-database command, results, and limitations are recorded in [the NFA-36 pipeline testing guide](article-pipeline-testing.md).

## NFA-38 OpenAI integration coverage

| Requirement                                                 | Automated evidence                             |
| ----------------------------------------------------------- | ---------------------------------------------- |
| Successful structured generation result                     | `test_openai_service.py`                       |
| Official SDK client configuration                           | `test_openai_service.py`                       |
| Missing key and model handling                              | `test_config.py` and `test_openai_service.py`  |
| Configurable timeout, output cap, and retry budget          | `test_config.py` and `test_openai_service.py`  |
| Authentication, rate-limit, timeout, and unavailable errors | `test_openai_service.py`                       |
| Incomplete and empty response handling                      | `test_openai_service.py`                       |
| Token-usage capture and missing usage                       | `test_openai_service.py`                       |
| Prompt, credential, and provider-detail log protection      | `test_openai_service.py`                       |
| No live or billable request                                 | Fake SDK client injected by every service test |

Run the focused NFA-38 tests from `apps/api`:

```bash
pytest tests/test_config.py tests/test_openai_service.py
```

The tests construct real OpenAI SDK exception types around synthetic HTTP responses, but all generation responses and client behaviour are mocked. No test reads a real API key or contacts OpenAI.

## NFA-39 LinkedIn prompt coverage

| Requirement                                                                    | Automated evidence                                                       |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| Professional, conversational, and analytical tones                             | `test_prompt_builder.py`                                                 |
| Short, medium, and long word and token limits                                  | `test_prompt_builder.py`                                                 |
| Exact permitted source-field allowlist                                         | `test_prompt_builder.py`                                                 |
| Higher-priority instructions separated from untrusted source data              | `test_prompt_builder.py`                                                 |
| Unsupported facts, statistics, quotations, names, dates, and events prohibited | `test_prompt_builder.py`                                                 |
| Exact article reference kept outside generated prose                           | `test_prompt_builder.py`                                                 |
| Title-only and missing information declined                                    | `test_prompt_builder.py`                                                 |
| Restricted and denied-rights content rejected                                  | `test_prompt_builder.py`                                                 |
| Injection text remains untrusted data                                          | `test_prompt_builder.py`                                                 |
| Invalid preferences and extra fields rejected                                  | `test_prompt_builder.py`                                                 |
| Prompt version and masked request representation                               | `test_prompt_builder.py`                                                 |
| Versioned supported and forbidden factual claims                               | `fixtures/linkedin_prompt_evaluations.json` and `test_prompt_builder.py` |

Run the focused NFA-39 tests from `apps/api`:

```bash
pytest tests/test_prompt_builder.py
```

The tests construct prompts from original synthetic fixture data. They do not call OpenAI, use a real credential, or evaluate live CNN information.

## NFA-40 LinkedIn generation coverage

| Requirement                                                                | Automated evidence                                                 |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Article, rights, prompt, OpenAI, validation, and persistence orchestration | `test_linkedin_generation_service.py`                              |
| Authentication and validated tone and length input                         | `test_linkedin_generation_api.py`                                  |
| Missing article and denied or missing rights                               | `test_linkedin_generation_service.py`                              |
| Insufficient permitted source information                                  | `test_linkedin_generation_service.py`                              |
| Strict Responses API JSON Schema forwarding                                | `test_openai_service.py` and `test_linkedin_generation_service.py` |
| Empty, malformed, contradictory, and out-of-range output rejection         | `test_linkedin_generation_service.py`                              |
| OpenAI timeout and safe failure handling                                   | Service and API tests                                              |
| Per-user rate limit and retry delay                                        | `test_linkedin_generation_api.py`                                  |
| Idempotent completed requests                                              | `test_linkedin_generation_service.py`                              |
| Exact source and rights-version preservation                               | `test_linkedin_generation_service.py`                              |
| Owner-only private draft retrieval                                         | `test_linkedin_generation_service.py`                              |
| Human review and no automatic publication                                  | Service and API response tests                                     |

Run the focused NFA-40 tests from `apps/api`:

```bash
pytest tests/test_openai_service.py \
  tests/test_prompt_builder.py \
  tests/test_linkedin_generation_service.py \
  tests/test_linkedin_generation_api.py
```

The OpenAI client, model result, article, rights decision, and users are synthetic. No focused or normal test makes a live OpenAI request, accesses live CNN information, or requires a real credential.

## NFA-41 generation REST API coverage

| Requirement                                                    | Automated evidence                                          |
| -------------------------------------------------------------- | ----------------------------------------------------------- |
| `POST /api/generations` and 201 response                       | `test_generation_api.py`                                    |
| Authentication and CSRF enforcement                            | `test_generation_api.py` plus existing authentication tests |
| Article UUID, tone, length, extra-field, and header validation | `test_generation_api.py`                                    |
| Authenticated user identity passed to the service              | `test_generation_api.py`                                    |
| NFA-40 service reuse and pre-provider rights enforcement       | Generation API and NFA-40 service tests                     |
| Minimal response and internal-field exclusion                  | `test_generation_api.py`                                    |
| Missing, restricted, and insufficient articles                 | API and NFA-40 service tests                                |
| Safe 502, 503, and 504 provider failures                       | `test_generation_api.py`                                    |
| Per-user rate limit and retry delay                            | `test_generation_api.py`                                    |
| Idempotency header validation and delegation                   | `test_generation_api.py`                                    |
| OpenAPI request, response, security, and error documentation   | `test_generation_api.py`                                    |

Run the focused NFA-41 tests from `apps/api`:

```bash
pytest tests/test_generation_api.py \
  tests/test_linkedin_generation_api.py \
  tests/test_linkedin_generation_service.py
```

These tests use synthetic records and provider doubles. They make no live OpenAI request and do not use live CNN information.

## NFA-42 factual-grounding coverage

| Requirement                                                 | Automated evidence                                                       |
| ----------------------------------------------------------- | ------------------------------------------------------------------------ |
| Strict structured output and empty-result rejection         | `test_generation_validator.py` and `test_linkedin_generation_service.py` |
| Trusted article ID and canonical URL                        | `test_generation_validator.py`                                           |
| Unsupported numbers and quotations                          | `test_generation_validator.py`                                           |
| Named entities and low-support factual assertions           | `test_generation_validator.py`                                           |
| Clearly framed commentary distinguished from factual claims | `test_generation_validator.py`                                           |
| Insufficient permitted context                              | `test_generation_validator.py` and prompt-builder tests                  |
| Safe warning text without source or claim excerpts          | `test_generation_validator.py`                                           |
| Blocking result rejected before persistence                 | `test_linkedin_generation_service.py`                                    |
| Grounding status and warnings in API responses              | Generation API tests                                                     |
| Grounding migration fields and index                        | `test_migrations_integration.py`                                         |

Run the focused NFA-42 tests from `apps/api`:

```bash
pytest tests/test_generation_validator.py \
  tests/test_linkedin_generation_service.py \
  tests/test_generation_api.py \
  tests/test_linkedin_generation_api.py
```

All grounding fixtures are original synthetic records. The validator does not call a second model, make network requests, retrieve restricted text, or log article and draft excerpts.

## NFA-43 generation operations coverage

| Requirement                                                                                              | Automated evidence                                                         |
| -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Configurable daily, concurrent, lease, retention, timeout, retry, and token controls                     | `test_config.py`, `test_generation_usage.py`, and `test_openai_service.py` |
| Shared daily and concurrent enforcement                                                                  | `test_generation_usage_integration.py` against safety-gated PostgreSQL     |
| Active duplicate protection                                                                              | Generation usage unit and PostgreSQL integration tests                     |
| Successful status and available token recording                                                          | `test_generation_usage.py` and `test_linkedin_generation_service.py`       |
| Failed status and safe category recording                                                                | Generation usage, OpenAI service, and LinkedIn generation tests            |
| Authentication before provider use                                                                       | Generation API authentication tests                                        |
| Safe HTTP errors and retry headers                                                                       | `test_generation_api.py` and `test_linkedin_generation_api.py`             |
| OpenAI authentication, temporary rate limit, quota, timeout, availability, and invalid-response handling | `test_openai_service.py`                                                   |
| Sensitive prompt, content, credential, and provider-detail protection                                    | OpenAI service, generation usage, and API tests                            |
| Migration fields, constraints, indexes, upgrade, and rollback                                            | `test_migrations_integration.py`                                           |

Run the normal focused NFA-43 tests from the repository root:

```bash
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_generation_usage.py \
  apps/api/tests/test_openai_service.py \
  apps/api/tests/test_linkedin_generation_service.py \
  apps/api/tests/test_generation_api.py \
  apps/api/tests/test_linkedin_generation_api.py \
  apps/api/tests/test_config.py
```

The real PostgreSQL test deletes and rebuilds only a deliberately named disposable database. Never point it at the normal development, shared, staging, or production database:

```bash
cd apps/api
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_generation_usage_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_generation_usage_integration.py
```

No NFA-43 test makes a live or billable OpenAI request. Provider responses, users, article information, and usage events are synthetic.

## NFA-44 AI evaluation and regression coverage

| Requirement                                                                 | Automated evidence                                                                                 |
| --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Reusable synthetic article dataset                                          | `fixtures/evaluation_articles.json` and its schema-validation tests                                |
| Mocked deterministic generation cases                                       | `fixtures/expected_generation_cases.json`                                                          |
| Structure, tone, length, and writing quality                                | `evaluation/test_generation_quality.py`                                                            |
| Grounding, numbers, quotations, source references, and insufficient context | `evaluation/test_grounding_and_safety.py`                                                          |
| Prompt injection and restricted information                                 | Evaluation safety tests plus prompt-builder and generation-service tests                           |
| Prompt-version comparison                                                   | `evaluation/test_prompt_regression.py`                                                             |
| Generation API failures and invalid preferences                             | `test_generation_api.py` and `test_linkedin_generation_api.py`                                     |
| Usage limits, concurrency, and duplicates                                   | `test_generation_usage.py` and the safety-gated PostgreSQL test                                    |
| Authentication, CSRF, rights, and authorisation                             | Generation API, service, prompt-builder, and ownership tests                                       |
| Optional live model remains separate                                        | `evaluation/test_live_model_evaluation.py` with the `live_ai` marker and explicit environment gate |

Run the complete deterministic NFA-44 evidence set from `apps/api`:

```bash
pytest tests/evaluation \
  tests/test_generation_api.py \
  tests/test_linkedin_generation_api.py \
  tests/test_linkedin_generation_service.py \
  tests/test_generation_usage.py \
  tests/test_openai_service.py
```

The optional live-model test is skipped unless `RUN_LIVE_AI_EVALUATION=true` is deliberately supplied. It can make a billable request. The GitHub workflow explicitly runs the backend suite with `-m "not live_ai"`, so CI cannot select it:

```bash
RUN_LIVE_AI_EVALUATION=true pytest -m live_ai -s \
  tests/evaluation/test_live_model_evaluation.py
```

See [the AI generation evaluation guide](ai-generation-evaluation.md) for scoring thresholds, regression procedure, live-test safeguards, and limitations.

## NFA-45 generation monitoring and audit coverage

| Requirement                                                                    | Automated evidence                                                   |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| Start, completion, and failure events                                          | `test_generation_audit.py` and `test_linkedin_generation_service.py` |
| Rights, validation, and usage-rejection events                                 | Audit service and generation workflow tests                          |
| Correlation identifier and duration                                            | `test_generation_audit.py`                                           |
| Success, failure, timeout, rate-limit, rejection, and average-duration metrics | `test_generation_audit.py`                                           |
| Available NFA-43 token totals                                                  | Monitoring aggregation test                                          |
| Safe fields and sensitive-data minimisation                                    | Audit redaction test                                                 |
| Administrator access and ordinary-user denial                                  | `test_admin_generation_monitoring.py`                                |
| Retention and configuration bounds                                             | Audit and configuration tests                                        |
| PostgreSQL table, columns, indexes, upgrade, and rollback                      | `test_migrations_integration.py`                                     |

Run the focused NFA-45 evidence set from the repository root:

```bash
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_generation_audit.py \
  apps/api/tests/test_admin_generation_monitoring.py \
  apps/api/tests/test_linkedin_generation_service.py \
  apps/api/tests/test_generation_api.py \
  apps/api/tests/test_linkedin_generation_api.py \
  apps/api/tests/test_config.py
```

The focused suite uses only synthetic IDs, article information, drafts, and provider outcomes. It does not contact CNN or OpenAI. See [the generation monitoring guide](generation-monitoring.md) for event definitions, protected endpoints, retention, failure investigation, and limitations.

## NFA-46 joined E4 acceptance coverage

`test_generation_workflow_acceptance.py` sends synthetic requests through the real FastAPI generation route and real generation orchestration. It uses the real article-rights service, prompt builder, grounding validator, usage calls, and generation audit service while replacing OpenAI and persistence with deterministic test doubles.

| Requirement                                             | Automated evidence                                                  |
| ------------------------------------------------------- | ------------------------------------------------------------------- |
| Successful authenticated HTTP-to-private-draft workflow | Complete success scenario and exact public response-field assertion |
| Session and CSRF enforcement                            | Missing-session and invalid-CSRF scenarios                          |
| Rights denied before provider access                    | Restricted-article scenario and zero OpenAI-call assertion          |
| Preference and source-context validation                | Invalid-enum and insufficient-context scenarios                     |
| Safe OpenAI and malformed-output failures               | Unavailable-provider and invalid-structured-output scenarios        |
| Shared usage rejection                                  | Limit-exceeded scenario, `Retry-After`, and zero provider access    |
| Trusted source reference and mandatory review           | Success response assertions                                         |
| Content-free correlated audit evidence                  | Recorded start, rights, validation, completion, and failure events  |
| Human control and no automatic publishing               | Draft status, review requirement, and route inspection              |

Run the focused NFA-46 evidence set from the repository root:

```bash
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_generation_workflow_acceptance.py \
  apps/api/tests/test_generation_api.py \
  apps/api/tests/test_linkedin_generation_service.py \
  apps/api/tests/test_generation_audit.py \
  apps/api/tests/test_admin_generation_monitoring.py \
  apps/api/tests/evaluation
```

The suite uses only original synthetic article content and mocked OpenAI output. It creates no live OpenAI request, retrieves no CNN content, and uses no real credential or personal information. See the [E4 acceptance record](e4-generation-acceptance.md) and [E4 architecture](architecture/ai-generation-architecture.md).

## NFA-48 image-prompt composer coverage

`test_image_prompt.py` verifies the internal image-prompt package without calling an image provider.

| Requirement                              | Automated evidence                                                                       |
| ---------------------------------------- | ---------------------------------------------------------------------------------------- |
| Valid structured prompt                  | Article-context result, version, reference, and review flags                             |
| Defined styles and composition           | Every style, aspect ratio, and composition mapping                                       |
| Strict parameters                        | Unsupported enums and extra free-text property rejection                                 |
| Current source rights                    | Allowed, denied, mismatched, incomplete-attribution, and restricted-content scenarios    |
| Permitted fields only                    | Exact article-context allowlist and excluded source metadata                             |
| Insufficient information                 | Safe rejection rather than invented visual details                                       |
| Article-or-draft context                 | Matching draft, missing draft, generation mismatch, validation rejection, and size bound |
| Prompt-injection separation              | Malicious synthetic content remains outside trusted instructions                         |
| Restricted photography and non-deception | Mandatory original-illustration and non-documentary rules                                |
| Version and safe representation          | `image_prompt_v1` and masked context fields                                              |

Run the focused NFA-48 checks from the repository root:

```bash
apps/api/.venv/bin/ruff check \
  apps/api/app/models/image_prompt.py \
  apps/api/app/prompts/image_illustration.py \
  apps/api/app/services/image_prompt.py \
  apps/api/tests/test_image_prompt.py
apps/api/.venv/bin/ruff format --check \
  apps/api/app/models/image_prompt.py \
  apps/api/app/prompts/image_illustration.py \
  apps/api/app/services/image_prompt.py \
  apps/api/tests/test_image_prompt.py
apps/api/.venv/bin/pytest -q apps/api/tests/test_image_prompt.py
```

The test data is original and synthetic. The suite makes no CNN or image-provider request, requires no API key, and uses no real personal information. See the [image-prompt composer guide](image-prompt-composer.md).

## NFA-49 sensitive-news image safety coverage

`test_image_safety.py` evaluates real NFA-48 prompt packages through the central NFA-49 service without calling an image provider.

| Requirement                    | Automated evidence                                                                             |
| ------------------------------ | ---------------------------------------------------------------------------------------------- |
| Ordinary topic                 | Allowed conceptual technology scenario                                                         |
| Sensitive categories           | Parameterised conflict, terrorism, disaster, injury, health, political, and criminal scenarios |
| Misleading documentary imagery | Conflict and disaster fabrication rejection                                                    |
| Conceptual alternative         | Sensitive requests restricted to conceptual, non-photorealistic treatment                      |
| Identifiable real person       | Sensitive person misrepresentation rejection                                                   |
| Frontend override prevention   | Extra safety fields rejected and text override denied                                          |
| Prompt injection               | Article instruction remains untrusted and cannot enable photorealism                           |
| Uncertain classification       | Conservative review-required provider gate                                                     |
| Provider safety                | Missing moderation blocks or pauses provider access                                            |
| Safe policy record             | Content-free recorder assertions                                                               |
| AI designation and review      | Required result fields in ordinary and sensitive decisions                                     |
| Provider call gate             | Allowed decisions continue; rejected and review-required decisions stop                        |

Run the focused NFA-49 checks from the repository root:

```bash
apps/api/.venv/bin/ruff check \
  apps/api/app/models/image_safety.py \
  apps/api/app/policies \
  apps/api/app/services/image_safety.py \
  apps/api/tests/test_image_safety.py
apps/api/.venv/bin/ruff format --check \
  apps/api/app/models/image_safety.py \
  apps/api/app/policies \
  apps/api/app/services/image_safety.py \
  apps/api/tests/test_image_safety.py
apps/api/.venv/bin/pytest -q apps/api/tests/test_image_safety.py
```

All scenarios use original synthetic topics and text. The suite makes no CNN, OpenAI, or image-provider request and stores no source or user text in decision records. See the [image safety policy](image-safety-policy.md).

## NFA-50 OpenAI image generation coverage

`test_openai_image_service.py` uses the official SDK exception classes and a mocked `client.images.generate` resource. It passes real NFA-48 and NFA-49 model structures into the NFA-50 provider boundary without making a network request.

| Requirement              | Automated evidence                                                                        |
| ------------------------ | ----------------------------------------------------------------------------------------- |
| Official SDK integration | Client factory receives backend key, timeout, and zero SDK retries                        |
| Successful generation    | Controlled request arguments, masked image bytes, metadata, and review state              |
| Missing credentials      | Safe settings error before client construction                                            |
| Safety enforcement       | Rejected safety decision stops before provider access                                     |
| Rights enforcement       | Denied or mismatched rights stop before provider access                                   |
| Supported settings       | Approved models, aspect-ratio sizes, quality enums, formats, and hashed safety identifier |
| Provider formats         | Strict Base64 image validation and masked HTTPS reference handling                        |
| Timeout                  | SDK and application deadline failures with no automatic replay                            |
| Authentication and quota | Safe permanent failures with no retry                                                     |
| Rate limiting            | One bounded mocked retry and exhausted-budget failure                                     |
| Temporary availability   | Controlled connection failure without ambiguous replay                                    |
| Moderation               | Generic provider moderation failure without sensitive category details                    |
| Invalid response         | Empty, malformed, wrong-signature, and unsafe-URL rejection                               |
| Duplicate protection     | Cached completion, active protection, and request-ID conflict handling                    |
| Usage tracking           | Available total, text, and image token counts plus missing-usage handling                 |
| Credential protection    | Logs and errors exclude key, prompt, provider detail, image data, and revised prompt      |
| Safe record              | Recorder receives content-free IDs, digest, dimensions, and usage only                    |

Run the focused NFA-50 checks from the repository root:

```bash
apps/api/.venv/bin/ruff check \
  apps/api/app/core/config.py \
  apps/api/app/core/image_generation_config.py \
  apps/api/app/models/image_generation.py \
  apps/api/app/services/openai_image_service.py \
  apps/api/tests/test_config.py \
  apps/api/tests/test_openai_image_service.py
apps/api/.venv/bin/ruff format --check \
  apps/api/app/core/config.py \
  apps/api/app/core/image_generation_config.py \
  apps/api/app/models/image_generation.py \
  apps/api/app/services/openai_image_service.py \
  apps/api/tests/test_config.py \
  apps/api/tests/test_openai_image_service.py
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_config.py \
  apps/api/tests/test_openai_image_service.py
```

No focused or normal NFA-50 test requires a real OpenAI key or spends provider credits. See the [OpenAI image generation integration guide](openai-image-generation.md).

## NFA-51 secure image storage coverage

NFA-51 uses synthetic locally generated pixels and a temporary private directory. The focused tests prove:

- content-based PNG detection, integrity checking, media-type matching, dimensions, size, and pixel controls;
- rejection of non-images, corrupt data, oversized data, and provider digest mismatches;
- removal of PNG comments and other unneeded source metadata through clean re-encoding;
- random private object keys, no public URL, restrictive local file permissions, and path isolation;
- owner, article, post, generation, model, prompt, policy, validation, review, and AI provenance metadata;
- idempotent request retries without a duplicate file;
- storage failure without false database success;
- database failure followed by object compensation deletion; and
- rejection of blocked output before file processing.

Run the focused set from the repository root:

```bash
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_config.py \
  apps/api/tests/test_image_validation.py \
  apps/api/tests/test_image_storage.py
```

The migration integration test verifies that `20261031_0011` applies to fresh PostgreSQL, exposes the required columns and indexes, survives the repeatable seed process, rolls back to `base`, and reapplies successfully. It is destructive and must use only the specifically named disposable database:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_migration_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
apps/api/.venv/bin/pytest -q apps/api/tests/test_migrations_integration.py
```

See the [secure generated-image storage guide](image-storage.md) for the validation, storage, database, idempotency, cleanup, and lifecycle design.

## NFA-52 image regeneration coverage

| Requirement                                                      | Automated evidence                                         |
| ---------------------------------------------------------------- | ---------------------------------------------------------- |
| Authentication, CSRF, and owner-scoped parent access             | `test_image_regeneration.py`                               |
| Current article and rights checks before provider access         | `test_image_regeneration.py`                               |
| Prompt and sensitive-news safety reapplied                       | Regeneration service tests                                 |
| New immutable image and parent-child version relationship        | Regeneration tests and NFA-54 joined workflow              |
| Original preserved on provider, validation, and storage failures | Regeneration tests and NFA-54 failed-regeneration scenario |
| Burst, daily, concurrent, and duplicate controls                 | `test_image_regeneration.py`                               |
| Safe response and error fields                                   | Regeneration API tests                                     |

Run the focused set from the repository root:

```bash
apps/api/.venv/bin/pytest -q apps/api/tests/test_image_regeneration.py
```

## NFA-53 secure image delivery coverage

| Requirement                                                   | Automated evidence               |
| ------------------------------------------------------------- | -------------------------------- |
| Owner-scoped metadata, content, and download access           | `test_image_delivery.py`         |
| Unauthenticated and cross-owner denial                        | Delivery and NFA-54 joined tests |
| Same missing response for absent and differently owned images | `test_image_delivery.py`         |
| Stored length and SHA-256 integrity verification              | `test_image_delivery.py`         |
| Approved MIME type and server-generated safe filename         | `test_image_delivery.py`         |
| Private no-store caching and security headers                 | `test_image_delivery.py`         |
| Missing, corrupt, and unavailable private objects             | `test_image_delivery.py`         |
| Storage key, path, credential, and unrestricted URL exclusion | Delivery response-schema tests   |

Run the focused set from the repository root:

```bash
apps/api/.venv/bin/pytest -q apps/api/tests/test_image_delivery.py
```

## NFA-54 complete E5 image workflow coverage

NFA-54 adds reusable synthetic article and image fixtures, a deterministic mocked OpenAI Images client, a joined prompt-to-delivery acceptance workflow, and an isolated PostgreSQL/private-storage proof.

| Requirement                                                                       | Automated evidence                                        |
| --------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Permitted prompt, safety, mocked provider, validation, storage, and delivery path | `test_image_workflow_acceptance.py`                       |
| Regeneration creates a child and preserves its parent                             | Joined acceptance workflow and PostgreSQL proof           |
| Rights and sensitive-news rejection before provider access                        | Joined acceptance workflow                                |
| Valid, invalid, corrupt, and oversized reusable files                             | `tests/support/image_workflow.py` and joined fixture test |
| Authentication and cross-owner access denial                                      | Joined acceptance and delivery tests                      |
| Failed regeneration leaves original available                                     | Joined acceptance workflow                                |
| Real migrations, PostgreSQL metadata, version sequence, and owner isolation       | `test_image_workflow_integration.py`                      |
| Temporary private storage and relative unpredictable keys                         | Joined tests and PostgreSQL proof                         |
| CI execution without live credentials                                             | `.github/workflows/quality.yml`                           |

Run the complete deterministic E5 set from the repository root:

```bash
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_image_prompt.py \
  apps/api/tests/test_image_safety.py \
  apps/api/tests/test_openai_image_service.py \
  apps/api/tests/test_image_validation.py \
  apps/api/tests/test_image_storage.py \
  apps/api/tests/test_image_regeneration.py \
  apps/api/tests/test_image_delivery.py \
  apps/api/tests/test_image_workflow_acceptance.py
```

The destructive integration fixture accepts only a URL containing `newsflow_image_pipeline_test` and explicit reset permission:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_image_pipeline_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
apps/api/.venv/bin/pytest -q -m integration \
  apps/api/tests/test_image_workflow_integration.py
```

The complete strategy, matrix, results, isolation rules, and limitations are in [the E5 image testing guide](e5-image-testing.md).

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

Normal tests do not need PostgreSQL, Docker, an OpenAI key, live news content, real user information, or production credentials. OpenAI responses are mocked and external services are not contacted.

## NFA-56 frontend application shell coverage

| Requirement                                                     | Automated evidence                                              |
| --------------------------------------------------------------- | --------------------------------------------------------------- |
| Shared authenticated application layout                         | `workspace-layout.test.tsx` and `workspace-components.test.tsx` |
| Dashboard, Create Post, Content Library, and Account protection | `route-protection.test.ts`                                      |
| Server validation before private child rendering                | `workspace-layout.test.tsx`                                     |
| Active route and accessible navigation                          | `workspace-components.test.tsx`                                 |
| Mobile menu state and Escape-key operation                      | `workspace-components.test.tsx`                                 |
| Reusable buttons, inputs, cards, statuses, and loading feedback | `workspace-components.test.tsx`                                 |
| Safe error boundary and retry action                            | `workspace-components.test.tsx`                                 |
| Existing authentication, session, CSRF, and logout behavior     | Existing NFA-24 frontend tests                                  |
| Production route and TypeScript validation                      | `npm run build` and `npm run typecheck`                         |

See the [NFA-56 frontend layout guide](frontend-layout.md) for the route structure, component conventions, responsive behavior, accessibility rules, security boundary, results, and limitations.

## NFA-58 article filtering and browsing-state coverage

| Requirement                                                            | Automated evidence                                            |
| ---------------------------------------------------------------------- | ------------------------------------------------------------- |
| Approved category options and accessible native selection              | `article-filtering.test.tsx`                                  |
| URL category restoration and one catalogue request                     | `article-filtering.test.tsx`                                  |
| Category, search, and sort preservation                                | `article-filtering.test.tsx` and `article-dashboard.test.tsx` |
| Cursor removal when filters change                                     | `article-filtering.test.tsx`                                  |
| Invalid or duplicated category handling without a frontend API request | `article-filtering.test.tsx`                                  |
| Frontend category query validation                                     | `article-api.test.ts`                                         |
| FastAPI category validation and OpenAPI contract                       | `test_article_catalogue.py`                                   |
| Cursor rejection when category state changes                           | `test_article_catalogue.py`                                   |
| PostgreSQL category filtering before pagination                        | `test_article_catalogue_integration.py`                       |
| Production TypeScript and route validation                             | `npm run typecheck` and `npm run build`                       |

See the [NFA-58 article filtering guide](article-filtering.md) for the approved identifiers, URL-state flow, pagination rules, empty and invalid states, accessibility, results, and limitations.

## NFA-59 article selection and source-panel coverage

| Requirement                                                            | Automated evidence                                       |
| ---------------------------------------------------------------------- | -------------------------------------------------------- |
| UUID-only article selection URL                                        | `article-selection.test.tsx` and `article-card.test.tsx` |
| Authenticated detail retrieval and response validation                 | `article-api.test.ts`                                    |
| Title, provider, date, category, summary, attribution, and source link | `source-panel.test.tsx`                                  |
| Available, restricted, and insufficient generation states              | `source-panel.test.tsx` and `test_article_catalogue.py`  |
| Restricted continuation disabled                                       | `source-panel.test.tsx`                                  |
| Missing, invalid, duplicated, and inaccessible selection states        | `generate-page.test.tsx` and `test_article_catalogue.py` |
| HTML-like source values rendered as text                               | `source-panel.test.tsx`                                  |
| Responsive metadata layout and accessible structure                    | `source-panel.test.tsx`                                  |
| PostgreSQL current detail and readiness                                | `test_article_catalogue_integration.py`                  |
| Production TypeScript and route validation                             | `npm run typecheck` and `npm run build`                  |

See the [NFA-59 article selection guide](article-selection.md) for the detail contract, source panel, safe states, accessibility, security boundary, results, and limitations.

## NFA-60 LinkedIn generation controls coverage

| Requirement                                                               | Automated evidence                                          |
| ------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Professional and medium defaults with exact supported choices             | `generation-controls.test.tsx`                              |
| Tone, length, and article UUID in the request                             | `generation-controls.test.tsx`                              |
| CSRF proof and random idempotency header                                  | `generation-controls.test.tsx`                              |
| Missing, invalid, restricted, and insufficient source handling            | `generation-controls.test.tsx` and `generate-page.test.tsx` |
| Active loading state and synchronous duplicate prevention                 | `generation-controls.test.tsx`                              |
| Authentication recovery and usage-limit retry lock                        | `generation-controls.test.tsx`                              |
| Runtime-validated success and mandatory review receipt                    | `generation-controls.test.tsx` and `types/generation.ts`    |
| Native labelled radio groups, keyboard operation, live regions, and focus | `generation-controls.test.tsx`                              |
| Header and cookie allowlists plus safe gateway errors                     | `generation-proxy.test.ts`                                  |
| Available and restricted Create Post integration                          | `generate-page.test.tsx`                                    |
| Production TypeScript and route validation                                | `npm run typecheck` and `npm run build`                     |

See the [NFA-60 LinkedIn generation controls guide](linkedin-generation-controls.md) for the exact request contract, supported preferences, same-origin gateway, controlled states, security boundary, accessibility behaviour, tests, and limitations.

## NFA-61 reusable generation state coverage

| Requirement                                                     | Automated evidence                                             |
| --------------------------------------------------------------- | -------------------------------------------------------------- |
| Idle, submitting, processing, completed, and failed transitions | `generation-state.test.tsx`                                    |
| Slow synchronous operation remains in processing                | `generation-state.test.tsx`                                    |
| Network and provider-timeout failure handling                   | `generation-state.test.tsx` and `generation-controls.test.tsx` |
| Deliberate retry with preserved input                           | `generation-state.test.tsx`                                    |
| Synchronous duplicate-request lock                              | `generation-state.test.tsx` and `generation-controls.test.tsx` |
| Older response cannot replace current state                     | `generation-state.test.tsx`                                    |
| Text-specific and image-specific status feedback                | `generation-state.test.tsx`                                    |
| Usage-limit countdown prevents early retry                      | `generation-state.test.tsx` and `generation-controls.test.tsx` |
| Polite status and assertive failure announcements               | `generation-state.test.tsx`                                    |
| No unsupported cancellation action                              | `generation-state.test.tsx`                                    |
| Integrated Create Post behaviour                                | `generation-controls.test.tsx` and `generate-page.test.tsx`    |
| Production TypeScript and route validation                      | `npm run typecheck` and `npm run build`                        |

See the [NFA-61 frontend generation states guide](generation-states.md) for the lifecycle, retry policy, duplicate and stale-response controls, accessibility rules, tests, and current cancellation limitation.

## NFA-62 LinkedIn draft editor coverage

| Requirement                                              | Automated evidence                                            |
| -------------------------------------------------------- | ------------------------------------------------------------- |
| Generated draft and source reference loading             | `linkedin-editor.test.tsx` and `generation-controls.test.tsx` |
| Multiline editing and line-preserving preview            | `linkedin-editor.test.tsx`                                    |
| Character count and configured length guidance           | `linkedin-editor.test.tsx`                                    |
| Empty and missing draft states                           | `linkedin-editor.test.tsx`                                    |
| Grounding warnings preserved after editing               | `linkedin-editor.test.tsx`                                    |
| Normal rerenders preserve local text                     | `linkedin-editor.test.tsx`                                    |
| Newer generation cannot silently overwrite edits         | `linkedin-editor.test.tsx`                                    |
| Unsaved same-tab navigation confirmation                 | `linkedin-editor.test.tsx`                                    |
| HTML-like text rendered without executable markup        | `linkedin-editor.test.tsx`                                    |
| Native keyboard editing and accessible labels            | `linkedin-editor.test.tsx`                                    |
| Validated generation response integrated with the editor | `generation-controls.test.tsx`                                |
| Production TypeScript and route validation               | `npm run typecheck` and `npm run build`                       |

See the [NFA-62 LinkedIn draft editor guide](linkedin-draft-editor.md) for the editor state, local preview, overwrite protection, navigation warning, source and warning rules, security, accessibility, tests, and E7 boundary.

## NFA-63 LinkedIn-inspired content preview coverage

| Requirement                                        | Automated evidence                                         |
| -------------------------------------------------- | ---------------------------------------------------------- |
| Current edited text and paragraph preservation     | `linkedin-preview.test.tsx` and `linkedin-editor.test.tsx` |
| Selected image and image-change synchronisation    | `linkedin-preview.test.tsx` and `linkedin-editor.test.tsx` |
| No-image, empty-draft, and missing-image states    | `linkedin-preview.test.tsx`                                |
| Source reference and HTTPS-only source link        | `linkedin-preview.test.tsx`                                |
| AI-generated illustration designation              | `linkedin-preview.test.tsx`                                |
| Review warnings remain visible                     | `linkedin-preview.test.tsx` and `linkedin-editor.test.tsx` |
| HTML-like text remains non-executable              | `linkedin-preview.test.tsx` and `linkedin-editor.test.tsx` |
| Accessible image descriptions and status fallback  | `linkedin-preview.test.tsx`                                |
| Responsive fluid layout classes                    | `linkedin-preview.test.tsx`                                |
| Session-cookie-only protected image gateway        | `image-content-proxy.test.ts`                              |
| UUID, media-type, cache, and safe-failure controls | `image-content-proxy.test.ts`                              |
| Production TypeScript and route validation         | `npm run typecheck` and `npm run build`                    |

See the [NFA-63 LinkedIn content preview guide](linkedin-content-preview.md) for the component contract, protected delivery flow, safety rules, states, accessibility behaviour, tests, and limitations.

## NFA-64 image generation control coverage

| Requirement                                               | Automated evidence                                         |
| --------------------------------------------------------- | ---------------------------------------------------------- |
| Owner-scoped initial image generation                     | `test_image_regeneration.py`                               |
| Root image storage and initial idempotent replay          | `test_image_regeneration.py`                               |
| Cross-user draft non-disclosure                           | `test_image_regeneration.py`                               |
| Initial FastAPI contract and private cache policy         | `test_image_regeneration.py`                               |
| Browser validation, CSRF, idempotency, and safe errors    | `image-generation-api.test.ts`                             |
| Same-origin gateway cookie and header allowlist           | `image-generation-proxy.test.ts`                           |
| Generate, regenerate, retain original, and select version | `image-controls.test.tsx`                                  |
| Preserve edited draft during image operations             | `image-controls.test.tsx`                                  |
| Duplicate-click protection and truthful loading           | `image-controls.test.tsx`                                  |
| Existing editor and preview regressions                   | `linkedin-editor.test.tsx` and `linkedin-preview.test.tsx` |

See the [NFA-64 image generation controls guide](image-generation-controls.md) for the request flow, supported preferences, security boundary, immutable version behaviour, accessibility, tests, and limitations.

## NFA-65 responsive and accessibility review coverage

| Requirement                                                                              | Automated evidence                                                    |
| ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Homepage, authentication, shell, dashboard, source, editor, preview, and image semantics | `accessibility-audit.test.tsx` using axe-core                         |
| Reviewed WCAG AA normal-text contrast tokens                                             | `contrast-and-motion.test.ts`                                         |
| Reduced-motion animation and scrolling rules                                             | `contrast-and-motion.test.ts`                                         |
| Mobile-menu focus entry and Escape focus return                                          | `workspace-components.test.tsx`                                       |
| Invalid-field association and first-error focus                                          | `auth-interface.test.tsx`                                             |
| Mobile, tablet, and desktop layout contracts                                             | `responsive-review.test.tsx` and existing component tests             |
| Long identifier, draft, and preview wrapping                                             | `responsive-review.test.tsx`                                          |
| Labels, statuses, alerts, and image alternatives                                         | Axe audit plus generation, editor, preview, and image component tests |
| Production TypeScript and route validation                                               | `npm run typecheck` and `npm run build`                               |

See the [NFA-65 responsive and accessibility review](responsive-accessibility-review.md) for the viewport matrix, defect record, evidence, manual keyboard and VoiceOver checklist, limitations, and review decision.

## NFA-72 deletion and retention coverage

| Requirement                                           | Automated evidence                                          |
| ----------------------------------------------------- | ----------------------------------------------------------- |
| Authenticated, CSRF-protected owner deletion          | `test_content_deletion.py`                                  |
| Cross-user and missing-resource non-disclosure        | `test_content_deletion.py`                                  |
| Immediate unreferenced private-image cleanup          | `test_content_deletion.py`                                  |
| Storage-failure retry without restoring draft access  | `test_content_deletion.py`                                  |
| Bounded retention worker and final content redaction  | `test_content_deletion.py` and migration integration tests  |
| Explicit confirmation and cancellation                | `draft-deletion.test.tsx`                                   |
| Loading, controlled failure, and library confirmation | `draft-deletion.test.tsx`                                   |
| Session and CSRF-only same-origin gateway              | `draft-deletion-proxy.test.ts`                              |
| Invalid identifier rejected before backend contact    | `draft-deletion-proxy.test.ts`                              |
| Versioned tables, constraints, rollback, and rebuild  | `test_migrations_integration.py`                            |

See the [NFA-72 content deletion and retention guide](content-deletion-retention.md) for the lifecycle, retention periods, image-reference protection, retry policy, backup limitations, worker command, and recovery boundary.

## NFA-73 saved-content lifecycle coverage

| Requirement | Automated evidence |
| --- | --- |
| Joined save, replay, retrieve, list, edit, history, image download, delete, and retention journey | `test_saved_content_lifecycle_e2e.py` |
| Authentication, CSRF, owner isolation, image ownership, and history ownership | `test_saved_content_lifecycle_e2e.py` plus focused API tests |
| Duplicate saves, stale writes, stable pagination, and database constraints | Joined lifecycle and saved-draft repository tests |
| Current edited-text copy and private image download | `content-export.test.tsx` and private image delivery tests |
| Version review and restoration | Saved-draft history API tests and `version-history.test.tsx` |
| Explicit deletion, controlled failure, cleanup retry, and retention | `draft-deletion.test.tsx`, content deletion tests, and joined lifecycle |
| Disposable database, synthetic data, and CI enforcement | E7 strategy document and `quality.yml` |

See the [NFA-73 saved-content lifecycle testing guide](saved-content-lifecycle-testing.md) for the complete coverage matrix, isolation rules, commands, expected failures, and limitations.

## Run the frontend suite

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

- Backend: start an isolated PostgreSQL 16 service, install Python dependencies, lint, check formatting, run Pytest with a 75 percent coverage floor, run the NFA-36 pipeline suite against `newsflow_pipeline_test`, run the NFA-58 catalogue proof against `newsflow_article_catalogue_test`, run the NFA-54 image-workflow proof against `newsflow_image_pipeline_test`, and run the NFA-67 and NFA-68 saved-draft and content-library proof against `newsflow_saved_draft_test`.
- Frontend: install locked npm dependencies, lint, check formatting, check TypeScript, run Vitest, and build Next.js.

The NFA-36, NFA-58, NFA-54, NFA-67, and NFA-68 workflow steps receive test-only credentials and reset permission only for their short-lived service databases. Other destructive PostgreSQL modules keep their separate safety-gated database names and remain opt-in.

Do not add real credentials to workflow files. The committed workflow values are disposable CI-only values and must never be reused outside that isolated job.

## Verification record

Verified locally on 2 November 2026:

- Backend linting and formatting passed.
- The normal backend run passed 416 tests, safely skipped 13 opt-in PostgreSQL tests, and deselected the optional live-model test.
- Backend branch-aware coverage measured 81.08 percent, above the enforced 75 percent floor.
- The isolated NFA-36 PostgreSQL pipeline suite passed 3 tests.
- Each NFA-36 test applies all migrations through `20261031_0011` and rolls the disposable schema back afterwards.
- The focused NFA-38 configuration and OpenAI service run passed 27 tests.
- The focused NFA-39 prompt-builder run passed 18 tests.
- The focused NFA-40 generation run passed 44 tests.
- The focused NFA-41 and reused NFA-40 API and service run passed 37 tests.
- The focused NFA-42 validation, service, and API run passed 49 tests.
- The focused NFA-43 generation operations run passed 82 tests.
- The safety-gated NFA-43 PostgreSQL integration test passed against a disposable Docker database, then rolled the schema back.
- The focused NFA-44 evaluation and generation-control run passed 83 tests and safely skipped the deliberately gated live-model test.
- The focused NFA-45 monitoring, generation workflow, API, and configuration run passed 71 tests.
- The focused NFA-46 E4 acceptance set passed 79 tests and safely skipped the optional live-model test.
- The focused NFA-48 image-prompt composer run passed 23 tests.
- The focused NFA-49 sensitive-news image safety run passed 19 tests.
- The focused NFA-50 configuration and OpenAI image service run passed 44 tests.
- The focused NFA-51 configuration, validation, private storage, idempotency, and cleanup run passed 32 tests.
- The NFA-51 migration applied, rolled back, and reapplied successfully against the disposable `newsflow_migration_test` PostgreSQL database.
- The focused NFA-52 immutable-regeneration run passed 10 tests.
- The focused NFA-53 secure-delivery run passed 12 tests.
- The NFA-54 joined acceptance workflow passed 4 tests.
- The complete deterministic E5 image set passed 107 tests.
- The safety-gated NFA-54 PostgreSQL and temporary-private-storage proof passed 1 test against `newsflow_image_pipeline_test`, applied migrations through `20261031_0012`, and rolled the schema back afterwards.
- No test used live CNN content, a live OpenAI request, real user data, or production credentials.
- The focused NFA-58 backend article-catalogue run passed 10 tests.
- The NFA-58 frontend run passed all 47 tests across 11 files, plus ESLint, Prettier, TypeScript, route type generation, and the Next.js production build.
- The NFA-58 PostgreSQL test is safety-gated for the disposable `newsflow_article_catalogue_test` database and will run automatically in GitHub Actions after this branch is pushed.
- The focused NFA-59 backend article detail and readiness run passed 11 tests.
- The complete backend run after NFA-59 passed 417 tests, skipped 13 safety-gated tests, deselected the optional live-model test, and measured 81.15 percent coverage.
- The NFA-59 frontend run passed all 59 tests across 14 files, plus ESLint, Prettier, TypeScript, route type generation, and the Next.js production build.
- Automated browser control was unavailable during the NFA-59 local verification, so its documented responsive browser review remains a manual acceptance step.
- The focused NFA-60 component, gateway, and page-integration run passed 17 tests across 3 files.
- The complete frontend run after NFA-60 passed 72 tests across 16 files, plus ESLint, Prettier, TypeScript, route generation, and the Next.js production build.
- The focused existing FastAPI generation endpoint run passed 33 tests, and Ruff passed for the generation request models and HTTP boundary.
- The NFA-60 local Next.js server returned HTTP 200, but native browser automation was unavailable, so responsive browser review remains a manual acceptance step.
- The focused NFA-61 state, control, and page-integration run passed 24 tests across 3 files.
- The complete frontend run after NFA-61 passed 82 tests across 17 files, plus ESLint, Prettier, TypeScript, route generation, and the Next.js production build.
- The NFA-61 local Next.js server returned HTTP 200. Native browser automation remained unavailable, so responsive and assistive-technology browser review remains a manual acceptance step.
- The focused NFA-62 editor, generation-control, and page-integration run passed 24 tests across 3 files.
- The complete frontend run after NFA-62 passed 91 tests across 18 files, plus ESLint, Prettier, TypeScript, route generation, and the Next.js production build.
- The NFA-62 local Next.js source preview returned HTTP 200. Native browser automation remained unavailable, so responsive, keyboard, and assistive-technology browser review remains a manual acceptance step.
- The focused NFA-63 preview, image gateway, editor, generation-control, and page-integration run passed 37 tests across 5 files.
- The complete frontend run after NFA-63 passed 104 tests across 20 files, plus ESLint, Prettier, TypeScript, route generation, and the Next.js production build.
- The NFA-63 local Next.js source preview returned HTTP 200. Native browser automation remained unavailable, so selected-image, responsive, keyboard, and assistive-technology browser review remains a manual acceptance step.
- The focused NFA-64 backend initial-image and regeneration run passed 15 tests without a live OpenAI call.
- The complete frontend run after NFA-64 passed 114 tests across 23 files.
- The NFA-64 production build passed and the local Next.js login route returned HTTP 200. Native browser automation was unavailable, so final responsive, keyboard, and assistive-technology browser review remains a manual acceptance step.
- The focused NFA-65 accessibility, contrast, motion, responsive, focus, and authentication run passed 26 tests across 5 files.
- The complete frontend run after NFA-65 passed 129 tests across 26 files, plus ESLint, Prettier, TypeScript, route generation, and the Next.js production build.
- The NFA-65 production server returned HTTP 200 for `/`, `/login`, and `/register`. The protected `/dashboard` route returned 307 to the authentication-required login route.
- Native browser control was unavailable during NFA-65, so the documented 375 px, 768 px, 1440 px, keyboard, and VoiceOver acceptance record remains pending human review.
- The focused NFA-67 API and service run passed 5 tests covering authentication, validation, metadata preservation, idempotency, duplicate protection, owner isolation, image validation, stale updates, and safe storage failures.
- The NFA-67 PostgreSQL test passed against the safety-gated `newsflow_saved_draft_test` database. It applied migration `20261101_0013`, verified immutable original and manual versions, rejected a stale write, and rolled the schema back. GitHub Actions will repeat the same proof.
- The complete backend run after NFA-67 passed 427 tests, skipped 14 safety-gated tests, deselected the optional live-model test, and measured 79.46 percent branch-aware coverage, above the 75 percent floor.
- The existing migration and repeatable-seed integration test passed with NFA-67's required source-generation field, then rolled back and rebuilt the isolated schema.
- The expanded NFA-68 focused API and service run passed 9 tests covering owner-only listing, stable newest-first pagination, total metadata, safe selected-image metadata, invalid parameters and UUIDs, partial updates, stale conflicts, cross-user masking, OpenAPI operations, and the retained NFA-67 create and update controls.
- The expanded NFA-68 PostgreSQL proof passed against `newsflow_saved_draft_test`. It verified owner-scoped paginated listing and safe image metadata without exposing the private storage key, in addition to NFA-67 migration, version, conflict, and rollback behaviour.
- The complete backend run after NFA-68 passed 431 tests, skipped 14 safety-gated tests, deselected the optional live-model test, and measured 79.50 percent branch-aware coverage, above the 75 percent floor.
- Ruff linting and formatting checks passed for the complete backend after NFA-68.
- The focused NFA-69 content-library API, listing, pagination, controlled-state, and reopening run passed 14 tests across 3 files.
- The complete frontend run after NFA-69 passed 143 tests across 29 files.
- Prettier, strict TypeScript, ESLint, and the Next.js 16 production build passed after NFA-69. The build generated the authenticated `/library` route and partially prerendered `/library/[draftId]` route.
- NFA-69 tests used synthetic saved drafts and mocked network responses. They did not use real accounts, production credentials, live CNN content, or live OpenAI requests.
- The focused NFA-70 backend run passed 14 saved-draft and history tests. It covered newest-first retrieval, selected history, owner isolation, unavailable direct modification, append-only restoration, and stale conflicts.
- The NFA-70 PostgreSQL saved-draft proof passed against `newsflow_saved_draft_test`, recording `initial_save` and `manual_edit` entries in the same transactions as the current saved state.
- The migration and repeatable-seed proof passed against `newsflow_migration_test`, including upgrade to `20261102_0014`, one synthetic initial history entry, downgrade to base, and rebuild to head.
- The complete frontend run after NFA-70 passed 146 tests across 30 files. Prettier, strict TypeScript, ESLint, and the Next.js 16 production build passed, including `/library/[draftId]/versions/[versionId]`.
- NFA-70 tests use only synthetic source, text, image metadata, users, and mocked network responses. They make no live CNN or OpenAI request.
- The focused NFA-71 clipboard and image-download gateway run passed 12 tests covering current edited text, exact line breaks, empty content, clipboard support and permission failures, session forwarding, safe filenames, approved MIME types, missing images, expired sessions, keyboard-focusable controls, and controlled backend failures.
- The retained NFA-53 backend image-delivery run passed 12 tests covering authentication, owner isolation, identical cross-owner and missing responses, storage integrity, approved formats, safe filenames, and private caching.
- The complete frontend run after NFA-71 passed 158 tests across 32 files. Prettier, strict TypeScript, ESLint, and the Next.js 16 production build passed, including the new `/api/images/[imageId]/download` route.
- NFA-71 tests use synthetic text and image bytes with mocked browser and network boundaries. They make no live CNN, OpenAI, or LinkedIn request.
- The focused NFA-72 backend and configuration run passed 24 tests, including owner deletion, cross-user masking, unauthenticated rejection, object cleanup, retry recording, retention results, and bounded settings.
- The complete backend quality run after NFA-72 passed 441 tests, skipped 15 opt-in integration tests, deselected the live-model test, and measured 78.15 percent branch-aware coverage, above the enforced 75 percent floor.
- The NFA-72 migration proof passed against `newsflow_migration_test`, including upgrade through `20261102_0015`, repeatable seed loading, full rollback, and rebuild to head.
- The expanded saved-draft PostgreSQL proof passed 2 tests against `newsflow_saved_draft_test`, including immediate access removal, private-image cleanup, history removal, prompt and text redaction, and final lifecycle evidence.
- The focused NFA-72 frontend run passed 5 tests covering confirmation, cancellation, CSRF-protected deletion, controlled failure, library redirection, cookie allowlisting, and invalid UUID rejection.
- The complete frontend run after NFA-72 passed 163 tests across 34 files. Prettier, ESLint, strict TypeScript, and the Next.js 16 production build passed, including `/api/drafts/[draftId]`.
- NFA-72 tests use only synthetic identifiers, content, accounts, and local disposable storage. They make no live CNN, OpenAI, LinkedIn, or production object-storage request.
- The NFA-73 joined lifecycle test passed against `newsflow_saved_draft_test`, covering authentication, CSRF, idempotent save, duplicate rejection, pagination, editing, stale-write protection, history, owner-authorised image download, cross-user masking, deletion, cleanup, and final retention removal.
- The isolated E7 PostgreSQL group passed 3 tests, including the retained persistence and retention proofs plus the new joined HTTP lifecycle.
- The complete backend run after NFA-73 passed 441 tests, skipped 16 opt-in integration tests, deselected the optional live-model test, and measured 78.15 percent branch-aware coverage, above the enforced 75 percent floor.
- The focused E7 frontend run passed 18 tests across 4 files. The complete frontend run passed 163 tests across 34 files, and ESLint, Prettier, strict TypeScript, generated route types, and the Next.js production build all passed.
- NFA-73 reuses the focused frontend, API, repository, migration, cleanup-failure, and retention tests instead of weakening or duplicating their detailed assertions. All fixtures remain synthetic and no live CNN, OpenAI, LinkedIn, production database, or production object-storage service is used.
- Automated tests verify responsive layout contracts and keyboard-reachable links. A final human review at 375 px, 768 px, and 1440 px remains appropriate before release.

## Review status

- Jira issues covered: NFA-36, NFA-38, NFA-39, NFA-40, NFA-41, NFA-42, NFA-43, NFA-44, NFA-45, NFA-46, NFA-48, NFA-49, NFA-50, NFA-51, NFA-52, NFA-53, NFA-54, NFA-56, NFA-58, NFA-59, NFA-60, NFA-61, NFA-62, NFA-63, NFA-64, NFA-65, NFA-67, NFA-68, NFA-69, NFA-70, NFA-71, NFA-72, and NFA-73
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
