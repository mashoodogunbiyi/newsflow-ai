# NFA-40 - LinkedIn Draft Generation Service

## Outcome

NFA-40 connects the existing NewsFlow AI authentication, PostgreSQL article catalogue, article-rights service, LinkedIn prompt builder, and OpenAI integration into one reusable backend workflow.

An authenticated user can request a source-grounded LinkedIn post draft from an authorised synthetic article. The backend validates and stores the result as private draft content for human review. It never publishes content to LinkedIn.

## Architecture

```text
POST /api/v1/linkedin-drafts
              |
              v
Authenticated session and CSRF proof
              |
              v
Per-user generation rate limit
              |
              v
Current PostgreSQL article snapshot
              |
              v
NFA-32 AI-processing rights decision
              |
              v
NFA-39 LinkedInPromptBuilder
              |
              v
NFA-38 OpenAIService
              |
              v
Strict JSON and word-limit validation
              |
              v
Owner-scoped PostgreSQL draft
```

The workflow reads only information already stored through the authorised catalogue pipeline. It does not retrieve an article directly from CNN during generation.

## API endpoints

### Generate a draft

```text
POST /api/v1/linkedin-drafts
```

The request requires:

- The HTTP-only authenticated session cookie.
- The matching `X-CSRF-Token` header.
- A current article UUID.
- A supported tone and length.

Example request:

```json
{
  "article_id": "40000000-0000-4000-8000-000000000003",
  "tone": "professional",
  "length": "medium"
}
```

Supported tones are `professional`, `conversational`, and `analytical`. Supported lengths are `short`, `medium`, and `long`. Pydantic rejects unsupported values and unexpected fields.

Clients may supply an `Idempotency-Key` header containing 8 to 128 letters, numbers, periods, underscores, colons, or hyphens. Repeating the same key with the same request returns the existing private draft instead of storing a duplicate. Reusing it for different generation inputs returns HTTP `409`. PostgreSQL stores only a SHA-256 representation of the client key.

Example response:

```json
{
  "draft_id": "generated-draft-id",
  "generation_id": "generated-run-id",
  "draft": "A source-grounded LinkedIn draft for human review.",
  "source": {
    "article_id": "40000000-0000-4000-8000-000000000003",
    "title": "Synthetic article title",
    "source_name": "NewsFlow AI synthetic fixture",
    "source_url": "https://example.invalid/article",
    "attribution_text": "Source: NewsFlow AI synthetic fixture",
    "rights_version_id": "current-rights-version-id"
  },
  "tone": "professional",
  "length": "medium",
  "status": "draft",
  "review_required": true,
  "prompt_version": "linkedin_post_v1",
  "model_identifier": "configured-model",
  "token_usage": {
    "input_tokens": 120,
    "output_tokens": 100,
    "total_tokens": 220
  },
  "created_at": "2026-10-29T18:00:00Z"
}
```

The response contains no user ID, secret, prompt content, session identifier, or provider error detail. It uses `Cache-Control: no-store`.

### Retrieve a private draft

```text
GET /api/v1/linkedin-drafts/{draft_id}
```

The repository query always combines the draft ID with the authenticated user's ID. A missing draft and another user's draft return the same HTTP `404` response. Private responses use `Cache-Control: private, no-store`.

## Rights and source controls

Before OpenAI is contacted, the service requires all of the following:

- An active authenticated user.
- An active article with an enabled source profile and current PostgreSQL snapshot.
- A current NFA-32 `USE_FOR_AI_GENERATION` decision.
- Verified and unexpired AI-processing and derivative-output permission.
- Complete required attribution.
- Available permitted content that is sufficient for the prompt builder.

The NFA-39 builder then sends only the approved title, source name, publication date, category, description, and permitted content fields to the AI boundary. The canonical URL, attribution text, article ID, provider item ID, and rights-version ID stay outside generated prose.

Missing, revoked, expired, disabled-source, incomplete, restricted, or insufficient information fails before provider access.

## Structured OpenAI response

The generation request uses the Responses API integration from NFA-38 and adds a strict JSON Schema format. The expected object contains exactly:

- `status`
- `draft`
- `insufficiency_reason`

The backend still validates the returned JSON with Pydantic. This defence rejects malformed JSON, missing or extra fields, empty ready drafts, contradictory status values, and unsupported insufficiency structures. It also enforces the versioned NFA-39 word ranges:

| Length | Required words | Maximum output tokens |
|---|---:|---:|
| Short | 80 to 120 | 220 |
| Medium | 130 to 200 | 360 |
| Long | 220 to 320 | 560 |

OpenAI's [Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses) recommends JSON Schema enforcement where supported. Application validation remains necessary because structured output does not prove factual accuracy.

## PostgreSQL persistence

A successful generation writes:

- One owner-scoped `generated_posts` row with `status = 'draft'`.
- One successful `generation_runs` row with the model, prompt version, provider request reference, token usage, hashed idempotency value, and the exact rights-version ID used.
- One immutable AI-origin `post_versions` row containing the generated draft and approved source attribution.
- Three safe application-generated hashtag records required by the approved NFA-20 schema.

Migration `20261029_0007` adds `generation_runs.article_rights_version_id` so the permission decision used for generation remains auditable even when current article rights change later.

The generated prose is retained because it is the user's editable draft. The source prompt and source content are not duplicated in the generation record. `prompt_text` contains only a non-sensitive request fingerprint marker because the existing schema requires a value.

## Request and cost controls

- The default per-user limit is 10 generation requests per 60 seconds.
- `GENERATION_RATE_LIMIT_ATTEMPTS` and `GENERATION_RATE_LIMIT_WINDOW_SECONDS` configure the local limiter.
- NFA-39 length selection supplies a bounded output-token value.
- NFA-38 enforces the server-wide maximum output, timeout, and retry budget.
- Provider retries remain bounded by the OpenAI SDK configuration.
- The service does not add an unbounded application retry loop.
- An idempotency key prevents repeated storage for the same completed request.
- Token usage and the model identifier are recorded without storing credentials.

The in-process limiter is suitable for local development. A multi-instance deployment must move this control to a shared rate-limit store, gateway, or trusted reverse proxy.

## Controlled errors

| Condition | HTTP status | Safe code |
|---|---:|---|
| Missing session | 401 | `authentication_required` |
| Invalid CSRF proof | 403 | `csrf_validation_failed` |
| Article is not permitted | 403 | `article_ai_generation_not_permitted` |
| Article is unavailable | 404 | `generation_article_not_found` |
| Source information is insufficient | 422 | `insufficient_source_information` |
| Per-user request limit reached | 429 | `linkedin_generation_rate_limited` |
| Idempotency key reused differently | 409 | `idempotency_key_conflict` |
| Empty, malformed, or out-of-range model result | 502 | Generation validation code |
| OpenAI or PostgreSQL is unavailable | 503 | Safe service-specific code |

Provider bodies, database details, credentials, source content, and generated prose are not written to error messages or operational logs.

## Automated tests

Run the focused NFA-40 checks from the repository root:

```bash
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_openai_service.py \
  apps/api/tests/test_prompt_builder.py \
  apps/api/tests/test_linkedin_generation_service.py \
  apps/api/tests/test_linkedin_generation_api.py
```

Coverage includes:

- Successful orchestration and source-reference preservation.
- Authentication and strict request validation.
- Missing article, denied rights, and insufficient source information.
- Correct writing preferences and strict JSON schema forwarding.
- Empty, malformed, insufficient, and out-of-range provider results.
- OpenAI timeout handling and provider cleanup.
- Per-user rate limiting and idempotent duplicate handling.
- Owner-only draft retrieval.
- Human-review status and no automatic publication.

Every test uses synthetic article information and a fake OpenAI client. Tests never make a live or billable OpenAI request and never use live CNN content.

Verified locally on 29 October 2026:

- The focused NFA-40 run passed 58 tests.
- The complete backend suite passed 216 tests and safely skipped 11 opt-in PostgreSQL integration tests.
- Backend branch-aware coverage was 78.28 percent, above the enforced 75 percent minimum.
- Ruff linting and formatting checks passed across the backend application and tests.
- The Alembic migration chain has one head at `20261029_0007`.

## Limitations and next steps

- NFA-40 provides backend endpoints. The Next.js dashboard does not yet provide the article selection and generation interface.
- The generated draft is structurally validated but remains unverified content requiring human review.
- Detailed factual-grounding evaluation and content-safety workflows remain later E4 tasks.
- Local rate limiting is process-specific and must use shared infrastructure before multi-instance deployment.
- Live CNN access remains blocked by ADR-001. Only synthetic fixtures may be used until written authorisation and a revised Go decision exist.
- A real generation requires an approved `OPENAI_MODEL` and a valid server-side `OPENAI_API_KEY` in the ignored `.env` file or deployed secret store.

NFA-40 is implemented for Mashood Ogunbiyi's review. The Jira issue should move to Done only after the checks pass, the pull request is merged, and final GitHub evidence is attached.
