# NFA-41 - LinkedIn Generation REST API

## Outcome

NFA-41 provides the frontend-facing REST endpoint that allows an authenticated NewsFlow AI user to request a private LinkedIn post draft:

```text
POST /api/generations
```

The endpoint is owned by NewsFlow AI. It is not an OpenAI or CNN endpoint. It reuses the NFA-40 generation service instead of duplicating article retrieval, rights checks, prompt construction, OpenAI access, output validation, or persistence.

## Request flow

```text
Next.js frontend
      |
      | POST /api/generations
      v
FastAPI authentication and CSRF validation
      |
      v
Per-user generation request limit
      |
      v
NFA-40 LinkedInGenerationService
      |-- current PostgreSQL article
      |-- display and AI-processing rights
      |-- NFA-39 prompt builder
      |-- NFA-38 OpenAI service
      |-- strict output validation
      `-- private PostgreSQL draft
      |
      v
Minimal frontend JSON response
```

The NFA-40 service checks article rights before constructing an OpenAI client. Restricted, expired, disabled, unavailable, or insufficient source information therefore fails before a provider request.

## Authentication and request protection

The request requires:

- A valid HTTP-only NewsFlow AI session cookie.
- The matching `X-CSRF-Token` header.
- A valid article UUID.
- A supported writing tone and post length.

The endpoint does not trust frontend validation. FastAPI and Pydantic validate the complete request again on the backend.

The optional `Idempotency-Key` header accepts 8 to 128 letters, numbers, periods, underscores, colons, or hyphens. Repeating the same key for the same user and request returns the existing generation rather than storing a duplicate.

## Request schema

```json
{
  "article_id": "40000000-0000-4000-8000-000000000003",
  "tone": "professional",
  "length": "medium"
}
```

Supported tones:

- `professional`
- `conversational`
- `analytical`

Supported lengths:

- `short`
- `medium`
- `long`

The request model forbids extra properties. A user cannot submit a prompt, model, owner ID, provider key, rights override, system instruction, token limit, or publishing instruction.

## Successful response

A successful request returns HTTP `201 Created`:

```json
{
  "generation_id": "41000000-0000-4000-8000-000000000020",
  "article_id": "40000000-0000-4000-8000-000000000003",
  "draft": "A source-grounded LinkedIn draft for human review.",
  "tone": "professional",
  "length": "medium",
  "source_title": "Synthetic article title",
  "source_name": "NewsFlow AI synthetic fixture",
  "source_url": "https://example.invalid/newsflow-ai/article",
  "source_attribution": "Source: NewsFlow AI synthetic fixture",
  "status": "draft",
  "review_required": true,
  "created_at": "2026-10-29T20:00:00Z"
}
```

The response includes the generation identifier, selected article identifier, source reference, user preferences, generated draft, and mandatory review state. It uses `Cache-Control: no-store`.

The response deliberately excludes:

- OpenAI credentials or provider request identifiers.
- Internal prompts or system instructions.
- Model names and token usage.
- Rights-version identifiers and confidential agreement details.
- User, session, owner, database, and internal draft identifiers.
- Restricted article content and exception traces.

## HTTP status codes

| Status | Meaning |
|---:|---|
| 201 | A private generation resource was created. |
| 400 | The request cannot be processed. |
| 401 | The session is missing, invalid, or expired. |
| 403 | CSRF validation failed or the article is not authorised for AI generation. |
| 404 | The article does not exist or must not be disclosed. |
| 409 | An idempotency key was reused for different inputs. |
| 422 | The request schema or permitted source information is invalid. |
| 429 | The authenticated user exceeded the generation request limit. |
| 502 | OpenAI failed the request or returned an invalid result. |
| 503 | Generation configuration, storage, rights data, or OpenAI is unavailable. |
| 504 | The upstream OpenAI request timed out. |

Every expected failure uses the shared JSON error envelope:

```json
{
  "error": {
    "code": "stable_machine_readable_code",
    "message": "Safe user-facing message."
  }
}
```

Provider bodies, credentials, prompts, article text, generated prose, database details, and stack traces are never copied into an error response.

## Request limits and ownership

- The default local limit is 10 generation attempts per user in 60 seconds.
- The response includes `Retry-After` when the user is rate limited.
- NFA-40 applies the configured OpenAI timeout, retry budget, and maximum output-token controls.
- Successful generations are stored against the authenticated user's ID.
- Existing owner-scoped retrieval requires the same user ID, preventing another user from accessing the private draft.
- Generated content is always returned as a draft and is never automatically published.

The in-memory request limiter is suitable for one local backend process. A multi-instance deployment must use a trusted shared rate-limit store or API gateway.

## OpenAPI documentation

When FastAPI is running locally, the endpoint is documented at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

The generated specification records the request and response models, authentication and CSRF description, source-rights behaviour, request limit, idempotency header, and expected HTTP responses.

## Automated tests

Run the focused NFA-41 API tests from `apps/api`:

```bash
pytest tests/test_generation_api.py \
  tests/test_linkedin_generation_api.py \
  tests/test_linkedin_generation_service.py
```

The tests cover:

- Successful generation and exact public response fields.
- Authentication and CSRF rejection before service access.
- Invalid article IDs, preferences, extra parameters, and oversized headers.
- Missing and restricted articles.
- Insufficient authorised source information.
- Safe invalid, unavailable, and timed-out OpenAI responses.
- Repository and rights-data failures without sensitive detail leakage.
- Per-user rate limiting and idempotency forwarding.
- OpenAPI request, response, error, and security descriptions.
- Reuse of the NFA-40 service and its pre-OpenAI rights checks.

All tests use synthetic article information, sessions, users, and provider responses. No test makes a live or billable OpenAI request, uses live CNN content, or reads a real credential.

Verified locally on 29 October 2026:

- The focused NFA-41 and reused NFA-40 generation run passed 36 tests.
- The complete backend suite passed 241 tests and safely skipped 11 opt-in PostgreSQL integration tests.
- Backend branch-aware coverage was 78.99 percent, above the enforced 75 percent minimum.
- Ruff linting and formatting checks passed across all backend application and test files.
- Docker Compose configuration and Git whitespace validation passed.

## Review status

- Jira issue: NFA-41
- Implementation status: Ready for Mashood Ogunbiyi's review
- Approval status: Pending review
- Live CNN status: Blocked by ADR-001
