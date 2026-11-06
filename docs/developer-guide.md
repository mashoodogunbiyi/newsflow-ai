# NewsFlow AI developer guide

## 1. Purpose

This guide explains how to work safely and effectively in the NewsFlow AI repository after completing the initial setup. New developers should start with the main [README](../README.md), follow the [local development guide](development-setup.md), and then use this document for everyday engineering work.

## 2. System model

NewsFlow AI is a three-service application:

- `apps/web` is the Next.js 16 and React 19 user interface.
- `apps/api` is the Python and FastAPI business-logic and security boundary.
- PostgreSQL 16 is the system of record.

FastAPI can call the OpenAI text and image APIs only through backend service boundaries. The browser never receives an OpenAI key. Generated image metadata is stored in PostgreSQL while image bytes use a backend-only private storage adapter.

The implemented article source is a synthetic fixture provider. Live CNN access is blocked because no authorised access method has been approved.

Read the [system architecture](architecture/system-architecture.md), [data flows](architecture/data-flow.md), and [decision register](architecture/architecture-decisions.md) before changing a trust boundary or provider integration.

## 3. Repository map

```text
newsflow-ai/
├── apps/
│   ├── api/                 # FastAPI, services, repositories, migrations and tests
│   └── web/                 # Next.js routes, React components, gateways and browser tests
├── docs/                    # Architecture, setup, testing, security and operations records
├── infrastructure/          # Local Docker and future hosting configuration
├── packages/                # Reserved shared-package boundary
├── scripts/                 # Repository verification and security checks
├── tests/                   # Cross-application test assets
├── compose.yaml             # Local frontend, backend, migration and PostgreSQL stack
└── .env.example             # Safe local configuration template
```

Important backend directories:

| Directory | Responsibility |
| --- | --- |
| `app/api/routes` | HTTP endpoints, dependencies and response contracts |
| `app/services` | Application workflows, rights, safety and recovery behavior |
| `app/repositories` | PostgreSQL queries and owner-scoped persistence |
| `app/providers` | Article-provider interface, fixture provider and blocked CNN adapter |
| `app/prompts` | Versioned text and image prompt construction |
| `app/models` | Validated application and API data models |
| `app/database` | Connection, table metadata and repeatable seed support |
| `migrations` | Alembic configuration and versioned schema changes |
| `tests` | Unit, contract and safety-gated PostgreSQL tests |

Important frontend directories:

| Directory | Responsibility |
| --- | --- |
| `app` | Next.js pages, protected workspace and same-origin API routes |
| `components` | Accessible article, editor, generation, library, preview and UI components |
| `lib` | Server gateways and application API clients |
| `hooks` | Reusable generation state management |
| `types` | Runtime-validated frontend contracts |
| `e2e` | Playwright journeys and deterministic API fixture |
| `__tests__` | Vitest component and gateway tests |

## 4. Recommended daily workflow

1. Update local `main` before starting a Jira issue:

   ```bash
   git switch main
   git pull --ff-only origin main
   ```

2. Create a focused branch:

   ```bash
   git switch -c nfa-123-short-description
   ```

3. Make one coherent change and update its documentation and tests.
4. Review the exact files before staging:

   ```bash
   git status --short
   git diff
   ```

5. Stage only the intended files, run the relevant checks, commit, push, and open a pull request.
6. After merge, switch to `main`, pull with `--ff-only`, and delete the completed local branch.

Do not use a Jira issue title as permission to weaken existing security, rights, ownership, validation, or test controls.

## 5. Start the development environment

### Docker Compose

Docker is the recommended first-time route:

```bash
cp .env.example .env
docker compose up --build --detach --wait
docker compose ps
```

Replace the PostgreSQL placeholders in `.env` before starting. The migration container applies `alembic upgrade head` before FastAPI starts.

Stop the services without deleting persistent volumes:

```bash
docker compose down
```

### Manual services

For backend development, start PostgreSQL and then:

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
alembic upgrade head
fastapi dev app/main.py
```

In a second terminal:

```bash
cd apps/web
npm ci
npm run dev
```

The complete environment-variable reference and troubleshooting guide are in [development-setup.md](development-setup.md).

## 6. Backend development conventions

- Keep HTTP concerns in route modules and business rules in services.
- Keep database access in repositories and use bound SQLAlchemy expressions.
- Require `require_authenticated_session` for private reads.
- Require `require_csrf_authenticated_session` for state changes.
- Scope private repository operations by the authenticated user ID.
- Return the same safe not-found response for missing and differently owned private resources.
- Check current source rights again before display or AI generation.
- Keep provider credentials in server-side settings and redact them from errors and logs.
- Use stable safe error codes at the HTTP boundary.
- Add migrations for schema changes; do not edit an applied migration to change history.
- Use deterministic provider doubles in routine tests.

FastAPI automatically exposes the current OpenAPI contract at [http://localhost:8000/docs](http://localhost:8000/docs) while the backend is running. See [api-reference.md](api-reference.md).

## 7. Frontend development conventions

- Put authenticated pages inside `app/(workspace)` so server session validation and the application shell are reused.
- Keep FastAPI authoritative for authentication, authorisation, rights and persistence.
- Send browser mutations through same-origin Next.js route handlers.
- Forward only explicitly approved headers and cookies.
- Never store passwords, provider keys, session identifiers or private data in browser storage.
- Runtime-validate backend data before rendering it.
- Render source and generated text as text, never unsanitised HTML.
- Preserve keyboard access, visible focus, status announcements and reduced-motion behavior.
- Keep user edits after recoverable failures and prevent duplicate submissions.
- Never present an AI result as published, factually guaranteed or sourced from live CNN.

Read [apps/web/README.md](../apps/web/README.md) for the detailed component and route conventions.

## 8. Database changes

Create a migration after updating the approved SQLAlchemy schema:

```bash
cd apps/api
alembic revision -m "describe the schema change"
```

Review the generated file carefully, then verify the upgrade:

```bash
alembic upgrade head
alembic current
```

Migration integration tests are destructive and must use a disposable database with both safety variables set. Never point them at the normal development or production database. Exact commands are in [development-setup.md](development-setup.md#9-run-quality-checks-and-tests).

## 9. Test and quality commands

Backend, from `apps/api` with the virtual environment active:

```bash
ruff check .
ruff format --check .
pytest -m "not live_ai"
```

Frontend, from `apps/web`:

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run test:e2e
npm run build
```

Repository checks, from the root:

```bash
python3 scripts/scan_secrets.py
python3 scripts/verify_architecture_documentation.py
python3 scripts/verify_deployment_documentation.py
python3 scripts/verify_readme_documentation.py
git diff --check
```

Run the smallest relevant test while developing, then the complete quality group before requesting review. See [testing.md](testing.md) for the coverage map, CI jobs, integration-database safety gates and current evidence.

## 10. Documentation responsibilities

Update documentation in the same change when you modify:

- a command, prerequisite or environment variable;
- a route, response contract or security requirement;
- a component, provider, trust boundary or data flow;
- a database relationship, migration or retention rule;
- a Docker, deployment, monitoring, backup or recovery behavior;
- a feature status or known limitation.

Use normal ASCII hyphens in project documentation. Do not paste credentials, restricted source material, private user information or production details into examples or screenshots.

## 11. Debugging guide

| Symptom | First checks |
| --- | --- |
| Frontend unavailable | `docker compose ps`, then `docker compose logs frontend` |
| Backend unhealthy | Open `/health`, then inspect `docker compose logs backend` |
| Backend not ready | Open `/ready`, then inspect PostgreSQL credentials and database health |
| Authentication unavailable | Verify FastAPI readiness, `API_INTERNAL_BASE_URL`, session cookies and PostgreSQL |
| Empty article catalogue | Confirm fixture mode and seed or synchronisation state; live CNN is intentionally disabled |
| Generation unavailable | Confirm rights, source sufficiency, limits and server-only OpenAI configuration |
| Image generation unavailable | Confirm provider configuration and remember local storage is rejected outside development and test |
| Migration failure | Stop application traffic, inspect `alembic current`, and do not rerun or downgrade blindly |

Use request IDs to correlate safe logs. Never add private content or secrets to logs to make debugging easier.

## 12. Security, privacy and rights checklist

Before requesting review:

- No secret is tracked or included in a screenshot.
- Protected operations require a valid server-managed session.
- State changes require CSRF proof.
- Private records and images are owner-scoped.
- Source rights are checked at the point of use.
- Provider input contains only necessary permitted fields.
- Logs exclude credentials, article content, prompts, drafts and storage keys.
- Tests use synthetic records and mocked external services.
- Live CNN access remains disabled.
- AI output remains subject to human review and is not automatically published.

## 13. Further reading

- [Local setup](development-setup.md)
- [API reference](api-reference.md)
- [System architecture](architecture/system-architecture.md)
- [Data flows](architecture/data-flow.md)
- [Testing](testing.md)
- [Security threat model](security-threat-model.md)
- [Deployment guide](deployment/deployment-guide.md)
- [Operations runbook](deployment/operations-runbook.md)
