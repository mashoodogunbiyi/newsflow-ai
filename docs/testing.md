# NewsFlow AI Testing Guide

## Purpose

This guide records the automated test strategy for account security, the provider-to-database article workflow, and the backend AI boundary, including NFA-33 synchronisation, the NFA-34 article catalogue REST API, NFA-35 ingestion observability, the NFA-36 complete synthetic pipeline suite, the mocked NFA-38 OpenAI integration, NFA-39 grounded prompt construction, NFA-40 private LinkedIn draft generation, the NFA-41 frontend-facing generation REST API, NFA-42 deterministic factual-grounding validation, NFA-43 generation operations, the NFA-44 AI evaluation and regression framework, NFA-45 generation monitoring and audit, the NFA-46 joined E4 acceptance workflow, the NFA-48 safe image-prompt composer, the NFA-49 sensitive-news image safety policy, the mocked NFA-50 OpenAI image generation boundary, and NFA-51 secure image validation and private storage.

The test suite is designed to detect security regressions before a pull request is merged. It uses only synthetic users, passwords, sessions, and content.

## Test layers

| Layer | Location | Purpose |
|---|---|---|
| Backend unit and API tests | `apps/api/tests/test_*.py` | Fast tests for accounts, providers, articles, rights, synchronisation, catalogue endpoints, OpenAI integration, grounded prompts, generation orchestration, CSRF, safe errors, and authorisation. |
| Account-security regression tests | `apps/api/tests/test_account_security_regression.py` | One integrated in-memory journey from registration through private-content access and logout. |
| PostgreSQL integration tests | `apps/api/tests/*_integration.py` | Opt-in verification of migrations, constraints, accounts, ownership, article ingestion, provenance, rights, synchronisation, and catalogue queries. |
| Frontend authentication tests | `apps/web/__tests__` | Registration, login, logout, error, loading, session restoration, gateway, and protected-route behaviour. |
| Complete article pipeline | `apps/api/tests/test_catalogue_pipeline_e2e.py` | Safety-gated synthetic provider-to-PostgreSQL-to-REST verification, including failure, rights, logs, and concurrent ingestion. |
| Pull-request quality checks | `.github/workflows/quality.yml` | Runs backend and frontend quality checks, enforces backend coverage, and runs the isolated NFA-36 PostgreSQL suite on GitHub. |
| AI generation evaluation | `apps/api/tests/evaluation` | Uses synthetic articles and mocked outputs to score generation properties and detect prompt regressions without external requests. |
| Generation monitoring and audit | `apps/api/tests/test_generation_audit.py` and `test_admin_generation_monitoring.py` | Checks lifecycle correlation, duration, metrics, token aggregation, retention, safe records, and administrator-only inspection. |

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

## NFA-38 OpenAI integration coverage

| Requirement | Automated evidence |
|---|---|
| Successful structured generation result | `test_openai_service.py` |
| Official SDK client configuration | `test_openai_service.py` |
| Missing key and model handling | `test_config.py` and `test_openai_service.py` |
| Configurable timeout, output cap, and retry budget | `test_config.py` and `test_openai_service.py` |
| Authentication, rate-limit, timeout, and unavailable errors | `test_openai_service.py` |
| Incomplete and empty response handling | `test_openai_service.py` |
| Token-usage capture and missing usage | `test_openai_service.py` |
| Prompt, credential, and provider-detail log protection | `test_openai_service.py` |
| No live or billable request | Fake SDK client injected by every service test |

Run the focused NFA-38 tests from `apps/api`:

```bash
pytest tests/test_config.py tests/test_openai_service.py
```

The tests construct real OpenAI SDK exception types around synthetic HTTP responses, but all generation responses and client behaviour are mocked. No test reads a real API key or contacts OpenAI.

## NFA-39 LinkedIn prompt coverage

| Requirement | Automated evidence |
|---|---|
| Professional, conversational, and analytical tones | `test_prompt_builder.py` |
| Short, medium, and long word and token limits | `test_prompt_builder.py` |
| Exact permitted source-field allowlist | `test_prompt_builder.py` |
| Higher-priority instructions separated from untrusted source data | `test_prompt_builder.py` |
| Unsupported facts, statistics, quotations, names, dates, and events prohibited | `test_prompt_builder.py` |
| Exact article reference kept outside generated prose | `test_prompt_builder.py` |
| Title-only and missing information declined | `test_prompt_builder.py` |
| Restricted and denied-rights content rejected | `test_prompt_builder.py` |
| Injection text remains untrusted data | `test_prompt_builder.py` |
| Invalid preferences and extra fields rejected | `test_prompt_builder.py` |
| Prompt version and masked request representation | `test_prompt_builder.py` |
| Versioned supported and forbidden factual claims | `fixtures/linkedin_prompt_evaluations.json` and `test_prompt_builder.py` |

Run the focused NFA-39 tests from `apps/api`:

```bash
pytest tests/test_prompt_builder.py
```

The tests construct prompts from original synthetic fixture data. They do not call OpenAI, use a real credential, or evaluate live CNN information.

## NFA-40 LinkedIn generation coverage

| Requirement | Automated evidence |
|---|---|
| Article, rights, prompt, OpenAI, validation, and persistence orchestration | `test_linkedin_generation_service.py` |
| Authentication and validated tone and length input | `test_linkedin_generation_api.py` |
| Missing article and denied or missing rights | `test_linkedin_generation_service.py` |
| Insufficient permitted source information | `test_linkedin_generation_service.py` |
| Strict Responses API JSON Schema forwarding | `test_openai_service.py` and `test_linkedin_generation_service.py` |
| Empty, malformed, contradictory, and out-of-range output rejection | `test_linkedin_generation_service.py` |
| OpenAI timeout and safe failure handling | Service and API tests |
| Per-user rate limit and retry delay | `test_linkedin_generation_api.py` |
| Idempotent completed requests | `test_linkedin_generation_service.py` |
| Exact source and rights-version preservation | `test_linkedin_generation_service.py` |
| Owner-only private draft retrieval | `test_linkedin_generation_service.py` |
| Human review and no automatic publication | Service and API response tests |

Run the focused NFA-40 tests from `apps/api`:

```bash
pytest tests/test_openai_service.py \
  tests/test_prompt_builder.py \
  tests/test_linkedin_generation_service.py \
  tests/test_linkedin_generation_api.py
```

The OpenAI client, model result, article, rights decision, and users are synthetic. No focused or normal test makes a live OpenAI request, accesses live CNN information, or requires a real credential.

## NFA-41 generation REST API coverage

| Requirement | Automated evidence |
|---|---|
| `POST /api/generations` and 201 response | `test_generation_api.py` |
| Authentication and CSRF enforcement | `test_generation_api.py` plus existing authentication tests |
| Article UUID, tone, length, extra-field, and header validation | `test_generation_api.py` |
| Authenticated user identity passed to the service | `test_generation_api.py` |
| NFA-40 service reuse and pre-provider rights enforcement | Generation API and NFA-40 service tests |
| Minimal response and internal-field exclusion | `test_generation_api.py` |
| Missing, restricted, and insufficient articles | API and NFA-40 service tests |
| Safe 502, 503, and 504 provider failures | `test_generation_api.py` |
| Per-user rate limit and retry delay | `test_generation_api.py` |
| Idempotency header validation and delegation | `test_generation_api.py` |
| OpenAPI request, response, security, and error documentation | `test_generation_api.py` |

Run the focused NFA-41 tests from `apps/api`:

```bash
pytest tests/test_generation_api.py \
  tests/test_linkedin_generation_api.py \
  tests/test_linkedin_generation_service.py
```

These tests use synthetic records and provider doubles. They make no live OpenAI request and do not use live CNN information.

## NFA-42 factual-grounding coverage

| Requirement | Automated evidence |
|---|---|
| Strict structured output and empty-result rejection | `test_generation_validator.py` and `test_linkedin_generation_service.py` |
| Trusted article ID and canonical URL | `test_generation_validator.py` |
| Unsupported numbers and quotations | `test_generation_validator.py` |
| Named entities and low-support factual assertions | `test_generation_validator.py` |
| Clearly framed commentary distinguished from factual claims | `test_generation_validator.py` |
| Insufficient permitted context | `test_generation_validator.py` and prompt-builder tests |
| Safe warning text without source or claim excerpts | `test_generation_validator.py` |
| Blocking result rejected before persistence | `test_linkedin_generation_service.py` |
| Grounding status and warnings in API responses | Generation API tests |
| Grounding migration fields and index | `test_migrations_integration.py` |

Run the focused NFA-42 tests from `apps/api`:

```bash
pytest tests/test_generation_validator.py \
  tests/test_linkedin_generation_service.py \
  tests/test_generation_api.py \
  tests/test_linkedin_generation_api.py
```

All grounding fixtures are original synthetic records. The validator does not call a second model, make network requests, retrieve restricted text, or log article and draft excerpts.

## NFA-43 generation operations coverage

| Requirement | Automated evidence |
|---|---|
| Configurable daily, concurrent, lease, retention, timeout, retry, and token controls | `test_config.py`, `test_generation_usage.py`, and `test_openai_service.py` |
| Shared daily and concurrent enforcement | `test_generation_usage_integration.py` against safety-gated PostgreSQL |
| Active duplicate protection | Generation usage unit and PostgreSQL integration tests |
| Successful status and available token recording | `test_generation_usage.py` and `test_linkedin_generation_service.py` |
| Failed status and safe category recording | Generation usage, OpenAI service, and LinkedIn generation tests |
| Authentication before provider use | Generation API authentication tests |
| Safe HTTP errors and retry headers | `test_generation_api.py` and `test_linkedin_generation_api.py` |
| OpenAI authentication, temporary rate limit, quota, timeout, availability, and invalid-response handling | `test_openai_service.py` |
| Sensitive prompt, content, credential, and provider-detail protection | OpenAI service, generation usage, and API tests |
| Migration fields, constraints, indexes, upgrade, and rollback | `test_migrations_integration.py` |

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

| Requirement | Automated evidence |
|---|---|
| Reusable synthetic article dataset | `fixtures/evaluation_articles.json` and its schema-validation tests |
| Mocked deterministic generation cases | `fixtures/expected_generation_cases.json` |
| Structure, tone, length, and writing quality | `evaluation/test_generation_quality.py` |
| Grounding, numbers, quotations, source references, and insufficient context | `evaluation/test_grounding_and_safety.py` |
| Prompt injection and restricted information | Evaluation safety tests plus prompt-builder and generation-service tests |
| Prompt-version comparison | `evaluation/test_prompt_regression.py` |
| Generation API failures and invalid preferences | `test_generation_api.py` and `test_linkedin_generation_api.py` |
| Usage limits, concurrency, and duplicates | `test_generation_usage.py` and the safety-gated PostgreSQL test |
| Authentication, CSRF, rights, and authorisation | Generation API, service, prompt-builder, and ownership tests |
| Optional live model remains separate | `evaluation/test_live_model_evaluation.py` with the `live_ai` marker and explicit environment gate |

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

| Requirement | Automated evidence |
|---|---|
| Start, completion, and failure events | `test_generation_audit.py` and `test_linkedin_generation_service.py` |
| Rights, validation, and usage-rejection events | Audit service and generation workflow tests |
| Correlation identifier and duration | `test_generation_audit.py` |
| Success, failure, timeout, rate-limit, rejection, and average-duration metrics | `test_generation_audit.py` |
| Available NFA-43 token totals | Monitoring aggregation test |
| Safe fields and sensitive-data minimisation | Audit redaction test |
| Administrator access and ordinary-user denial | `test_admin_generation_monitoring.py` |
| Retention and configuration bounds | Audit and configuration tests |
| PostgreSQL table, columns, indexes, upgrade, and rollback | `test_migrations_integration.py` |

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

| Requirement | Automated evidence |
|---|---|
| Successful authenticated HTTP-to-private-draft workflow | Complete success scenario and exact public response-field assertion |
| Session and CSRF enforcement | Missing-session and invalid-CSRF scenarios |
| Rights denied before provider access | Restricted-article scenario and zero OpenAI-call assertion |
| Preference and source-context validation | Invalid-enum and insufficient-context scenarios |
| Safe OpenAI and malformed-output failures | Unavailable-provider and invalid-structured-output scenarios |
| Shared usage rejection | Limit-exceeded scenario, `Retry-After`, and zero provider access |
| Trusted source reference and mandatory review | Success response assertions |
| Content-free correlated audit evidence | Recorded start, rights, validation, completion, and failure events |
| Human control and no automatic publishing | Draft status, review requirement, and route inspection |

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

| Requirement | Automated evidence |
|---|---|
| Valid structured prompt | Article-context result, version, reference, and review flags |
| Defined styles and composition | Every style, aspect ratio, and composition mapping |
| Strict parameters | Unsupported enums and extra free-text property rejection |
| Current source rights | Allowed, denied, mismatched, incomplete-attribution, and restricted-content scenarios |
| Permitted fields only | Exact article-context allowlist and excluded source metadata |
| Insufficient information | Safe rejection rather than invented visual details |
| Article-or-draft context | Matching draft, missing draft, generation mismatch, validation rejection, and size bound |
| Prompt-injection separation | Malicious synthetic content remains outside trusted instructions |
| Restricted photography and non-deception | Mandatory original-illustration and non-documentary rules |
| Version and safe representation | `image_prompt_v1` and masked context fields |

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

| Requirement | Automated evidence |
|---|---|
| Ordinary topic | Allowed conceptual technology scenario |
| Sensitive categories | Parameterised conflict, terrorism, disaster, injury, health, political, and criminal scenarios |
| Misleading documentary imagery | Conflict and disaster fabrication rejection |
| Conceptual alternative | Sensitive requests restricted to conceptual, non-photorealistic treatment |
| Identifiable real person | Sensitive person misrepresentation rejection |
| Frontend override prevention | Extra safety fields rejected and text override denied |
| Prompt injection | Article instruction remains untrusted and cannot enable photorealism |
| Uncertain classification | Conservative review-required provider gate |
| Provider safety | Missing moderation blocks or pauses provider access |
| Safe policy record | Content-free recorder assertions |
| AI designation and review | Required result fields in ordinary and sensitive decisions |
| Provider call gate | Allowed decisions continue; rejected and review-required decisions stop |

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

| Requirement | Automated evidence |
|---|---|
| Official SDK integration | Client factory receives backend key, timeout, and zero SDK retries |
| Successful generation | Controlled request arguments, masked image bytes, metadata, and review state |
| Missing credentials | Safe settings error before client construction |
| Safety enforcement | Rejected safety decision stops before provider access |
| Rights enforcement | Denied or mismatched rights stop before provider access |
| Supported settings | Approved models, aspect-ratio sizes, quality enums, formats, and hashed safety identifier |
| Provider formats | Strict Base64 image validation and masked HTTPS reference handling |
| Timeout | SDK and application deadline failures with no automatic replay |
| Authentication and quota | Safe permanent failures with no retry |
| Rate limiting | One bounded mocked retry and exhausted-budget failure |
| Temporary availability | Controlled connection failure without ambiguous replay |
| Moderation | Generic provider moderation failure without sensitive category details |
| Invalid response | Empty, malformed, wrong-signature, and unsafe-URL rejection |
| Duplicate protection | Cached completion, active protection, and request-ID conflict handling |
| Usage tracking | Available total, text, and image token counts plus missing-usage handling |
| Credential protection | Logs and errors exclude key, prompt, provider detail, image data, and revised prompt |
| Safe record | Recorder receives content-free IDs, digest, dimensions, and usage only |

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

Verified locally on 31 October 2026:

- Backend linting and formatting passed.
- The normal backend run passed 390 tests and safely skipped 13 opt-in PostgreSQL and live-model tests.
- Backend branch-aware coverage measured 83.85 percent, above the enforced 75 percent floor.
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
- No test used live CNN content, a live OpenAI request, real user data, or production credentials.

## Review status

- Jira issues covered: NFA-36, NFA-38, NFA-39, NFA-40, NFA-41, NFA-42, NFA-43, NFA-44, NFA-45, NFA-46, NFA-48, NFA-49, NFA-50, and NFA-51
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
