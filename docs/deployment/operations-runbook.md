# NewsFlow AI operations runbook

## 1. Status and purpose

This is a proposed runbook for a future approved NewsFlow AI deployment. It is based on the current application behavior, but it has not been exercised in production because no production environment exists.

Public or production release remains No-Go. Live CNN ingestion remains disabled. Operators must not use this runbook to bypass release, rights, privacy, storage, or security gates.

## 2. Roles

Assign named people before deployment. One person may hold more than one role in a small team, but the responsibility must be explicit.

| Role | Responsibility |
| --- | --- |
| Product owner | Approves audience, feature scope, provider use, maintenance impact, and user communication. |
| Technical owner | Owns deployments, migrations, application health, rollback, and recovery coordination. |
| Security owner | Owns secrets, access, incident classification, evidence protection, and security release gates. |
| Data and rights owner | Owns source authorisation, permitted use, retention, deletion, and privacy decisions. |
| Incident commander | Coordinates one active incident, decisions, timestamps, owners, and communication. |

The current project owner is Mashood Ogunbiyi. Production role assignments remain pending.

## 3. Service inventory

| Component | Current operational function | Primary signal | Safe immediate action |
| --- | --- | --- | --- |
| Next.js frontend | Browser UI and same-origin backend gateways | HTTPS response, frontend error rate, browser checks | Stop new traffic or roll back the frontend image. |
| FastAPI backend | Authentication, articles, generation, storage, and content lifecycle | `GET /health`, `GET /ready`, HTTP error and latency metrics | Remove unhealthy instance, disable provider features, or roll back compatible code. |
| PostgreSQL | Accounts, sessions, provenance, drafts, history, audit, and operation state | `/ready`, database availability, connection and storage alarms | Stop writes, preserve evidence, and engage database recovery procedure. |
| Private image storage | Generated image bytes | Storage error and cleanup backlog | Disable image generation and delivery changes; preserve existing metadata. |
| OpenAI | Text and image generation | Safe provider result categories, latency, limits, and spend | Disable generation; do not retry uncertain paid requests. |
| News provider | Authorised article ingestion | Sync status, rights rejection, stale-success and failure thresholds | Set `NEWS_SOURCE_MODE=disabled` and stop sync jobs. |

## 4. Health checks

### Liveness

`GET /health` checks that the FastAPI process can answer. Its expected response is:

```json
{"status":"ok"}
```

It does not prove PostgreSQL, storage, OpenAI, or a news provider is healthy.

### Readiness

`GET /ready` performs a bounded PostgreSQL check and configuration validation. A ready response is:

```json
{
  "status": "ready",
  "database": "connected",
  "configuration": "valid"
}
```

An unavailable dependency returns a safe `503` without exposing a connection string. The platform should stop routing normal traffic to an instance that is not ready.

### Protected operational endpoints

These endpoints require an authenticated administrator and must not be exposed as public anonymous metrics:

- `GET /api/admin/sync/jobs`
- `GET /api/admin/sync/jobs/{job_id}`
- `GET /api/admin/sync/metrics`
- `GET /api/admin/sync/health`
- `GET /api/admin/generations/audit`
- `GET /api/admin/generations/metrics`

Use a least-privilege administrator account. Do not copy private content or secret-bearing output into tickets.

## 5. Logging and monitoring

Set `LOG_FORMAT=json` for deployment. Safe logs should include only approved operational fields such as:

- Timestamp.
- Request identifier.
- Event name and component.
- Safe user, job, generation, or draft identifiers where necessary.
- Status, error category, duration, retry count, and recovery state.
- Model identifier and token counts where already approved for generation audit.

Never log:

- Passwords, password hashes, session or CSRF tokens.
- `DATABASE_URL`, `OPENAI_API_KEY`, storage credentials, cookies, or request authorisation headers.
- Article content, private drafts, prompts, provider response bodies, user email addresses, or private image object keys.

Recommended deployment alerts, which are not yet configured, include:

- Readiness failure or elevated HTTP `5xx` rate.
- High request latency or exhausted application workers.
- PostgreSQL connection, storage, replication, or backup failure.
- Repeated login or abuse-limit activity.
- Generation provider authentication, timeout, rate-limit, or spend threshold events.
- Article synchronisation failures, stale success, excessive rejection, or long-running jobs.
- Image storage failure, integrity rejection, or cleanup backlog growth.
- Deletion or retention work that remains overdue.
- Secret, rights, or configuration drift.

Alert thresholds and recipients must be established using measured staging baselines. Do not invent a passing production baseline.

## 6. Routine operating schedule

### Each release

- Confirm the release decision, rights status, CI result, image digests, migrations, backup recovery point, and rollback compatibility.
- Verify health, authentication, owner isolation, safe logs, alerts, and blocked provider modes.
- Record deployment or rollback evidence.

### Daily when deployed

- Review availability, error rate, latency, provider failures, database capacity, backup status, and cleanup queues.
- Investigate failed or long-running sync and generation operations.
- Confirm source and provider feature flags still match the approved decision.

### Weekly

- Review administrator activity, secret access, dependency notices, usage and spending, stale sessions, cleanup retries, and retention work.
- Confirm monitoring contacts and escalation paths remain valid.

### Monthly

- Review user access, administrator assignments, source rights, provider terms, privacy retention, capacity, patch status, risk register, and unresolved incidents.
- Confirm backup restore exercises and incident rehearsals are on schedule.

### Quarterly or after material change

- Run an isolated restore exercise.
- Rehearse one dependency outage and one security incident.
- Review threat model, recovery targets, deployment architecture, rights decision, and this runbook.

## 7. Startup procedure

1. Confirm an approved change record and assigned operator.
2. Verify networking, secret store, PostgreSQL, object storage, log sink, and monitoring.
3. Verify the intended migration revision and run the one-off migration job.
4. Start FastAPI and wait for `/health` and `/ready`.
5. Start Next.js and verify private API connectivity.
6. Start only approved scheduled workers.
7. Route synthetic verification traffic, then approved user traffic.
8. Observe logs, metrics, database connections, and errors during the agreed watch period.

For local development only:

```bash
docker compose up --build --detach --wait
docker compose ps
docker compose logs --tail=100
```

## 8. Shutdown procedure

1. Record the reason and announce the maintenance state to affected users.
2. Stop new traffic and scheduled work.
3. Allow bounded in-flight operations to finish.
4. Record uncertain generation or storage operations for reconciliation.
5. Stop frontend and backend instances gracefully.
6. Verify no migration, retention, or cleanup job is active.
7. Keep persistent database, storage, logs, and evidence intact.

For local development only:

```bash
docker compose down
```

Do not add `--volumes` when data must be preserved.

## 9. Incident classification and first response

Use the organisation's approved severity system. Until one is selected, treat any of the following as urgent and stop the affected feature:

- Suspected secret, account, session, private content, or personal-data exposure.
- Cross-user access or public object access.
- Data corruption, unexplained deletion, or backup failure.
- Unauthorised source retrieval or rights violation.
- Uncontrolled provider spending or repeated duplicate paid requests.
- Sustained inability to authenticate, save content, or protect ownership.

First response:

1. Assign an incident commander and start a timestamped record.
2. Protect users by disabling the smallest affected feature or stopping traffic.
3. Preserve safe logs, request identifiers, image digests, migration state, and configuration version without copying secrets or private content unnecessarily.
4. Revoke exposed credentials or sessions when required.
5. Identify whether data integrity, confidentiality, rights, or provider cost is affected.
6. Follow the relevant procedure below.
7. Restore service only after verification and accountable approval.
8. Record root cause, impact, recovery, follow-up owners, and deadlines.

## 10. Recovery procedures

### 10.1 PostgreSQL unavailable

1. Confirm `/ready` fails while `/health` may still succeed.
2. Stop or reject writes; do not report successful changes that cannot commit.
3. Check managed-service availability, credentials, TLS, connection capacity, storage, and recent migrations.
4. Do not loop application retries against an unavailable database.
5. If restoration is required, follow [backup and recovery](backup-and-recovery.md) in an isolated target first.
6. Verify migration head, ownership checks, sessions, deletion tombstones, and storage reconciliation before reopening traffic.

### 10.2 OpenAI unavailable, rate limited, or uncertain

1. Preserve the user's selected article and edited draft.
2. Return the controlled provider error and retain safe operation evidence.
3. Do not retry authentication, validation, or permanent policy errors.
4. Do not automatically retry an uncertain image timeout that may have incurred cost.
5. Disable generation when failures or spending cross the approved threshold.
6. Restore only after a controlled synthetic or approved test succeeds.

### 10.3 Private image storage unavailable

1. Disable new image generation and storage-changing operations.
2. Do not create a false successful database record when bytes were not stored.
3. Preserve existing draft text and original image metadata during failed regeneration.
4. Record orphan candidates or pending cleanup through the existing safe recovery state.
5. After storage returns, run bounded reconciliation and verify digest, ownership, and object presence before clearing evidence.

### 10.4 Article ingestion failure or rights concern

1. Set `NEWS_SOURCE_MODE=disabled` and stop manual and scheduled synchronisation.
2. Do not scrape or switch to an unapproved source.
3. Preserve the authorisation evidence and affected provider/job identifiers.
4. Keep already stored records subject to their current rights status; do not generate from expired or restricted rights.
5. Resume only after the data and rights owner records approval.

### 10.5 Suspected secret exposure

1. Disable the affected feature or identity.
2. Revoke and replace the secret in the provider and managed secret store.
3. Review access logs and safe application events for misuse.
4. Redeploy or restart only the components that need the replacement.
5. Verify the previous value no longer works and scan repository history and artifacts.
6. Record notification and follow-up obligations without placing the secret in the incident record.

### 10.6 Failed migration or release

1. Stop new application traffic and do not rerun the migration blindly.
2. Capture the current Alembic revision and database error safely.
3. Determine whether the migration was transactional and whether partial changes exist.
4. Prefer a reviewed forward fix.
5. Use an application rollback only when the current schema is backward compatible.
6. Use a data restore only through the approved recovery procedure and only after impact approval.

### 10.7 Partial deletion or retention failure

1. Keep active user access removed after the deletion transaction succeeds.
2. Preserve cleanup status and retry evidence.
3. Do not delete a shared image object while an active owned record still references it.
4. Run the idempotent cleanup and redaction workers after the dependency returns.
5. Alert when retry age or backlog exceeds the approved threshold.
6. After a restore, reapply deletion tombstones before reopening access.

## 11. Deployment verification and rollback

Use the checklists in the [deployment guide](deployment-guide.md). A failed mandatory check makes the release No-Go. Application rollback must use the previous approved immutable image and must first confirm database compatibility. Database restoration is a separate incident action and must not be used as a convenient code rollback.

## 12. Known operational limitations

- No production environment, monitoring platform, alert routing, or incident rota exists.
- No production object-storage adapter or reconciliation inventory exists.
- No production scheduler currently runs article sync, retention, or cleanup work.
- No production backup or restore has been implemented or proven.
- In-process authentication and some provider controls require shared deployment enforcement.
- Rights and production provider approvals are not complete.
- The current operations guidance needs provider-specific commands after a hosting platform is selected.

## 13. Related documents

- [Deployment guide](deployment-guide.md)
- [Environment configuration](environment-configuration.md)
- [Backup and recovery](backup-and-recovery.md)
- [Reliability controls](../reliability-and-recovery.md)
- [Ingestion observability](../ingestion-observability.md)
- [Generation monitoring](../generation-monitoring.md)
