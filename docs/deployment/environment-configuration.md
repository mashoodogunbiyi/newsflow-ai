# NewsFlow AI environment configuration

## 1. Purpose

This guide classifies the configuration used by the current NewsFlow AI repository and explains how it should be supplied in a future approved deployment. It contains names and safe examples only. It does not contain real credentials.

The root `.env.example` is a local-development template. The ignored `.env` file is appropriate for a developer workstation, but a deployment must use the hosting platform's configuration and managed secret facilities.

## 2. Configuration rules

- Store secrets only in an approved managed secret store.
- Grant each runtime identity access only to the secrets it needs.
- Never expose a secret through a `NEXT_PUBLIC_` setting.
- Never commit `.env`, database passwords, provider keys, storage credentials, or exported platform configuration.
- Keep staging and production values separate from development and from each other.
- Use secret references or runtime injection. Do not bake environment values into container images.
- Validate configuration before traffic is enabled, and fail closed when a required value is absent.
- Redact secret values from logs, support messages, screenshots, and Jira evidence.
- Rotate a secret after suspected exposure and verify that the previous value is revoked.

## 3. Required deployment configuration

| Variable | Location and sensitivity | Deployment rule |
| --- | --- | --- |
| `APP_ENV` | Backend, non-secret | Must be `production` in production and `staging` in staging. This controls secure session cookies and storage safeguards. |
| `DATABASE_URL` | Backend secret | Required at API startup. Use the private PostgreSQL TLS connection string from the secret store. Never expose it to Next.js browser code. |
| `FRONTEND_ORIGIN` | Backend, non-secret | Exact public HTTPS frontend origin with no trailing slash, for example `https://newsflow.example`. |
| `API_INTERNAL_BASE_URL` | Next.js server, non-secret | Private FastAPI origin available to the Next.js server, for example an internal service address. It must not contain credentials. |
| `NEXT_PUBLIC_API_BASE_URL` | Browser-visible, non-secret | Public API origin only if the selected architecture needs one. Prefer same-origin gateways. Never place a key or password here. |
| `NEWS_SOURCE_MODE` | Backend, non-secret | Must remain `disabled` in production. `fixture` is permitted only for controlled synthetic demonstrations. No live CNN mode exists. |
| `LOG_LEVEL` | Backend, non-secret | Use the approved operational level, normally `INFO`; do not enable verbose production logging without a reviewed reason. |
| `LOG_FORMAT` | Backend, non-secret | Use `json` for a structured production log sink. |

`DATABASE_URL` is the only setting the current FastAPI process always requires to start. Provider credentials are conditional because the application can run with their features disabled.

## 4. Conditional provider and storage configuration

| Variable | Location and sensitivity | Deployment rule |
| --- | --- | --- |
| `OPENAI_API_KEY` | Backend secret | Configure only after provider, privacy, security, model, and spending approval. Required only when an OpenAI feature runs. |
| `OPENAI_MODEL` | Backend, non-secret | Approved text model identifier. It must be set before text generation runs. |
| `OPENAI_IMAGE_MODEL` | Backend, non-secret | Approved image model identifier. The current default is development configuration, not evidence of production approval. |
| `IMAGE_STORAGE_BACKEND` | Backend, non-secret | The only implemented value is `local`. It is deliberately rejected in staging and production. A new approved adapter and configuration contract are required before deployment. |
| `IMAGE_STORAGE_LOCAL_ROOT` | Backend, non-secret | Development and test path only. Do not map it to production and call it object storage. |

OpenAI and image-generation controls:

| Variable | Current default | Purpose |
| --- | ---: | --- |
| `OPENAI_REQUEST_TIMEOUT` | `30` | Text provider request timeout in seconds. |
| `OPENAI_MAX_OUTPUT_TOKENS` | `800` | Maximum requested text output tokens. |
| `OPENAI_MAX_RETRIES` | `2` | Bounded text provider retry count. |
| `IMAGE_GENERATION_TIMEOUT` | `120` | Image provider timeout in seconds. |
| `IMAGE_GENERATION_MAX_CONCURRENT_REQUESTS` | `2` | Process-level image request concurrency. |
| `IMAGE_GENERATION_MAX_RETRIES` | `1` | Bounded retry count for supported safe cases. |
| `IMAGE_GENERATION_RETRY_BASE_SECONDS` | `1` | Base delay for an allowed retry. |
| `IMAGE_GENERATION_MAX_RESPONSE_BYTES` | `26214400` | Maximum provider response size. |
| `IMAGE_GENERATION_DUPLICATE_CACHE_SIZE` | `100` | In-process duplicate request cache capacity. |
| `IMAGE_STORAGE_MAX_BYTES` | `10485760` | Maximum validated stored image size. |
| `IMAGE_STORAGE_MAX_PIXELS` | `4000000` | Maximum validated image pixel count. |

Process-level limits do not replace shared deployment controls. A public multi-instance service also needs platform-level rate limits, budgets, quotas, and an emergency stop.

## 5. Backend configuration reference

### 5.1 Database and request boundary

| Variable | Default | Validation and operational meaning |
| --- | ---: | --- |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` | `5` | Bounded from 1 to 30 seconds. Used for startup and readiness connectivity. |
| `API_MAX_REQUEST_BODY_BYTES` | `1048576` | Bounded JSON request-body limit. The edge must enforce a matching or stricter limit. |

### 5.2 Authentication and sessions

| Variable | Default | Validation and operational meaning |
| --- | ---: | --- |
| `REGISTRATION_RATE_LIMIT_ATTEMPTS` | `5` | In-process registration attempts in one window. |
| `REGISTRATION_RATE_LIMIT_WINDOW_SECONDS` | `60` | Registration window length. |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | `5` | In-process login attempts in one window. |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | `60` | Login window length. |
| `SESSION_LIFETIME_MINUTES` | `60` | Absolute server-managed session lifetime. Production cookies become Secure through `APP_ENV`. |

The application uses random server-managed sessions stored as hashes in PostgreSQL. It does not currently require a `SESSION_SECRET`. Do not invent or document an unused secret as if it were implemented.

### 5.3 Article synchronisation and ingestion monitoring

| Variable | Default | Purpose |
| --- | ---: | --- |
| `ARTICLE_SYNC_INTERVAL_SECONDS` | `14400` | Proposed scheduler interval. A production scheduler is not currently provided. |
| `ARTICLE_SYNC_PAGE_SIZE` | `50` | Maximum provider page size within the validated range. |
| `ARTICLE_SYNC_MAX_RETRIES` | `2` | Bounded synchronisation retries. |
| `ARTICLE_SYNC_RETRY_BASE_SECONDS` | `1` | Retry base delay. |
| `ARTICLE_SYNC_LEASE_SECONDS` | `300` | Durable synchronisation lease duration. |
| `MANUAL_SYNC_RATE_LIMIT_ATTEMPTS` | `2` | Administrator manual-sync attempts per window. |
| `MANUAL_SYNC_RATE_LIMIT_WINDOW_SECONDS` | `60` | Manual-sync rate window. |
| `INGESTION_METRICS_ENABLED` | `true` | Enables safe ingestion metrics. |
| `INGESTION_METRICS_WINDOW_HOURS` | `24` | Default metrics window. |
| `INGESTION_FAILURE_THRESHOLD` | `3` | Consecutive failure health threshold. |
| `INGESTION_SUCCESS_STALE_SECONDS` | `21600` | Age after which last success is considered stale. |
| `INGESTION_LONG_RUNNING_SECONDS` | `600` | Long-running job threshold. |
| `INGESTION_REJECTION_RATE_PERCENT` | `25` | Rejected-record percentage threshold. |

These values do not authorise a news provider. In production, `NEWS_SOURCE_MODE=disabled` remains mandatory until rights approval changes.

### 5.4 Generation usage, audit, and retention

| Variable | Default | Purpose |
| --- | ---: | --- |
| `GENERATION_RATE_LIMIT_ATTEMPTS` | `10` | Per-user burst attempts per window. |
| `GENERATION_RATE_LIMIT_WINDOW_SECONDS` | `60` | Burst limit window. |
| `GENERATION_DAILY_LIMIT` | `50` | Shared PostgreSQL per-user daily allowance. |
| `GENERATION_CONCURRENT_LIMIT` | `2` | Shared active-attempt allowance per user. |
| `GENERATION_ATTEMPT_TIMEOUT_SECONDS` | `180` | Age after which an unfinished reservation can be reconciled. |
| `GENERATION_USAGE_RETENTION_DAYS` | `90` | Usage-record retention. Review against final privacy policy. |
| `GENERATION_AUDIT_RETENTION_DAYS` | `90` | Content-free generation audit retention. |
| `GENERATION_MONITORING_WINDOW_HOURS` | `24` | Default administrator metric window. |

### 5.5 Deletion and cleanup

| Variable | Default | Purpose |
| --- | ---: | --- |
| `DRAFT_DELETION_RETENTION_DAYS` | `30` | Retained deleted-draft content window before redaction. |
| `DELETION_AUDIT_RETENTION_DAYS` | `365` | Minimal deletion evidence retention. |
| `IMAGE_CLEANUP_RETRY_SECONDS` | `300` | Failed private-object cleanup retry delay. |

A production scheduler for retention and cleanup jobs is still required. Backup retention must not silently defeat deletion policy.

### 5.6 Seed control

| Variable | Default | Purpose |
| --- | ---: | --- |
| `SEED_DATA_ENABLED` | `false` | Explicit safety gate for development seed loading. Keep false in staging and production. |

## 6. Docker-only local variables

These values support `compose.yaml` and are not the proposed production database-secret design:

| Variable | Sensitivity | Local purpose |
| --- | --- | --- |
| `POSTGRES_USER` | Local credential | Creates the local Compose database user. |
| `POSTGRES_PASSWORD` | Local secret | Creates the local Compose database password. |
| `POSTGRES_DB` | Non-secret | Creates the local database name. |
| `POSTGRES_PORT` | Non-secret | Host port bound to loopback. |
| `BACKEND_PORT` | Non-secret | Host FastAPI port bound to loopback. |
| `FRONTEND_PORT` | Non-secret | Host Next.js port bound to loopback. |

Use managed-database identities and secret references in deployment. Do not expose a production PostgreSQL port publicly.

## 7. Environment comparison

| Control | Development | Staging | Production |
| --- | --- | --- | --- |
| `APP_ENV` | `development` | `staging` | `production` |
| Source mode | `fixture` or `disabled` | `disabled` until approved | `disabled` until approved |
| Data | Synthetic | Synthetic or specifically approved test data | Real data only after privacy and rights approval |
| Session cookie Secure flag | Not required on localhost | Required | Required |
| PostgreSQL | Local Compose allowed | Managed private service | Managed private service |
| Image storage | Local adapter allowed | Blocked until approved adapter exists | Blocked until approved adapter exists |
| OpenAI | Optional local key | Disabled until deployment approval | Disabled until deployment approval |
| Secrets | Ignored `.env` allowed | Managed secret store | Managed secret store |
| HTTPS | Local exception | Required | Required |
| Seed loading | Explicit synthetic use only | Disabled | Disabled |

## 8. Secret lifecycle

1. An accountable owner requests a secret for one documented purpose.
2. The security owner approves scope, environment, and permitted identities.
3. The platform stores the secret and injects it only at runtime.
4. Access is logged and periodically reviewed.
5. Rotation is tested without printing either the previous or replacement value.
6. Suspected exposure triggers revocation, replacement, log review, and incident recording.
7. Offboarding removes identities and secret access.

Do not place secret values in CLI history, pull-request descriptions, Jira comments, screenshots, test fixtures, image layers, build arguments, or monitoring labels.

## 9. Configuration validation

Before enabling traffic:

- Confirm the selected environment has all required names without printing values.
- Confirm `APP_ENV`, `FRONTEND_ORIGIN`, and provider feature flags match the release decision.
- Confirm the backend starts and `GET /ready` returns a safe successful response.
- Confirm missing `DATABASE_URL` prevents startup with a clear error.
- Confirm missing provider configuration affects only the disabled provider feature.
- Confirm `APP_ENV=production` rejects the current local image-storage adapter.
- Confirm the Next.js build does not contain backend-only secret names or values.
- Confirm `.env` remains ignored with `git check-ignore .env`.
- Run `python3 scripts/scan_secrets.py` before release.

## 10. Known limitations

- The repository has no production object-storage setting because the adapter has not been implemented.
- No managed secret provider has been selected or integrated.
- No production environment configuration has been created or tested.
- No provider key should be configured until the corresponding release gates are approved.
- Application-level in-memory limits require shared edge controls in a multi-instance deployment.
- Values in `.env.example` are development examples, not recommended production values.

## 11. Related documents

- [Deployment guide](deployment-guide.md)
- [Operations runbook](operations-runbook.md)
- [Backup and recovery](backup-and-recovery.md)
- [Backend configuration implementation](../../apps/api/app/core/config.py)
- [Safe local template](../../.env.example)
