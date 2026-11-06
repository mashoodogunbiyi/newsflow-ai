# NewsFlow AI

NewsFlow AI is a full-stack, review-first workspace that turns permitted news facts into editable LinkedIn drafts and original AI-generated illustrations while preserving source attribution, content rights, ownership and human control.

> **Current status:** the application is implemented and tested for a controlled local demonstration using synthetic article data and mocked external providers. Public production release and live CNN integration remain **No-Go**.

![NewsFlow AI homepage showing the fixture-mode product introduction](docs/screenshots/homepage.png)

## Overview

NewsFlow AI demonstrates how a modern AI-assisted content product can be built without treating generation as a shortcut around editorial responsibility.

An authenticated user can:

1. Paste an exact approved article URL or browse rights-approved article metadata.
2. Review the selected source and its attribution.
3. Generate a source-grounded LinkedIn draft with controlled tone and length.
4. Edit the text and inspect automated grounding warnings.
5. Generate and compare original conceptual illustrations.
6. Save, reopen, version, copy, download and delete their private content.

The application never automatically publishes to LinkedIn. Every generated result remains subject to human review.

## Problem statement

Creating professional social content from news involves more than asking an AI model to summarise an article. A responsible workflow must also answer:

- Is the source authorised for display and AI processing?
- Which source fields are permitted?
- Can each factual claim be traced to the supplied evidence?
- How are generated images prevented from looking like authentic news photography?
- Who owns each private draft and image?
- What happens when a provider, database or storage operation fails?

NewsFlow AI addresses those concerns through a provider-neutral ingestion boundary, versioned rights records, grounded prompt construction, deterministic output checks, private storage, object-level authorisation, human editing and auditable operational controls.

## Implemented features

### Accounts and security

- Registration with email validation and Argon2id password hashing.
- Login, absolute-expiry server-managed sessions and secure logout.
- HTTP-only session cookies and CSRF protection for state-changing requests.
- Owner-scoped access to drafts, versions and generated images.
- Generic private-resource errors that do not reveal another user's records.
- Request limits, security headers, secret scanning and dependency auditing.

### Article ingestion and discovery

- Provider-neutral article interface with a deterministic synthetic fixture provider.
- Validation, normalisation, sanitisation, stable identity and deduplication.
- Provenance, attribution and versioned permitted-use records.
- Manual administrator synchronisation with durable job evidence.
- Exact approved-URL lookup plus topic filtering, category filtering, ordering and cursor-based catalogue pagination.
- Fail-closed behavior when an authorised source is unavailable.

### AI-assisted creation

- Backend-only OpenAI text and image service boundaries.
- Versioned, source-grounded prompt construction with prompt-injection separation.
- Professional, conversational and analytical tone controls in English, French or Spanish.
- Length controls with idempotency, daily limits and concurrency controls.
- Deterministic schema, length and factual-grounding validation.
- Sensitive-news image policy, conceptual illustration rules and AI designation.
- Generated-image validation, metadata removal, digest checking and private delivery.
- Mocked provider tests that do not require real API credentials or paid calls.

### Review and content management

- Responsive draft editor and LinkedIn-inspired preview.
- Immutable image alternatives and selected-version preview.
- Durable saved drafts with optimistic concurrency and immutable history.
- Personal content library with secure thumbnails and pagination.
- User-controlled text copying and owner-authorised image downloads.
- Deletion, retention, retryable image cleanup and content-free audit evidence.

### Engineering and quality

- Docker Compose environment for Next.js, FastAPI, migrations and PostgreSQL.
- Alembic schema migrations and repeatable synthetic seed data.
- Unit, integration, browser, accessibility, performance, security and recovery tests.
- GitHub Actions checks for backend, frontend, browser, packaging and documentation contracts.
- Architecture, deployment, operations, backup and recovery documentation.

## Technology stack

| Layer            | Technology                                          | Responsibility                                                                    |
| ---------------- | --------------------------------------------------- | --------------------------------------------------------------------------------- |
| Frontend         | Next.js 16, React 19, TypeScript, Tailwind CSS 4    | Responsive pages, protected workspace, editor, preview and content library        |
| Frontend testing | Vitest, React Testing Library, Playwright, axe-core | Components, gateways, browser journeys and accessibility checks                   |
| Backend          | Python, FastAPI, Pydantic                           | HTTP APIs, validation, authentication, authorisation and orchestration            |
| Data             | PostgreSQL 16, SQLAlchemy, Alembic                  | Accounts, sessions, articles, rights, drafts, images, versions and audit evidence |
| AI integration   | Official OpenAI Python SDK                          | Structured text generation and original illustration generation                   |
| Image processing | Pillow                                              | Image format, size, pixel, metadata and integrity validation                      |
| Packaging        | Docker, Docker Compose                              | Reproducible local services, migrations, health checks and persistent volumes     |
| Quality          | Ruff, ESLint, Prettier, Pytest, GitHub Actions      | Formatting, static checks, automated tests and CI enforcement                     |

## System architecture

```mermaid
flowchart LR
    Browser["User browser"] --> Next["Next.js and React"]
    Next -->|"Same-origin gateways"| API["FastAPI"]
    API --> Auth["Session, CSRF, rights and ownership"]
    Auth --> DB[("PostgreSQL")]
    Auth --> Images[("Private image storage<br/>local adapter in development")]
    Auth --> OpenAI(["OpenAI APIs<br/>server-side only"])
    Fixture(["Synthetic article provider"]) --> API
    CNN(["Live CNN integration<br/>blocked"]) -.-> API
```

The browser never connects directly to PostgreSQL, private image storage or OpenAI. FastAPI is the authoritative security and business-logic boundary. The implemented provider factory accepts only fixture mode and rejects unapproved source access.

Detailed diagrams:

- [System architecture and trust boundaries](docs/architecture/system-architecture.md)
- [Article, generation, storage and export data flows](docs/architecture/data-flow.md)
- [Architecture decisions and trade-offs](docs/architecture/architecture-decisions.md)
- [AI generation component architecture](docs/architecture/ai-generation-architecture.md)

## Repository structure

```text
newsflow-ai/
├── .github/workflows/       # Pull-request and main-branch quality checks
├── apps/
│   ├── api/                 # FastAPI, SQLAlchemy, Alembic and backend tests
│   └── web/                 # Next.js, React components and browser tests
├── docs/                    # Setup, architecture, testing, security and operations
├── infrastructure/          # Docker guidance and future hosting boundaries
├── packages/                # Reserved shared-package boundary
├── scripts/                 # Security and documentation verification
├── tests/                   # Cross-application test assets
├── compose.yaml             # Local multi-service environment
├── .env.example             # Safe configuration template
├── PROJECT_PLAN.md          # Epic and task delivery plan
└── PROJECT_MANAGEMENT.md    # Jira workflow and project-management approach
```

See the [developer guide](docs/developer-guide.md) for the detailed backend and frontend directory map.

## Getting started

### Prerequisites

For the recommended Docker setup:

- Git 2.30 or later.
- Docker Desktop or Docker Engine 24 or later.
- Docker Compose plugin 2.20 or later.

For manual service development:

- Node.js 20.19 or later and npm 11 or a compatible release.
- Python 3.10 to 3.14, with Python 3.12 recommended.
- PostgreSQL 16.

### Clone and configure

```bash
git clone https://github.com/mashoodogunbiyi/newsflow-ai.git
cd newsflow-ai
cp .env.example .env
```

Open the ignored `.env` file and replace these local PostgreSQL placeholders:

```dotenv
POSTGRES_USER=choose_a_local_username
POSTGRES_PASSWORD=choose_a_local_password
POSTGRES_DB=newsflow
DATABASE_URL=postgresql://choose_a_local_username:choose_a_local_password@localhost:5432/newsflow
```

Use development-only credentials. The local application and normal test suite do not require a real OpenAI key. Confirm that Git ignores the file:

```bash
git check-ignore -v .env
```

To make real text generation calls, add an API key and a text model available to your OpenAI API project to the ignored `.env` file. Image generation uses the same key and the separately configured `OPENAI_IMAGE_MODEL`:

```dotenv
OPENAI_API_KEY=replace_with_your_own_api_key
OPENAI_MODEL=replace_with_an_approved_text_model
```

Never add the real value to `.env.example`, source code, screenshots or Git. ChatGPT access and OpenAI API billing are separate; a key authorises this backend to make metered API requests.

The complete variable reference is in [environment-configuration.md](docs/deployment/environment-configuration.md).

## Running with Docker

Start Docker Desktop or Docker Engine, then run from the repository root:

```bash
docker compose config --quiet
docker compose up --build --detach --wait
docker compose ps
```

Compose starts PostgreSQL, applies every Alembic migration, loads one idempotent synthetic demonstration record through a development-only one-shot service, waits for FastAPI readiness and then starts Next.js.

| Service           | Local address                                                |
| ----------------- | ------------------------------------------------------------ |
| Frontend          | [http://localhost:3000](http://localhost:3000)               |
| FastAPI health    | [http://localhost:8000/health](http://localhost:8000/health) |
| FastAPI readiness | [http://localhost:8000/ready](http://localhost:8000/ready)   |
| Swagger UI        | [http://localhost:8000/docs](http://localhost:8000/docs)     |
| ReDoc             | [http://localhost:8000/redoc](http://localhost:8000/redoc)   |

View logs:

```bash
docker compose logs --follow
```

Stop the application without deleting the database or private-image volumes:

```bash
docker compose down
```

Do not add `--volumes` unless you deliberately intend to delete local development data.

## Running services manually

Use the [complete local development guide](docs/development-setup.md) for PostgreSQL creation and troubleshooting.

### Backend

With PostgreSQL running and the root `.env` configured:

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
alembic upgrade head
fastapi dev app/main.py
```

### Frontend

In another terminal:

```bash
cd apps/web
npm ci
npm run dev
```

The frontend requires FastAPI and PostgreSQL for authentication and protected application data.

## Database migrations and seed data

Docker applies migrations and loads the safe synthetic demonstration record automatically. For a manual backend:

```bash
cd apps/api
source .venv/bin/activate
alembic upgrade head
alembic current
```

When running without Compose, load the repeatable synthetic fixture only in development or test:

```bash
SEED_DATA_ENABLED=true python -m app.database.seed
```

Never enable development seed loading in staging or production. Migration integration tests require a separately named disposable database and explicit reset permission; see the [testing guide](docs/testing.md).

After signing in, the dashboard can resolve this development-only catalogue URL without contacting the domain:

```text
https://example.invalid/newsflow/synthetic-clean-energy
```

The URL workflow intentionally matches an existing approved catalogue record. It does not download or scrape arbitrary pages.

## Running tests

### Backend

From `apps/api` with the development environment active:

```bash
ruff check .
ruff format --check .
pytest -m "not live_ai"
```

### Frontend

From `apps/web`:

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run test:e2e
npm run build
```

### Repository checks

From the repository root:

```bash
python3 scripts/scan_secrets.py
python3 scripts/verify_architecture_documentation.py
python3 scripts/verify_deployment_documentation.py
python3 scripts/verify_demonstration_package.py
python3 scripts/verify_readme_documentation.py
git diff --check
```

Routine tests use synthetic fixtures and mocked provider responses. They do not require live CNN access, real OpenAI credentials, production data or paid API calls. See [testing.md](docs/testing.md) for integration-database safety rules, current results and CI coverage.

## Demonstration

The recommended portfolio demonstration runs the real Next.js interface against the deterministic local mock API. It exercises sign-in, approved URL selection, draft generation, editing, image generation, preview, private saving, reopening, copying, downloading and deletion without contacting CNN or OpenAI.

From the repository root:

```bash
cd apps/web
npm ci
npm run demo
```

Open [http://127.0.0.1:3100](http://127.0.0.1:3100). The terminal prints the mock-only account and approved synthetic article URL. These public fixture credentials work only with the loopback demonstration API and are not application, database or provider secrets.

The [complete demonstration package](docs/demonstration/README.md) contains the presenter script, architecture talking points, rehearsal checklist, fallback plan, screenshots, verification evidence and honest limitations. A real OpenAI key is optional for the integrated Docker environment and is deliberately not read by this reliable mock demonstration.

## API documentation

When FastAPI is running:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- OpenAPI JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

The [API reference](docs/api-reference.md) explains authentication cookies, CSRF, idempotency, pagination, safe errors and the main endpoint groups.

## Screenshots

All screenshots use a synthetic account, synthetic article metadata and mocked provider output.

| Article dashboard                                                                    | Generation workspace                                                                             |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| ![Authenticated synthetic article catalogue](docs/screenshots/article-dashboard.png) | ![Editable LinkedIn draft and illustration workspace](docs/screenshots/generation-workspace.png) |

| Content library                                                                                     | Public homepage                                               |
| --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| ![Private content library containing a synthetic saved draft](docs/screenshots/content-library.png) | ![Public NewsFlow AI homepage](docs/screenshots/homepage.png) |

The [screenshot manifest](docs/screenshots/README.md) records the data source and repeatable capture command.

## Security and privacy

- Secrets are loaded from ignored environment files or a future managed secret store.
- Provider keys and database credentials remain server-side.
- Passwords use Argon2id; raw session values are never stored in PostgreSQL.
- Private operations require authenticated, owner-scoped repository queries.
- State-changing requests require CSRF proof.
- Logs use allowlisted operational fields and exclude credentials, prompts, drafts and private storage keys.
- Generated images are validated before private persistence and delivered through owner-authorised endpoints.
- Production HTTPS, managed secrets, shared edge controls, private object storage, backups and incident operations remain release gates.

Read the [security threat model](docs/security-threat-model.md), [API security review](docs/api-security.md) and [authorisation guide](docs/authorization.md).

## Source rights and AI safety

Live CNN access is not authorised. The implemented provider factory supports only a synthetic fixture source for development and tests. The disabled CNN adapter does not scrape, bypass access restrictions or retrieve live content.

Any future news provider must have documented permission, permitted fields, attribution rules, retention rules and AI-processing rights before activation.

AI limitations:

- Generated text may contain mistakes even after automated grounding checks.
- Automated validation does not replace human fact-checking.
- Generated images are conceptual illustrations, not authentic event photography.
- AI-generated image labelling must remain visible where required.
- Provider output is never published automatically.
- Users must review the source, wording, context and illustration before export or use.

See [ADR-001](docs/jira/NFA-8.md), the [grounding policy](docs/factual-grounding-validation.md), [image safety policy](docs/image-safety-policy.md) and [AI evaluation report](docs/ai-grounding-content-safety-evaluation.md).

## Known limitations

- Live CNN ingestion is blocked pending written authorisation and a new Go decision.
- The included article catalogue uses synthetic fixtures, not live news.
- Pasted URLs must already exist in the rights-approved catalogue; arbitrary web-page ingestion is intentionally disabled.
- Live text and image generation require approved OpenAI configuration and available provider credit.
- The only implemented image-storage adapter is local and is rejected in staging and production.
- No production hosting platform, secret store, monitoring stack, backup system or restore proof exists.
- Background scheduling for production sync, retention and cleanup is not configured.
- Shared edge rate limiting and provider-spending alerts remain production requirements.
- Human UAT, representative screen-reader review and final production security gates remain incomplete.
- Automatic LinkedIn publishing is intentionally not implemented.
- No software licence has been selected.

## Future improvements

- Integrate an explicitly authorised article provider after rights approval.
- Implement an encrypted private object-storage adapter and reconciliation inventory.
- Select and verify an approved hosting, secrets, monitoring, backup and recovery platform.
- Add shared rate limiting, spending alerts and an emergency generation stop.
- Complete human UAT, screen-reader review and production security sign-off.
- Add password reset only after its identity-verification and abuse controls are designed.

## Project status

| Area                                                            | Status                                                        |
| --------------------------------------------------------------- | ------------------------------------------------------------- |
| Engineering foundation and Docker packaging                     | Implemented and locally verified                              |
| Accounts, sessions and object authorisation                     | Implemented and tested                                        |
| Synthetic article pipeline and catalogue                        | Implemented and tested                                        |
| OpenAI text and image service boundaries                        | Implemented and mocked in routine tests                       |
| Editor, preview and image alternatives                          | Implemented and tested                                        |
| Saved-content lifecycle, export and deletion                    | Implemented and tested                                        |
| Security, reliability, accessibility and performance automation | Implemented with documented manual and production limitations |
| Architecture and developer documentation                        | Implemented                                                   |
| Controlled local synthetic-data demonstration                   | Package prepared; manual rehearsal and owner acceptance pending |
| Live CNN integration                                            | No-Go                                                         |
| Public production release                                       | No-Go                                                         |

Detailed evidence is available in the [testing guide](docs/testing.md), [release-readiness review](docs/release-readiness-quality-signoff.md), [Docker packaging record](docs/docker-packaging.md), and [deployment guide](docs/deployment/deployment-guide.md).

## Documentation

| Document                                                                  | Purpose                                                    |
| ------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Local development setup](docs/development-setup.md)                      | Complete installation, configuration and troubleshooting   |
| [Developer guide](docs/developer-guide.md)                                | Daily workflow, code structure and engineering conventions |
| [API reference](docs/api-reference.md)                                    | OpenAPI access, authentication and endpoint overview       |
| [Testing guide](docs/testing.md)                                          | Commands, coverage, CI, isolation and current evidence     |
| [System architecture](docs/architecture/system-architecture.md)           | Components, authentication and trust boundaries            |
| [Data flows](docs/architecture/data-flow.md)                              | Ingestion, generation, storage, export and recovery        |
| [Environment configuration](docs/deployment/environment-configuration.md) | Complete runtime variable and secret classification        |
| [Deployment guide](docs/deployment/deployment-guide.md)                   | Proposed hosting architecture and release procedure        |
| [Operations runbook](docs/deployment/operations-runbook.md)               | Health, monitoring, maintenance and incidents              |
| [Backup and recovery](docs/deployment/backup-and-recovery.md)             | Proposed backup, restore and reconciliation controls       |
| [Demonstration package](docs/demonstration/README.md)                     | Presenter script, rehearsal, fallback and evidence         |
| [Project plan](PROJECT_PLAN.md)                                           | Epics and delivery tasks                                   |
| [Project management](PROJECT_MANAGEMENT.md)                               | Jira workflow and working agreements                       |

## Contributing workflow

This is currently a portfolio project, but it follows a collaborative pull-request workflow:

1. Start from an updated `main` branch.
2. Create a short Jira-linked feature branch.
3. Keep the change focused and update tests and documentation together.
4. Run the relevant quality checks.
5. Open a pull request and review its CI evidence before merging.

See the [developer guide](docs/developer-guide.md#4-recommended-daily-workflow) for the commands.

## Licence

No software licence has been selected. The repository must not be treated as granting permission to reuse third-party source material.
