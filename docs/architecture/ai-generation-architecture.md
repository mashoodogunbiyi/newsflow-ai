# E4 AI Generation Architecture

## Purpose and scope

This document describes the completed NewsFlow AI LinkedIn draft generation architecture delivered by Epic E4, including NFA-38 to NFA-46.

The workflow accepts a request from an authenticated NewsFlow AI user, verifies the selected article and its current rights, builds a bounded source-grounded prompt, calls OpenAI from FastAPI, validates the result, stores a private draft, records safe operational evidence, and returns a frontend-safe response.

It does not retrieve live CNN content, expose OpenAI credentials to the browser, or publish to LinkedIn.

## System context

```text
Next.js user interface
        |
        | Authenticated POST /api/generations
        v
FastAPI generation route
        |
        +--> Session and CSRF validation
        +--> Burst, daily, concurrency, and duplicate controls
        +--> PostgreSQL article and current rights
        +--> Versioned prompt builder
        +--> OpenAI service boundary
        +--> Structural and factual-grounding validation
        +--> Private owner-scoped draft persistence
        +--> Usage and audit evidence
        |
        v
Frontend-safe private draft response
```

PostgreSQL stores application records and operational metadata. The OpenAI API is called only by FastAPI. The Next.js browser code never receives `OPENAI_API_KEY`.

## Components and responsibilities

| Component | Main implementation | Responsibility |
|---|---|---|
| Generation REST API | `app/api/routes/generations.py` | Defines `POST /api/generations`, authentication dependency, request model, response model, and documented HTTP outcomes. |
| Shared API boundary | `app/api/generation.py` | Applies the burst limiter, delegates to the generation service, and maps safe service failures to HTTP responses. |
| Authentication and CSRF | `app/api/dependencies.py` | Resolves the server-managed session and requires matching CSRF proof before generation. |
| Article retrieval | `repositories/linkedin_generation.py` | Loads the current active article snapshot and saves the resulting private draft for its owner. |
| Rights verification | `services/article_rights.py` | Evaluates current source, verification, retention, attribution, AI-processing, and derivative-output permission. |
| Prompt construction | `services/prompt_builder.py` and `prompts/linkedin_post.py` | Builds the versioned trusted instructions and separates them from the allowed untrusted source fields. |
| OpenAI boundary | `services/openai_service.py` | Uses the official asynchronous SDK with bounded timeout, output, retry, safe error, and usage behaviour. |
| Generation orchestration | `services/linkedin_generation.py` | Coordinates retrieval, rights, prompts, OpenAI, output checks, persistence, usage, and audit recording. |
| Grounding validator | `services/generation_validator.py` | Checks trusted references and source support for numbers, quotations, dates, entities, and factual assertions. |
| Usage controls | `services/generation_usage.py` | Enforces shared daily, concurrency, and duplicate controls and stores safe provider-attempt outcomes and token counts. |
| Monitoring and audit | `services/generation_audit.py` and `services/generation_monitoring.py` | Correlates lifecycle events, measures duration, applies retention, and provides administrator-only audit and aggregate metrics. |

## Complete request lifecycle

1. The user signs in through the existing NewsFlow AI account flow.
2. The frontend submits `POST /api/generations` with the session cookie, CSRF header, article ID, tone, length, and optional idempotency key.
3. FastAPI and Pydantic reject missing, extra, or unsupported request fields.
4. The API resolves the authenticated user from the server-managed session and verifies CSRF proof.
5. The process-local burst limiter checks the authenticated user.
6. The audit service assigns a unique generation request ID and records `generation_started`.
7. The generation repository retrieves the current article snapshot.
8. The rights service verifies display and AI-generation permission. A denial stops the workflow before OpenAI.
9. The prompt builder includes only title, source name, publication date, category, description, and explicitly permitted content. Application instructions and untrusted article data remain separate.
10. The shared PostgreSQL usage service checks the daily allowance, active concurrency, and duplicate request state.
11. The OpenAI service sends a bounded structured-output request with the configured server-side model and credential.
12. The backend validates the JSON contract, insufficiency state, requested word range, source reference, and factual grounding.
13. A successful result is stored as an owner-scoped draft with source, rights, prompt version, model, usage, and safe validation metadata.
14. Usage and audit services record safe completion, token counts, duration, and correlation data.
15. The API returns the narrow `GenerationResponse` with `status = "draft"` and `review_required = true`.

A failure at any stage produces a stable safe category. Restricted article content, prompts, generated output, provider bodies, credentials, and stack traces are not copied into operational errors or audit records.

## Prompt design and versioning

The current prompt version is `linkedin_post_v1`.

The prompt package has two security boundaries:

- Trusted application instructions define grounding, safety, response structure, tone, length, and human-review rules.
- Untrusted article data is serialised as a separate JSON block and is explicitly treated as data, not instructions.

The allowed source fields are fixed by `PERMITTED_AI_SOURCE_FIELDS`. The prompt builder fails closed when permission, attribution, or permitted factual information is missing.

A future prompt change must create a new version rather than silently changing the meaning of `linkedin_post_v1`. The NFA-44 regression framework must compare the new version against the current baseline before release.

See [LinkedIn prompting](../linkedin-prompting.md) and [AI generation evaluation](../ai-generation-evaluation.md).

## Writing preferences

| Preference | Supported values | Behaviour |
|---|---|---|
| Tone | `professional`, `conversational`, `analytical` | Maps to application-owned trusted wording. Free-text tone instructions are not accepted. |
| Length | `short`, `medium`, `long` | Enforces 80-120, 130-200, or 220-320 words and a corresponding provider output cap. |

The browser cannot submit a system prompt, model name, owner ID, token budget, rights override, provider key, or publishing instruction.

## OpenAI and environment configuration

Real values belong only in the ignored `.env` file or an approved deployment secret store.

| Variable | Default | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | None | Required server-side credential for OpenAI generation. Sensitive. |
| `OPENAI_MODEL` | None | Approved OpenAI model identifier. |
| `OPENAI_REQUEST_TIMEOUT` | 30 | Maximum request duration in seconds. |
| `OPENAI_MAX_OUTPUT_TOKENS` | 800 | Server-wide upper output limit. |
| `OPENAI_MAX_RETRIES` | 2 | Bounded SDK retry budget for eligible temporary failures. |
| `GENERATION_RATE_LIMIT_ATTEMPTS` | 10 | Requests allowed in the local burst window. |
| `GENERATION_RATE_LIMIT_WINDOW_SECONDS` | 60 | Local burst window duration. |
| `GENERATION_DAILY_LIMIT` | 50 | Shared provider-bound attempts per user per UTC day. |
| `GENERATION_CONCURRENT_LIMIT` | 2 | Shared active provider-bound attempts per user. |
| `GENERATION_ATTEMPT_TIMEOUT_SECONDS` | 180 | Active usage reservation lease. |
| `GENERATION_USAGE_RETENTION_DAYS` | 90 | Completed usage-record retention. |
| `GENERATION_AUDIT_RETENTION_DAYS` | 90 | Generation audit-event retention. |
| `GENERATION_MONITORING_WINDOW_HOURS` | 24 | Default administrator metric window. |

Never place an OpenAI key in a `NEXT_PUBLIC_` variable, source code, documentation, Jira, screenshots, tests, or Git history.

See [OpenAI integration](../openai-integration.md) and the safe repository template [.env.example](../../.env.example).

## Rights, privacy, and ownership

- Generation requires current verified display, AI-processing, and derivative-output permission.
- Missing, unverified, revoked, expired, disabled-source, or restricted rights fail closed.
- Required source attribution must be complete.
- Only permitted source fields enter the prompt.
- The trusted source reference is constructed by backend code and cannot be replaced by model output.
- Stored drafts belong to the authenticated user and remain private.
- The frontend response excludes owner IDs, rights-version IDs, prompts, model identifiers, provider request IDs, and token counts.
- Audit records exclude complete prompts, article content, generated drafts, API keys, session tokens, and provider response bodies.

Live CNN access remains blocked by ADR-001. E4 tests and demonstrations use original synthetic fixtures only.

## Validation and human review

Validation occurs in layers:

1. Pydantic validates the public request.
2. The prompt builder verifies rights, attribution, and source sufficiency.
3. OpenAI is asked for one strict JSON object.
4. Pydantic validates the returned JSON again.
5. The application enforces the selected word range.
6. The grounding validator checks source-reference integrity and configured factual-claim patterns.

Outcomes are `passed_automated_checks`, `review_required`, or `rejected`. A passed automated result is not a factual guarantee. Every returned draft still has `review_required = true`.

No E4 route publishes to LinkedIn. Publication remains a manual user action outside NewsFlow AI.

See [Factual grounding and output validation](../factual-grounding-validation.md).

## Failure and usage behaviour

The public API uses one error envelope:

```json
{
  "error": {
    "code": "stable_machine_readable_code",
    "message": "Safe user-facing message."
  }
}
```

The API distinguishes authentication, CSRF, rights denial, missing articles, invalid preferences, insufficient context, duplicates, usage limits, invalid provider output, unavailable dependencies, and timeouts. Safe retryable responses include `Retry-After` when available.

The OpenAI SDK retry budget is bounded. The application does not add an unbounded second retry loop. Cost-sensitive daily, concurrent, and duplicate controls use PostgreSQL so they work across backend instances.

See [Generation API](../generation-api.md) and [Generation operations](../generation-operations.md).

## Monitoring and retention

NFA-45 records content-free lifecycle events with one request correlation ID. Administrators can inspect:

```text
GET /api/admin/generations/audit
GET /api/admin/generations/metrics
```

Aggregate metrics cover request outcomes, duration, rights and validation rejections, usage controls, provider error categories, and available token totals without using user or article IDs as metric labels.

See [Generation monitoring and audit](../generation-monitoring.md).

## Verification strategy

Routine tests mock OpenAI and use synthetic source data. They cover each component plus the complete HTTP-to-draft workflow. Safety-gated PostgreSQL tests prove migrations, rights, ownership, usage controls, and the article pipeline against deliberately named disposable databases.

The NFA-46 acceptance suite is `apps/api/tests/test_generation_workflow_acceptance.py`. It proves the joined request flow, authentication, CSRF, rights, preferences, source sufficiency, provider failure, malformed output, usage rejection, audit evidence, source reference, mandatory review, and absence of automatic publishing.

See [E4 acceptance results](../e4-generation-acceptance.md) and [Testing](../testing.md).

## Frontend handoff

E6 must implement the user-facing article selection, generation form, loading state, error display, source reference, validation warnings, editing, saving, copying, and manual export behaviour against the documented contract. FastAPI remains authoritative for authentication, rights, limits, validation, and ownership.

See [E6 generation integration contract](../e6-generation-integration-contract.md).

## Known limitations

- Generated drafts may contain inaccuracies despite automated checks.
- Grounding rules cannot prove complete factual correctness.
- Output varies between model requests and model versions.
- Insufficient permitted information may prevent generation.
- OpenAI availability, latency, rate limits, and account quota affect the feature.
- Token counts are recorded when available, but monetary cost is not calculated in application logic.
- The local burst limiter is process-specific; shared cost controls use PostgreSQL.
- Audit metrics are calculated on demand and do not yet feed an external dashboard or pager.
- Live-model evaluation is optional, billable, and excluded from normal CI.
- Live CNN integration remains prohibited until the existing No-Go decision is formally replaced with approved evidence.

## E4 readiness statement

The E4 backend is ready for E6 frontend integration against synthetic or otherwise authorised article data. It is not a production-release approval and does not authorise live CNN access or automatic LinkedIn publishing.
