# NewsFlow AI deployment guide

## Document control

| Field | Value |
| --- | --- |
| Jira issue | NFA-85 |
| Status | Proposed deployment design - not deployed |
| Last reviewed | 2026-11-05 |
| Application owner | Mashood Ogunbiyi |
| Review basis | Current repository configuration, NFA-82 release decision, NFA-84 Docker package, and NFA-75 security gates |

## 1. Purpose and release boundary

This guide explains how NewsFlow AI could be deployed in an approved hosting environment. It does not claim that a staging or production deployment, production backup, production monitor, or live provider connection exists.

The current decision is:

- Controlled local demonstration with synthetic data: Conditional Go.
- Public or production release: No-Go.
- Live CNN ingestion: No-Go until written authorisation and a new architecture decision approve a specific access method.
- OpenAI use in a deployed environment: blocked until provider terms, privacy, model, budget, and operational controls are approved.
- Generated-image storage in staging or production: blocked until the development-only local adapter is replaced by an approved private object-storage adapter.

The release gates in [NFA-82](../release-readiness-quality-signoff.md) and [NFA-75](../security-threat-model.md) take precedence over this proposed design.

## 2. Proposed deployment architecture

```text
User browser
    |
    | HTTPS
    v
Approved edge service / load balancer / web application firewall
    |
    +--> Next.js frontend
    |       |
    |       | private authenticated API requests
    |       v
    +--> FastAPI backend
            |
            +--> Managed PostgreSQL on a private network
            +--> Approved private object storage - not yet implemented
            +--> OpenAI API - disabled until deployment approval
            +--> Authorised news provider - none currently approved

Supporting platform services:
    - Managed secret store
    - Central structured log and metric sink
    - Encrypted database and object backups
    - Image registry and deployment automation
```

The frontend and backend may run on one approved platform or on separate services. In either design:

- Browser traffic must use HTTPS.
- PostgreSQL and object storage must not be directly reachable from the public internet.
- Browser code must never receive `DATABASE_URL`, `OPENAI_API_KEY`, database passwords, storage credentials, or other secrets.
- FastAPI must be the only application component allowed to access private content records and image objects.
- Same-origin Next.js API gateways should continue forwarding the secure session cookie to FastAPI.

## 3. Hosting requirements

An approved hosting environment must provide:

- Isolated staging and production environments.
- Immutable application images built from reviewed commits.
- HTTPS termination, trusted proxy configuration, HSTS, CSP, frame protection, MIME protection, and referrer policy verification.
- Private networking and least-privilege identities between application, database, storage, secret, and logging services.
- A managed secret store with access logging and rotation support.
- Managed PostgreSQL 16 or a compatible reviewed version with TLS, encrypted storage, backups, point-in-time recovery where approved, and restricted administrative access.
- Private object storage with encryption, public access blocked, owner-controlled delivery, object lifecycle controls, integrity metadata, and reconciliation support.
- Central structured logging, health monitoring, alerting, retention, and restricted operator access.
- A container registry with vulnerability scanning, provenance, and immutable image references.
- Approved capacity, spend limits, provider quotas, and an emergency generation stop.

The development `compose.yaml` is a local packaging and demonstration tool. It is not a production orchestrator or proof that these hosting controls exist.

## 4. Component requirements

### 4.1 Next.js frontend

The frontend image is built from `apps/web/Dockerfile` with Node.js 22 and runs the Next.js standalone server as a non-root user.

Deployment requirements:

- Set `API_INTERNAL_BASE_URL` to the private FastAPI origin available to the Next.js server.
- Set `NEXT_PUBLIC_API_BASE_URL` only when browser-visible configuration is required. It is public and must never contain a credential.
- Keep authentication through the existing same-origin route handlers so HTTP-only cookies remain inaccessible to client-side JavaScript.
- Route public traffic to the frontend through the approved HTTPS edge.
- Configure the runtime port and hostname through the platform, without embedding environment-specific values in the image.
- Verify `/`, `/login`, `/register`, protected-route redirects, and frontend-to-backend communication after deployment.

### 4.2 FastAPI backend

The backend image is built from `apps/api/Dockerfile` with Python 3.12 and runs Uvicorn as a non-root user.

Deployment requirements:

- Set `APP_ENV=production` so session cookies require HTTPS.
- Load `DATABASE_URL` and any approved provider credentials from the managed secret store.
- Set `FRONTEND_ORIGIN` to the exact public HTTPS frontend origin with no trailing slash.
- Keep `NEWS_SOURCE_MODE=disabled` for production. The existing `fixture` mode is only for controlled synthetic demonstrations.
- Do not enable OpenAI features until their release gates are approved.
- Apply edge and shared rate limits in addition to the current application controls.
- Expose `GET /health` for process liveness and `GET /ready` for database-backed readiness through a restricted monitoring path where possible.
- Preserve request identifiers and safe structured logs without recording user content or credentials.

### 4.3 PostgreSQL

Use PostgreSQL 16 unless a different compatible version is reviewed and tested. The initial schema uses the `pgcrypto` extension, so the managed service and migration role must allow its required setup.

Requirements:

- Private network access only.
- TLS in transit and encryption at rest.
- Separate least-privilege application and migration roles where the platform supports them.
- Connection limits, timeouts, slow-query inspection, storage alarms, and tested backup and recovery controls.
- Production records must never be copied into normal development or CI environments.
- Migration state must be checked before and after each release.

### 4.4 Private image storage

The repository currently supports `IMAGE_STORAGE_BACKEND=local` only. The backend deliberately rejects that adapter when `APP_ENV` is `staging` or `production`. Production image generation must remain disabled until an approved private object-storage adapter is implemented and tested.

The future adapter must:

- Block all anonymous and public object access.
- Use server-side encryption and a least-privilege application identity.
- Preserve the existing owner-authorised backend delivery path.
- Enforce content type, size, integrity, and safe object-key rules.
- Support idempotent deletion, inventory, cleanup retries, and reconciliation with PostgreSQL.
- Avoid exposing internal bucket names, object keys, or provider credentials in API responses.

### 4.5 External providers

- OpenAI: keep disabled until the approved model, data terms, privacy review, quotas, budget alerts, timeouts, and incident controls are recorded.
- News source: no live CNN method is authorised. Keep ingestion disabled. Synthetic fixtures may be used only in controlled demonstrations and must not be presented as live CNN content.
- Do not add web scraping, access-control bypasses, or an unreviewed provider as a deployment workaround.

## 5. Deployment prerequisites

Do not begin a public deployment until all of the following are recorded as complete:

1. Product and technical owners approve the target environment and intended audience.
2. NFA-82 public-release blockers and NFA-75 SEC-01 through SEC-06 are closed or an accountable owner explicitly accepts an allowed residual risk.
3. Human UAT is signed off.
4. The rights decision permits every enabled source and use.
5. The production object-storage adapter is implemented and verified.
6. Managed secrets, TLS, shared rate limiting, provider budget controls, monitoring, backups, restore testing, and incident ownership exist.
7. OpenAI terms, privacy, model, and spending approvals exist before any key is configured.
8. CI passes for the exact commit and images selected for release.
9. A rollback and database compatibility decision is recorded for the release.
10. A change window and responsible operators are assigned.

## 6. Deployment procedure

These are platform-neutral steps. Convert them into reviewed provider-specific automation before production use.

1. Record the release commit, image digests, change summary, owner, approver, and maintenance window.
2. Confirm the release prerequisites and rights gates above.
3. Build the frontend and backend images from the reviewed commit in CI.
4. Scan dependencies and images, generate the required provenance or software bill of materials, and stop on an unresolved release-blocking result.
5. Push immutable images to the approved private registry.
6. Provision or verify the private network, PostgreSQL, object storage, secret store, log sink, monitoring, and HTTPS edge.
7. Load environment-specific non-secret settings and secret references. Do not copy a developer `.env` file into the platform.
8. Take and verify a pre-change database backup or platform recovery point.
9. Run the migration as a one-off release job using the migration identity:

   ```bash
   alembic current
   alembic upgrade head
   alembic current
   ```

10. Deploy the FastAPI image without enabling blocked provider features.
11. Wait for `GET /health` and `GET /ready` to succeed.
12. Deploy the Next.js image and verify its private connection to FastAPI.
13. Run the verification checklist in section 8 with synthetic records.
14. Review logs, metrics, error rate, latency, database connections, and cleanup queues.
15. Record the outcome. If a release check fails, stop or roll back according to section 9.

Never run `alembic downgrade` automatically in production. A database rollback may destroy data or be incompatible with the previous application. Prefer a forward fix unless the exact downgrade has been reviewed and rehearsed against a disposable copy.

## 7. Startup and shutdown

### Startup order

1. Secret, network, database, storage, logging, and monitoring services are available.
2. The migration job reaches the intended Alembic revision.
3. FastAPI starts and becomes ready.
4. Next.js starts and reaches FastAPI through its private origin.
5. The HTTPS edge sends traffic only to healthy instances.
6. Scheduled maintenance jobs start only after their dependencies are healthy.

### Controlled shutdown

1. Stop new traffic or enable maintenance mode at the edge.
2. Disable scheduled ingestion, generation, deletion, and cleanup workers.
3. Allow bounded in-flight requests to complete, then stop frontend and backend instances gracefully.
4. Confirm no migration or maintenance job is still running.
5. Stop supporting services only when the platform operation requires it. Do not delete persistent database or object-storage data.
6. Record the shutdown reason and any incomplete work that needs reconciliation.

For the local development stack only, use the verified commands in [NFA-84](../docker-packaging.md):

```bash
docker compose up --build --detach --wait
docker compose ps
docker compose down
```

`docker compose down` preserves the named development volumes unless a separate destructive volume-removal option is used.

## 8. Deployment verification

Use synthetic test data and a dedicated non-production verification account.

- Confirm the expected commit and immutable image digests are running.
- Confirm HTTPS, certificate validity, redirects, HSTS, security headers, trusted proxy behavior, and secure cookie attributes.
- Confirm `/health` reports process availability.
- Confirm `/ready` reports `status=ready`, `database=connected`, and `configuration=valid` without exposing credentials.
- Confirm registration, login, authenticated `GET /api/v1/auth/me`, logout, and CSRF behavior.
- Confirm one user cannot read another user's drafts or image objects.
- Confirm synthetic article browsing and pagination.
- Confirm live CNN ingestion is unavailable and `NEWS_SOURCE_MODE=disabled`.
- If OpenAI is not approved, confirm generation fails closed without a provider request.
- If private production storage is not approved, confirm image generation remains unavailable.
- Confirm migrations reached the intended head and application queries succeed.
- Confirm structured logs arrive without passwords, keys, cookies, article text, draft text, prompts, or private object keys.
- Confirm monitoring and alerts receive a controlled test signal.
- Confirm backup status and the date of the latest successful isolated restore exercise.
- Confirm restart behavior and data persistence without deleting application state.

The release owner records each result, evidence link, timestamp, environment, and reviewer. A failed mandatory check returns the decision to No-Go.

## 9. Rollback considerations

Application rollback and data recovery are different operations.

### Application rollback

1. Stop the rollout and preserve logs, request identifiers, and the affected image digest.
2. Determine whether the database schema remains backward compatible with the previous application image.
3. If compatible, direct traffic to the last approved image and run the verification checklist.
4. If incompatible, keep traffic stopped and choose a reviewed forward fix or an explicitly rehearsed schema recovery plan.
5. Do not silently re-enable a provider or rights path that was disabled in the failed release.

### Data recovery

Use the separate [backup and recovery guide](backup-and-recovery.md). Do not restore a production database only to undo application code. A restore can lose newer records and can reintroduce content that users deleted. Deletion tombstones and cleanup work must be reapplied before access resumes.

## 10. Known deployment limitations

- No approved hosting provider or production environment has been selected.
- No staging or production deployment has been executed.
- No production private object-storage adapter exists.
- No production backup, point-in-time recovery, or restore exercise exists.
- No production secret store, log sink, monitoring platform, alert routing, or incident rota has been selected.
- Shared edge rate limiting, provider spending alerts, emergency stops, and production worker scheduling are not implemented.
- Python dependencies use bounded ranges rather than a complete hash-locked production resolution.
- Container signing, software bill of materials generation, continuous image scanning, and reviewed commit-SHA workflow pinning remain open.
- Human UAT, VoiceOver review, and production transport and proxy verification remain pending.
- Live CNN integration remains No-Go.

These limitations are release blockers, not optional post-release improvements.

## 11. Related documents

- [Environment configuration](environment-configuration.md)
- [Operations runbook](operations-runbook.md)
- [Backup and recovery](backup-and-recovery.md)
- [Docker packaging](../docker-packaging.md)
- [Reliability and recovery](../reliability-and-recovery.md)
- [Security threat model](../security-threat-model.md)
- [Release readiness decision](../release-readiness-quality-signoff.md)
- [Source authorisation decision](../jira/NFA-8.md)
