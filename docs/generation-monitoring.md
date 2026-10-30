# NFA-45 Generation Monitoring and Audit

## Purpose

NFA-45 adds operational visibility to the NewsFlow AI LinkedIn generation workflow. It helps an authorised administrator answer whether a request started, which safe decision stopped it, whether OpenAI failed, how long it took, and what token metadata was reported.

The monitoring system deliberately does not store complete prompts, article content, generated drafts, API keys, passwords, session tokens, provider response bodies, or stack traces.

## Monitoring strategy

The implementation uses two related PostgreSQL records:

- `generation_audit_events` records the complete content-free request lifecycle, including events that occur before an OpenAI call.
- `generation_usage_events`, introduced by NFA-43, remains the source for provider-attempt status and available input, output, and total token counts.

This avoids duplicating token records while still capturing rights denials, validation failures, and short-term or shared usage rejections. Every new request receives a random `generation_request_id`. All lifecycle events for that request use the same identifier.

Metrics are calculated from these stored records. Metrics contain aggregate counts and never use user IDs or article IDs as labels.

## Audit event definitions

| Event | Meaning | Safe details |
|---|---|---|
| `generation_started` | Authenticated generation processing began. | Request, user, article, and time identifiers. |
| `generation_rights_verified` | Current rights allowed AI generation. | Stable rights decision category. |
| `generation_rights_denied` | Current rights prevented use. | Stable denial category, not confidential source content. |
| `generation_usage_rejected` | A rate, daily, concurrency, or duplicate control rejected the request. | Stable error category. |
| `generation_validation_passed` | The generated output passed blocking automated checks. | Validation status and prompt version. |
| `generation_validation_failed` | Source sufficiency, output, length, or grounding validation failed. | Stable validation code and prompt version. |
| `generation_completed` | A private draft was created or an idempotent result was reused. | Duration, generation run, usage event, model identifier, and prompt version. |
| `generation_failed` | The request ended unsuccessfully. | Duration, usage event when available, and safe error category. |

Automated validation is not a factual guarantee. Every completed draft still requires human review.

## Stored fields

Each audit row can contain:

- Audit event ID.
- Generation request ID.
- Authenticated user ID.
- Selected article ID.
- Event type and status.
- UTC event time.
- Completed request duration in milliseconds.
- Generation run and NFA-43 usage event IDs when available.
- Configured model identifier and prompt version when relevant.
- Stable error, rights, and validation categories.

The table has no column for a prompt, article body, permitted-content text, generated draft, API key, or credential. Structured application logs use the request identifier, event name, status, duration, model identifier, and error category only.

## Protected administration API

The following endpoints require an active authenticated session belonging to a user whose PostgreSQL role is `admin`:

```text
GET /api/admin/generations/audit
GET /api/admin/generations/metrics
```

`GET /api/admin/generations/audit` accepts:

- `limit` from 1 to 100, default 50.
- Optional `generation_request_id` to follow one request.
- Optional `event_type` to inspect one lifecycle event type.

`GET /api/admin/generations/metrics` accepts an optional `window_hours` from 1 to 168. The default is `GENERATION_MONITORING_WINDOW_HOURS`, which is 24 hours.

The metric response contains:

- Total, successful, failed, and still-active request counts.
- Rights, validation, and usage rejection counts.
- OpenAI timeout and rate-limit counts.
- Average completed request duration.
- Provider attempt and available input, output, and total token counts.
- Counts grouped by safe error category.

An ordinary authenticated user receives `403 administrator_required`. An unauthenticated caller receives `401`. Monitoring storage failure produces a safe `503` without database or provider details.

## Retention

Generation audit records are retained for 90 days by default. Configure a value from 1 to 730 days with:

```dotenv
GENERATION_AUDIT_RETENTION_DAYS=90
```

The audit service removes records older than the configured period when a new audited generation starts. NFA-43 usage events use their existing `GENERATION_USAGE_RETENTION_DAYS` policy. A future production deployment should also schedule the same retention operation so expiry does not depend only on new traffic.

Changing the retention period requires a privacy, security, troubleshooting, legal, and storage review. Retention must not be extended indefinitely without a documented reason.

## Database migration

Apply migration `20261030_0010` before running the updated backend:

```bash
cd apps/api
alembic upgrade head
```

The migration creates `generation_audit_events`, its constraints, foreign keys, and indexes. It does not copy prompts, drafts, or article content into the table.

## Failure investigation

1. Obtain the `generation_request_id` from a safe operational event or audit response.
2. Sign in as an administrator and query `/api/admin/generations/audit?generation_request_id=<id>`.
3. Confirm that `generation_started` exists.
4. Check for `generation_rights_denied`, `generation_usage_rejected`, or `generation_validation_failed` before the terminal event.
5. Inspect the `generation_failed` error category.
6. Compare the aggregate metrics window for repeated timeouts, rate limits, validation failures, or rights rejections.
7. Use the linked `usage_event_id` to inspect available NFA-43 status and token metadata when a provider attempt occurred.
8. Investigate provider health for `ai_timeout`, `ai_rate_limit_error`, or `ai_service_unavailable`. Investigate application configuration for `ai_configuration_error`. Investigate source permission records for a rights denial.

Do not paste `.env`, API keys, prompts, article content, generated drafts, cookies, or raw provider errors into Jira, logs, screenshots, or support messages.

## Automated evidence

| Requirement | Evidence |
|---|---|
| Start, rights, validation, completion, failure, and rejection events | `tests/test_generation_audit.py` and `tests/test_linkedin_generation_service.py` |
| Correlation and duration | `tests/test_generation_audit.py` |
| Success, failure, error, rejection, duration, and token metrics | `tests/test_generation_audit.py` |
| Administrator access and ordinary-user denial | `tests/test_admin_generation_monitoring.py` |
| Sensitive-data minimisation | `tests/test_generation_audit.py` |
| Configuration bounds | `tests/test_config.py` |
| Table, columns, indexes, migration, and rollback | `tests/test_migrations_integration.py` |

Run the focused routine tests from the repository root:

```bash
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_generation_audit.py \
  apps/api/tests/test_admin_generation_monitoring.py \
  apps/api/tests/test_linkedin_generation_service.py \
  apps/api/tests/test_generation_api.py \
  apps/api/tests/test_linkedin_generation_api.py \
  apps/api/tests/test_config.py
```

These tests use synthetic identifiers, articles, drafts, and provider outcomes. They do not call CNN or OpenAI.

## Limitations and next operational steps

- Metrics are calculated on demand from a maximum of 50,000 audit events in the requested window. A higher-volume deployment should export bounded aggregate metrics to an approved monitoring platform.
- This task provides protected inspection but does not configure an external alert receiver, dashboard, pager, or log destination.
- Retention is applied during audited request startup. Production should also run reviewed scheduled cleanup.
- Audit access relies on the existing user role. Production access must follow least privilege and administrative account review.
- Audit records support investigation but do not replace human review, provider billing records, incident response, or legal review.

## Review status

- Jira issue: NFA-45
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
