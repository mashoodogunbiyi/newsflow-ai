# NFA-43 - Generation Error Handling and Usage Controls

## Status

- Jira issue: NFA-43
- Implementation status: Complete and ready for review
- Approval status: Pending Mashood Ogunbiyi's review
- Date implemented: 30 October 2026

## Outcome

NewsFlow AI now places shared, configurable controls around every provider-bound LinkedIn draft generation attempt. The controls protect availability and cost, stop simultaneous duplicate requests, record safe success or failure evidence, and return understandable API errors without exposing prompts, article content, generated prose, credentials, or provider exception details.

## Control sequence

The backend performs the following checks in order:

1. FastAPI requires a valid authenticated session and CSRF proof.
2. The process-local burst limiter rejects unusually frequent requests.
3. The article and its display rights are checked.
4. Current AI-processing and derivative-output rights are checked.
5. The prompt builder confirms that sufficient permitted source information exists.
6. A completed request with the same idempotency key returns the stored draft.
7. PostgreSQL reserves a generation usage attempt under a per-user transaction lock.
8. The reservation enforces the daily limit, concurrent limit, and active duplicate rule.
9. The bounded OpenAI request runs with the configured timeout, output-token cap, and retry budget.
10. The response is validated, grounded, and stored.
11. The usage attempt is marked `succeeded` with available token counts, or `failed` with a safe error category.

Unauthenticated, unauthorised, restricted, insufficient, duplicate, and over-limit requests fail before a new OpenAI call is made.

## Configurable limits

| Environment variable | Default | Purpose |
|---|---:|---|
| `GENERATION_RATE_LIMIT_ATTEMPTS` | 10 | Maximum requests per authenticated user in the short burst window. |
| `GENERATION_RATE_LIMIT_WINDOW_SECONDS` | 60 | Length of the short burst window. |
| `GENERATION_DAILY_LIMIT` | 50 | Maximum provider-bound attempts per user per UTC day, including failed attempts. |
| `GENERATION_CONCURRENT_LIMIT` | 2 | Maximum active provider-bound attempts per user. |
| `GENERATION_ATTEMPT_TIMEOUT_SECONDS` | 180 | Lease time before an abandoned active attempt is safely recovered. |
| `GENERATION_USAGE_RETENTION_DAYS` | 90 | Retention period for completed operational usage records. |
| `OPENAI_REQUEST_TIMEOUT` | 30 | Deadline for one OpenAI SDK request. |
| `OPENAI_MAX_OUTPUT_TOKENS` | 800 | Server-wide output cap that user input cannot increase. |
| `OPENAI_MAX_RETRIES` | 2 | Bounded SDK retry budget for eligible temporary failures. |

The short burst limiter protects one API process. The daily, concurrency, and duplicate controls use PostgreSQL transactions and per-user advisory locks, so they remain consistent when multiple backend instances share the same database.

## Duplicate request policy

The optional `Idempotency-Key` header is hashed with the authenticated user ID before storage.

- If the same completed request is submitted again, the existing private draft is returned without another OpenAI call.
- If the same request is still active, the API returns HTTP 409 with `generation_in_progress` and a `Retry-After` header.
- If a key is reused for different article or preference inputs, the API returns HTTP 409 with `idempotency_key_conflict`.
- A failed request may be retried after its active attempt is closed. Each provider-bound retry counts towards the daily allowance.

Raw idempotency values are not stored. The database keeps only a SHA-256 request fingerprint.

## Usage record

Migration `20261030_0009` creates `generation_usage_events`. Each row stores only operational metadata:

- User ownership identifier.
- Hashed request fingerprint.
- Status: `started`, `succeeded`, or `failed`.
- Generation run identifier after a successful save.
- Model identifier after success.
- Input, output, and total token counts when OpenAI supplies them.
- Safe error category after failure.
- Creation, lease-expiry, and completion timestamps.

The table does not store a prompt, article text, generated draft, API key, provider error body, or raw idempotency key. Old completed usage rows are deleted according to the configured retention period when that user next reserves an attempt. Expired `started` rows become failed `generation_abandoned` records before new limits are calculated.

## Error categories

| Category | Retry classification | Meaning |
|---|---|---|
| `ai_authentication_error` | Non-retryable until configuration changes | OpenAI rejected the server credential. |
| `ai_rate_limit_error` | Retryable after the provider or SDK delay | A temporary provider rate limit remained after bounded SDK retries. |
| `ai_quota_error` | Non-retryable until configuration or budget changes | The provider account or project has no available usage quota. |
| `ai_timeout` | Retryable | The bounded provider request timed out. |
| `ai_service_unavailable` | Retryable | A connection or temporary provider failure occurred. |
| `ai_invalid_response` | Non-retryable for the same response | The provider returned incomplete or empty output. |
| `ai_configuration_error` | Non-retryable until configuration changes | Required server-side AI configuration is unavailable. |
| `generation_validation_error` | Usually non-retryable for the same input | Generated output failed schema, length, sufficiency, or grounding rules. |
| `generation_storage_error` | Retryable after storage recovery | PostgreSQL could not save the draft. |
| `generation_abandoned` | Retryable | An active lease expired before completion. |
| `generation_unexpected_error` | Investigate before retrying repeatedly | A safe fallback category for an unexpected workflow failure. |

API clients also receive stable control codes:

| Condition | HTTP | Code |
|---|---:|---|
| Short burst or daily allowance reached | 429 | `generation_limit_exceeded` |
| Concurrent allowance reached | 429 | `generation_concurrency_limit` |
| Identical request already active | 409 | `generation_in_progress` |
| Shared usage controls unavailable | 503 | `generation_usage_unavailable` |
| OpenAI timeout | 504 | `openai_timeout` |
| Temporary OpenAI rate limit | 503 | `openai_rate_limited` |
| OpenAI authentication or quota problem | 503 | Safe provider-specific code |
| Invalid model response | 502 | Safe validation or provider-response code |

Limit and temporary provider responses include `Retry-After` when a safe delay is available.

## Retry policy

NewsFlow AI configures the official OpenAI Python SDK with a finite timeout and `OPENAI_MAX_RETRIES`. The application does not add a second nested retry loop. This keeps the maximum number and duration of attempts bounded.

OpenAI documents that temporary rate limits and selected server errors can be retried with exponential backoff, while authentication failures require the credential or organisation configuration to be corrected. It also recommends respecting `Retry-After` and distinguishing temporary rate limits from billing or quota failures. NewsFlow AI therefore:

- Allows the configured SDK retry budget for eligible temporary errors.
- Marks authentication, invalid request, malformed response, and quota failures as non-retryable.
- Preserves a bounded numeric `Retry-After` value for temporary rate-limit responses when supplied.
- Never retries missing source rights, insufficient permitted information, user validation failures, or configuration errors.

References:

- [OpenAI API error guidance](https://developers.openai.com/api/docs/guides/error-codes)
- [OpenAI rate-limit guidance](https://developers.openai.com/api/docs/guides/rate-limits)
- [OpenAI Python SDK reference](https://developers.openai.com/api/reference/python)

## Logging and privacy

Structured operational events include only safe fields such as status, attempt ID, duration, model identifier after success, token counts, and error category. They exclude:

- OpenAI API keys and database credentials.
- Email addresses and raw user IDs.
- Raw idempotency keys and request fingerprints.
- Prompts, article titles, article content, generated drafts, and source URLs.
- Provider response bodies, exception messages, and tracebacks in API responses.

The API continues to return the shared safe JSON structure:

```json
{
  "error": {
    "code": "generation_limit_exceeded",
    "message": "You have reached your current generation limit."
  }
}
```

## Operational troubleshooting

### A user reaches the daily limit

1. Confirm the `generation_limit_exceeded` response and `Retry-After` header.
2. Review safe usage statuses and counts for the user through an authorised database or future administrator tool.
3. Do not manually delete evidence merely to bypass a cost control.
4. Change `GENERATION_DAILY_LIMIT` only after a budget and abuse-risk review.

### Attempts remain active

1. Check backend availability and OpenAI timeout events.
2. Confirm `GENERATION_ATTEMPT_TIMEOUT_SECONDS` is longer than the configured provider request deadline and bounded retries.
3. Expired leases are automatically marked `generation_abandoned` on the user's next reservation.
4. Do not expose request fingerprints or user identifiers in public logs or Jira comments.

### OpenAI rate limits requests

1. Check the safe `ai_rate_limit_error` category and provider request ID if present.
2. Respect the returned `Retry-After` delay.
3. Review provider limits and application traffic before changing retry or concurrency settings.
4. Do not increase retries and concurrency together without a cost and availability review.

### Authentication or quota fails

1. Confirm whether the safe category is authentication or quota related.
2. Verify the ignored `.env` or deployment secret manager without printing the key.
3. Review the correct OpenAI project, organisation, and usage limits.
4. Restart the backend after correcting deployment configuration.

## Automated evidence

- `test_generation_usage.py` verifies configuration boundaries, daily, concurrent, duplicate, unavailable, success, failure, token, and safe-log behaviour with isolated doubles.
- `test_generation_usage_integration.py` safety-gates a disposable PostgreSQL proof of shared duplicate, concurrent, and daily limits plus failure status persistence.
- `test_linkedin_generation_service.py` verifies that usage reservation wraps provider access and records tokens or safe timeout failure categories.
- `test_openai_service.py` verifies authentication, temporary rate limiting, `Retry-After`, quota classification, timeout, temporary availability, invalid responses, token usage, and sensitive-data protection without a live request.
- Generation API tests verify safe HTTP codes, retry headers, authentication before service access, and the unchanged provider-call boundary.
- Migration tests verify the new table, fields, constraints, indexes, upgrade, and rollback path.

All provider responses and source records used by these tests are synthetic. No automated test calls OpenAI, uses live CNN content, reads a real API key, or creates a billable request.

The safety-gated PostgreSQL integration test passed against a separate disposable Docker database on 30 October 2026. The local frontend, rebuilt FastAPI backend, and PostgreSQL services then reported healthy; `/health` returned `status: ok`, `/ready` confirmed the database connection, and Alembic reported `20261030_0009 (head)`.

## Acceptance criteria review

- [x] Consistent retryable and non-retryable error strategy defined.
- [x] Authentication, rate limit, timeout, temporary failure, quota, and invalid-response handling implemented.
- [x] Bounded SDK retry, timeout, and output-token configuration retained.
- [x] Short burst, daily, concurrent, and duplicate-request controls implemented.
- [x] Shared PostgreSQL enforcement supports multiple backend instances.
- [x] Request counts, statuses, model identifier, and available token usage recorded.
- [x] Safe API responses and `Retry-After` behaviour implemented.
- [x] Unauthenticated and rights-denied requests fail before OpenAI access.
- [x] Sensitive prompts, content, credentials, and provider details excluded from usage records and operational logs.
- [x] Automated unit and PostgreSQL integration tests added.
- [x] Configuration, retry policy, and troubleshooting documented.

## Limitations and next steps

- Cost is not calculated in business logic because model pricing can change. Token usage is recorded so a reviewed reporting layer can apply current pricing later.
- The process-local burst limiter is not shared, but the cost-sensitive daily, concurrent, and duplicate controls are shared through PostgreSQL.
- Usage records currently have no public or user-facing endpoint. Any future reporting endpoint must enforce owner or administrator authorisation and expose only necessary fields.
- If generation work moves to a queue, the worker must renew or replace the current lease model while preserving the same limits and safe statuses.
