# NewsFlow AI Maintenance Guide

## 1. Purpose

This guide identifies the main code and operational responsibilities a future maintainer must understand. It supplements the developer, deployment, testing, and architecture guides; it does not create a production operating claim.

## 2. Repository ownership map

| Area | Primary location | Maintenance responsibility |
| --- | --- | --- |
| Next.js interface | `apps/web/app`, `apps/web/components` | Routes, responsive UI, accessibility, same-origin gateways, and browser state |
| FastAPI application | `apps/api/app` | API contracts, validation, orchestration, authentication, authorisation, and errors |
| Database model | `apps/api/app/database`, `apps/api/migrations` | SQLAlchemy records, Alembic revisions, seed safety, constraints, and indexes |
| Article pipeline | `apps/api/app/providers`, article services and repositories | Authorised source boundary, validation, normalisation, rights, provenance, and deduplication |
| Text and image generation | OpenAI, generation, prompting, and image services | Backend-only provider access, grounding, safety, cost limits, idempotency, and recovery |
| Private images | Image storage and delivery services | Validation, owner-scoped delivery, cleanup, reconciliation, and storage adapter policy |
| Automated tests | `apps/api/tests`, `apps/web/__tests__`, `apps/web/e2e` | Deterministic coverage, synthetic fixtures, integration isolation, and regression evidence |
| Packaging and CI | `compose.yaml`, Dockerfiles, `.github/workflows` | Builds, health checks, migrations, lifecycle verification, and quality gates |
| Documentation | `README.md`, `docs`, `PROJECT_PLAN.md` | Accurate commands, decisions, restrictions, evidence, and handover records |

## 3. Change procedure

For each Jira-linked change:

1. update local `main` with `git pull --ff-only origin main`;
2. create a focused branch;
3. change implementation, tests, and documentation together;
4. run focused tests, then the relevant complete quality checks;
5. run the secret scanner and `git diff --check`;
6. review the staged diff before committing;
7. open a pull request and wait for CI;
8. merge only after review; and
9. update local `main` and remove the completed branch.

Never place real secrets in a commit, Jira comment, screenshot, fixture, log, or command example.

## 4. Database maintenance

- Add every schema change through a new Alembic revision; do not rewrite an applied shared migration.
- Test upgrade and supported rollback behaviour against a disposable database.
- Keep constraints and object-level ownership rules aligned with API repositories.
- Keep seed data synthetic, idempotent, development-only, and explicitly enabled.
- Review query plans and indexes when list size, filtering, sorting, or joins change.
- Back up and restore an approved production database before claiming production recovery readiness.

## 5. Authentication and authorisation maintenance

- Keep passwords inside the Argon2id hashing boundary.
- Keep raw session identifiers out of PostgreSQL and logs.
- Require CSRF proof for cookie-authenticated state changes.
- Scope private draft, version, and image queries to the authenticated owner.
- Preserve generic private-resource errors to avoid object discovery.
- Review rate limits, session lifetime, cookie attributes, and security headers before deployment.

## 6. Article-source and rights maintenance

The implemented source mode is `fixture`. Live CNN access is No-Go.

Before adding or enabling a provider:

1. obtain written authorisation;
2. record permitted fields, AI-processing rights, attribution, retention, image, and redistribution rules;
3. update ADR-001 and the rights documentation;
4. implement the provider behind the existing adapter interface;
5. preserve validation, normalisation, sanitisation, deduplication, provenance, and rights versioning;
6. add synthetic and authorised integration tests; and
7. complete legal and product-owner review before activation.

Do not replace this process with arbitrary web scraping or access-control bypassing.

## 7. OpenAI and AI-safety maintenance

- Keep provider keys in backend-only secrets.
- Pin and review model configuration rather than assuming model availability.
- Preserve prompt boundaries between instructions and untrusted source data.
- Retain factual-grounding validation and source attribution.
- Retain image-safety policy, conceptual illustration rules, and AI designation.
- Review retry, timeout, concurrency, daily-use, output-size, and spending controls.
- Use mocked providers in routine CI; keep live tests explicit, optional, and billable.
- Never treat automated evaluation as a substitute for human editorial review.

## 8. Docker, configuration, and dependencies

- Keep `.env.example` complete but free of real values.
- Add any new backend setting to the environment guide, Compose model, and verification scripts where applicable.
- Keep application containers non-root and restrict exposed development ports to loopback.
- Run `bash scripts/verify_docker_packaging.sh` after changing Dockerfiles, Compose, health checks, migrations, or startup commands.
- Review Python and npm dependency updates, lockfile changes, security advisories, build output, and licences before merge.

## 9. Monitoring, backup, and recovery

The repository contains proposed operational guidance, not a deployed monitoring or backup service.

Before production:

- select approved log, metric, alert, secret, database, and private-storage platforms;
- implement and test backup schedules, retention, encryption, restore, and reconciliation;
- monitor database readiness, request latency, provider failures, generation limits, storage failures, cleanup retries, and security events;
- keep logs free of prompts, drafts, credentials, session values, private paths, and unnecessary personal data;
- document an incident owner, escalation route, maintenance window, recovery objective, and rollback decision; and
- perform recovery exercises and record their results.

## 10. Documentation maintenance

Update the README whenever a file, feature, command, limitation, or project status materially changes. Also update the narrow supporting guide, API reference, diagrams, test evidence, deployment guidance, and Jira issue when their contracts change.

Run:

```bash
python3 scripts/verify_handover_package.py
python3 scripts/verify_handover_clean_checkout.py
python3 scripts/verify_readme_documentation.py
python3 scripts/scan_secrets.py
git diff --check
```

## 11. Outstanding maintenance information

A future production owner must still supply:

- the approved hosting platform and region;
- managed secret-store ownership and rotation policy;
- PostgreSQL backup, retention, restore, and support arrangements;
- private object-storage service and access policy;
- monitoring, alerting, incident, and on-call ownership;
- data-controller, privacy, retention, and deletion decisions;
- authorised article-provider contract and rights owner;
- OpenAI project, model, budget, and emergency-disable ownership;
- software licence decision; and
- release, rollback, and change-approval authority.

