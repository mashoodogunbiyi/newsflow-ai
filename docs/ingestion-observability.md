# NFA-35 - Article Ingestion Observability

## Purpose

This document defines how NewsFlow AI records, measures, inspects, and responds to article-ingestion activity. It extends the durable synchronisation jobs introduced by NFA-33. It does not create a separate or conflicting job store.

Live CNN access remains blocked. All current ingestion monitoring uses the authorised synthetic fixture provider.

## Operational flow

```text
Scheduled or administrator trigger
             |
             v
      ArticleSyncService
        |            |
        |            +--> safe structured log events
        v
PostgreSQL article_sync_jobs
        |
        +--> recent job and detail views
        +--> aggregate metrics
        `--> threshold-based health indicators
```

Every run has one UUID job identifier. The same identifier appears in durable PostgreSQL status and related log events, allowing an operator to correlate a problem without logging source content or credentials.

## Structured log events

The application can render logs as JSON or readable structured console text. JSON is the default because log collectors can reliably search and aggregate its fields.

| Event | Level | Meaning |
|---|---|---|
| `article_sync_started` | Info | A worker claimed a durable job. |
| `article_sync_provider_request_completed` | Info | One provider request completed and its duration was measured. |
| `article_sync_provider_request_failed` | Warning | A provider request failed with a safe category and code. |
| `article_sync_provider_retry` | Warning | A retry was scheduled using the bounded retry policy. |
| `article_sync_item_rejected` | Warning | A record failed validation or rights-aware ingestion. No article content or source identifier is included. |
| `article_sync_completed` | Info | A run completed without rejected records. |
| `article_sync_partially_completed` | Warning | Some work completed but one or more records or stages failed. |
| `article_sync_failed` | Warning | The job failed before useful processing completed. |
| `article_sync_checkpoint_deferred` | Error | Article work completed but the checkpoint update failed. |

Common fields include `job_id`, `provider_id`, `trigger_type`, `status`, `duration_ms`, `provider_duration_ms`, `counts`, `error_code`, `error_category`, and `failed_stage`.

The formatter uses an explicit field allowlist. It redacts common password, token, API-key, and connection-URL credential shapes. The ingestion workflow never logs article titles, descriptions, permitted content, canonical URLs, full provider responses, database URLs, session values, or API keys. Exceptions are converted to stable safe codes and summaries before they are stored or logged.

## Metrics

Metrics are derived from the existing `article_sync_jobs` records for a configurable time window. They include:

- Total, completed, failed, partially completed, interrupted, and active jobs.
- Retrieved, created, updated, skipped, and rejected article counts.
- Provider request attempts and provider-related job failures.
- Database-related job failures.
- Average total job duration.
- Average cumulative provider-request duration.

Provider request time is measured around every provider call, including failed attempts. Total job duration is derived from the durable start and completion timestamps. This avoids storing duplicate duration values that could disagree.

`INGESTION_METRICS_ENABLED=false` disables aggregate calculation while leaving job status and health inspection available. No third-party monitoring service is required for local development. A deployment can forward the JSON logs and protected metrics response to an approved platform later without changing the ingestion workflow.

## Error categories and stages

Failures use stable categories so dashboards and alert rules do not depend on changing exception text:

- `provider_connection_error`
- `provider_timeout`
- `provider_authentication_error`
- `provider_rate_limit_error`
- `article_validation_error`
- `database_error`
- `synchronisation_conflict`
- `source_authorisation_error`
- `internal_pipeline_error`

The `failed_stage` field narrows the location, such as `provider_request`, `provider_validation`, `validation`, `database`, `checkpoint`, `authorisation`, `synchronisation`, `worker`, or `pipeline`.

## Protected administrator endpoints

The following endpoints require a valid authenticated session and an active administrator role:

```text
GET /api/admin/sync/jobs
GET /api/admin/sync/jobs/{job_id}
GET /api/admin/sync/metrics
GET /api/admin/sync/health
```

`GET /api/admin/sync/jobs` accepts `limit` from 1 to 100 and an optional `provider_id`. `GET /api/admin/sync/metrics` accepts an optional `window_hours` from 1 to 168. Responses contain safe operational fields only. They do not expose credentials, raw provider payloads, restricted article content, internal agreement references, or traceback details.

The existing NFA-33 manual endpoint remains available at `POST /api/v1/admin/articles/sync`, and its individual status endpoint remains available at `GET /api/v1/admin/articles/sync/{job_id}`.

## Health indicators and thresholds

The health response can be `healthy`, `warning`, or `critical`.

| Indicator | Default threshold | Status |
|---|---:|---|
| Repeated terminal failures | 3 consecutive jobs | Critical |
| No recent successful completion | 6 hours | Warning |
| Long-running active job | 10 minutes | Warning |
| High recent article rejection rate | 25 percent | Warning |

If no threshold is breached, the response contains the `ingestion_operational` healthy indicator. Thresholds are environment variables so staging and production can reflect the deployed schedule and service-level expectations.

Recommended operational response:

1. Read `/api/admin/sync/health` and identify the indicator.
2. Read recent jobs and locate the affected job IDs.
3. Compare the stored `error_category`, `error_code`, and `failed_stage` with matching structured logs.
4. Check source authorisation before any provider configuration change.
5. Resolve the underlying provider, validation, database, or worker problem.
6. Run one authorised manual synchronisation if appropriate.
7. Confirm that a new successful job clears the failure sequence and updates the last-success time.

Do not work around source restrictions, disable validation, or log restricted data while troubleshooting.

## Configuration

| Variable | Default | Purpose |
|---|---:|---|
| `LOG_LEVEL` | `INFO` | Minimum application log level. |
| `LOG_FORMAT` | `json` | `json` for collection or `console` for readable local output. |
| `INGESTION_METRICS_ENABLED` | `true` | Enables aggregate metric calculation. |
| `INGESTION_METRICS_WINDOW_HOURS` | `24` | Default aggregate window. |
| `INGESTION_FAILURE_THRESHOLD` | `3` | Consecutive failures before critical health. |
| `INGESTION_SUCCESS_STALE_SECONDS` | `21600` | Maximum time since a successful run. |
| `INGESTION_LONG_RUNNING_SECONDS` | `600` | Active-job runtime warning threshold. |
| `INGESTION_REJECTION_RATE_PERCENT` | `25` | Recent rejection-rate warning threshold. |

These settings are non-secret. Provider credentials and database passwords remain in the ignored `.env` file or a deployment secret manager and must never be placed in log configuration.

## Database change

Migration `20261029_0006` adds `provider_failures`, `provider_duration_ms`, `error_category`, and `failed_stage` to `article_sync_jobs`. It also adds recent-job and status/time indexes. Counts, provider duration, and failure dimensions are constrained and version controlled. The migration supports rollback.

Apply it from `apps/api` with:

```bash
alembic upgrade head
```

## Verification

Run the focused fast tests from `apps/api`:

```bash
pytest tests/test_article_sync.py \
  tests/test_ingestion_observability.py \
  tests/test_admin_ingestion_observability.py
```

The tests cover start, completion, partial, and failure evidence; provider durations; metrics; provider and database categories; protected status APIs; repeated failures; stale success; sensitive-value redaction; and safe response fields. The migration integration test checks the new columns, constraints, indexes, upgrade, rollback, and rebuild against a deliberately disposable PostgreSQL database.

## Limitations and next steps

- Metrics are calculated from up to 10,000 jobs in the selected window, which is suitable for the current MVP. A higher-volume deployment should use database aggregates or an approved metrics system.
- Local health indicators do not send notifications. Deployment alert delivery must be configured in an approved monitoring platform with access controls and retention rules.
- The in-process rate limiter and one-shot scheduler remain development-oriented. A production deployment should use managed scheduling and shared rate limiting.
- Live CNN monitoring cannot be enabled until the NFA-5 authorisation gap and NFA-8 No-Go decision are formally resolved.

## Review status

- Jira issue: NFA-35
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
