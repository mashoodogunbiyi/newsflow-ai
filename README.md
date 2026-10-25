# NewsFlow AI

NewsFlow AI is a planned full-stack application that turns authorised CNN International news information into original, source-grounded LinkedIn posts and accompanying AI-generated illustrations.

> Status: engineering foundation and account implementation in progress. NFA-12 to NFA-18 provide the working frontend, backend, PostgreSQL connection, secure configuration, Docker environment, quality checks, tests, and local development guide. NFA-20 and NFA-21 provide the approved schema, Alembic migrations, and synthetic seed data. NFA-22 adds secure user registration. NFA-23 adds credential verification, expiring server-managed sessions, protected current-user access, CSRF-protected logout, and authentication rate limiting. ADR-001 continues to block live CNN integration, so development uses original static demonstration content.

## Product workflow

1. Discover recent CNN articles through an authorised source.
2. Let a signed-in user filter and select an article.
3. Build a bounded fact pack from the permitted source fields.
4. Generate a LinkedIn post for the chosen tone, length, and audience.
5. Generate an original, LinkedIn-suitable illustration.
6. Let the user review, edit, regenerate, save, copy, and download the result.

Direct LinkedIn publishing, other news sources, video generation, payments, and social analytics are outside the first release.

## Planned architecture

| Layer | Planned technology | Responsibility |
|---|---|---|
| Web | Next.js, React, TypeScript, Tailwind CSS | Authentication screens, news dashboard, generation controls, editor, and preview |
| Backend API (our application) | FastAPI, Python | Business logic, validation, authorisation, orchestration, and REST endpoints |
| Data | PostgreSQL | Users, permitted article metadata, source lineage, generations, and saved posts |
| Queue/scheduler | Lightweight worker selected during implementation | Authorised news synchronisation and long-running generation work |
| External AI API | OpenAI API, called with the official Python SDK | LinkedIn post generation through the Responses API and original image generation |
| Object storage | S3-compatible storage; local adapter for development | Generated image assets |
| Delivery | Docker Compose and GitHub Actions | Reproducible local setup, tests, and release checks |

### FastAPI and the OpenAI API are different

- **FastAPI** is the Python framework we will use to build NewsFlow AI's own backend API. It will receive requests from the website, authenticate users, read and write the database, validate source facts, and coordinate external services.
- **The OpenAI API** is the external AI service that our FastAPI backend will call. We will use its Responses API to generate structured LinkedIn drafts and its image-generation capability to create original illustrations.
- **The OpenAI Python SDK** is the library used inside the FastAPI application to make those OpenAI API requests. Python is the implementation language; it is not a replacement for the OpenAI API.

```text
Next.js website
      |
      v
Our FastAPI backend
      |
      +----> Authorised CNN source
      |
      +----> OpenAI API
               |-- Responses API: LinkedIn post
               `-- Image generation: illustration
```

All OpenAI calls will therefore run on our backend. The `OPENAI_API_KEY` will be loaded from a server-side environment variable or secret manager and will never be sent to the browser or committed to the repository. This follows the [official OpenAI API guidance](https://developers.openai.com/api/reference/overview).

## Planning documents

- [PROJECT_PLAN.md](PROJECT_PLAN.md) - end-to-end delivery plan organised as Epics and Tasks.
- [PROJECT_MANAGEMENT.md](PROJECT_MANAGEMENT.md) - Jira setup, workflow, issue templates, roadmap, and operating rules.
- [docs/development-setup.md](docs/development-setup.md) - complete beginner-friendly installation, configuration, startup, testing, verification, and troubleshooting guide.
- [docs/jira/NFA-3.md](docs/jira/NFA-3.md) - functional and non-functional requirements baseline with measurable acceptance criteria.
- [docs/jira/NFA-4.md](docs/jira/NFA-4.md) - research and recommendation for authorised CNN data access.
- [docs/jira/NFA-5.md](docs/jira/NFA-5.md) - authorisation decision, current restrictions, and supporting evidence record.
- [docs/jira/NFA-6.md](docs/jira/NFA-6.md) - approved fixture-first source data contract covering required fields, validation, missing information, attribution, provenance, refresh, and retention.
- [docs/jira/NFA-7.md](docs/jira/NFA-7.md) - approved privacy, copyright, hallucination, and AI-generated image risk review with mandatory safeguards and release gates.
- [docs/jira/NFA-8.md](docs/jira/NFA-8.md) - approved architecture decision recording No-Go for live CNN integration and Go for fixture-based development.
- [docs/jira/NFA-9.md](docs/jira/NFA-9.md) - approved initial risk register covering development, delivery, security, cost, AI safety, and legal compliance, with named owners and treatment actions.
- [docs/jira/NFA-20.md](docs/jira/NFA-20.md) - approved PostgreSQL MVP schema and ERD covering accounts, source provenance, generations, versioned posts, images, saved content, ownership, constraints, indexes, and 3NF review.

### Documentation update rule

The README is the running written record of the project's progress. Whenever a project Markdown document or NFA deliverable is added or modified, the same change must update this README to:

- Link to the new or modified document where appropriate.
- Explain what work was completed or changed.
- Update the current project status and next step when affected.

The README and the related project document should be staged and committed together so the repository history remains understandable.

## Repository structure

```text
newsflow-ai/
├── compose.yaml             # Frontend, backend, and PostgreSQL development stack
├── apps/
│   ├── api/                 # FastAPI application, Alembic migrations, seed data, and Dockerfile
│   └── web/                 # Next.js application and development Dockerfile
├── packages/                # Shared contracts, schemas, or generated clients
├── infrastructure/
│   ├── database/            # Future hosted database, backup, and restore configuration
│   └── docker/              # Container and local-service configuration
├── docs/
│   ├── development-setup.md # Complete local development guide
│   ├── architecture/        # Architecture Decision Records and design notes
│   └── jira/                # Jira task deliverables and approved baselines
├── tests/                   # Cross-service and end-to-end tests
├── .editorconfig            # Shared text-formatting defaults
├── .env.example             # Safe local configuration template
├── .gitignore               # Excludes secrets, dependencies, builds, and local files
├── README.md
├── PROJECT_PLAN.md
└── PROJECT_MANAGEMENT.md
```

The frontend and backend directories contain working application foundations. PostgreSQL connection configuration and readiness checking are implemented in the backend. Environment variables are validated centrally, secret values are masked, and unsafe example placeholders are rejected. Docker Compose can run the frontend, backend, and database together with health-based startup ordering and persistent PostgreSQL storage. NFA-20 defines the approved database model, NFA-21 provides its migrations and seed process, NFA-22 securely creates user accounts, and NFA-23 authenticates those accounts with server-managed sessions. Shared packages and cross-service tests will be added by their related engineering tasks.

### Directory responsibilities

| Path | Responsibility |
|---|---|
| `apps/web` | Frontend user interface, authentication screens, dashboard, editor, and previews |
| `apps/api` | Backend API, validation, authorisation, persistence, and external-service orchestration |
| `apps/api/migrations` | Alembic database migration environment and versioned schema revisions |
| `packages` | Code and contracts shared between applications |
| `infrastructure/database` | Future hosted database, backup, and restore configuration |
| `infrastructure/docker` | Docker and local dependency configuration |
| `docs/architecture` | Architecture decisions and technical design records |
| `docs/jira` | Approved Jira deliverables and project-governance evidence |
| `docs/development-setup.md` | Software requirements, setup, configuration, testing, verification, and troubleshooting |
| `tests` | Cross-application, integration, and end-to-end tests |
| `compose.yaml` | Local multi-container development configuration |

Start with the complete [local development guide](docs/development-setup.md). The frontend also has its own [setup and structure guide](apps/web/README.md). The generated [Next.js agent instructions](apps/web/AGENTS.md) record version-specific framework rules that contributors and coding tools must follow. The backend has a separate [FastAPI setup and structure guide](apps/api/README.md).

### Frontend application

The NFA-12 frontend uses Next.js 16, React 19, TypeScript, the App Router, and Tailwind CSS 4. Its current homepage is a responsive presentation of the planned NewsFlow AI workflow and fixture-mode product controls.

Run it locally from the repository root:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Run `npm run lint` and `npm run build` before committing frontend changes. Application dependencies, `.next` output, local environment files, and logs remain excluded from Git.

### Backend application and PostgreSQL

The backend uses Python and FastAPI. NFA-13 provides the application foundation, and NFA-14 adds a PostgreSQL connection boundary, environment-based database settings, startup verification, and a tested `GET /ready` endpoint. Database credentials remain in the ignored local `.env` file and are never returned in API errors.

Use Python 3.10 or newer. Python 3.12 is recommended. Run it locally from the repository root:

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
fastapi dev app/main.py
```

Before starting the API, copy `.env.example` to `.env` and replace the PostgreSQL placeholders with the credentials for your local `newsflow` database. Keep the development server running, then open `http://127.0.0.1:8000/health` for API liveness, `http://127.0.0.1:8000/ready` for PostgreSQL readiness, or `http://127.0.0.1:8000/docs` for interactive API documentation. Run `pytest` before committing backend changes. The virtual environment, Python caches, test caches, local environment files, and logs remain excluded from Git.

Create or update the schema and load the optional development fixture from `apps/api`:

```bash
alembic upgrade head
SEED_DATA_ENABLED=true python -m app.database.seed
```

The seed loader runs only in development or test, contains fictional data on the reserved `example.invalid` domain, and is safe to run repeatedly without creating duplicates. It is disabled by default and refuses staging or production.

NFA-22 adds `POST /api/v1/auth/register`. It validates and normalises the email address, enforces the documented password policy, stores only an Argon2id hash, relies on PostgreSQL uniqueness for race-safe duplicate prevention, and never returns the password or hash. The interactive contract and example request are available at `http://127.0.0.1:8000/docs` while the backend is running.

NFA-23 adds `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, and `POST /api/v1/auth/logout`. A successful login verifies the Argon2id password hash, creates an absolute-expiry PostgreSQL session, and sends a random session identifier in an HTTP-only cookie. PostgreSQL stores only its SHA-256 hash. The current-user endpoint rejects missing, expired, revoked, and disabled-user sessions. Logout requires a session-specific CSRF token, revokes the server record, and expires the browser cookies. Login attempts are rate limited, invalid credentials use one generic response, and deployment cookies automatically require HTTPS in staging and production.

### Secure local configuration

Copy the safe example when local environment configuration is needed:

```bash
cp .env.example .env
```

Add real values only to `.env`. The `.env` file is ignored by Git and must never be committed. The committed example contains placeholders rather than working credentials. Replace the database and OpenAI placeholders only in `.env`:

```dotenv
DATABASE_URL=postgresql://your_local_user:your_local_password@localhost:5432/newsflow
OPENAI_API_KEY=your_real_openai_api_key
```

The FastAPI backend loads these values through one validated settings class and stores both as masked secret values. `DATABASE_URL` is required at API startup. `OPENAI_API_KEY` is required only when an OpenAI feature runs; a missing value or unchanged example placeholder produces a clear error without revealing a credential. OpenAI keys remain server-side and must never be placed in a `NEXT_PUBLIC_` variable. `NEWS_SOURCE_MODE` remains `fixture` because live CNN integration is not authorised. See the [backend configuration guide](apps/api/README.md#configure-the-application) for the full variable reference and operating rules.

### Docker development environment

NFA-16 runs the application as three cooperating containers:

- `frontend` runs the Next.js development server and is available at `http://localhost:3000`.
- `backend` runs FastAPI and is available at `http://localhost:8000`.
- `database` runs PostgreSQL and stores its data in the persistent `postgres_data` named volume.

For first-time setup, create the ignored local configuration file, replace its PostgreSQL placeholders, and start the stack:

```bash
cp .env.example .env
docker compose up --build
```

Docker waits for PostgreSQL to become healthy before starting FastAPI, then waits for FastAPI before starting Next.js. Stop the stack with `docker compose down`; this preserves the database volume. Full startup, shutdown, log, communication-test, persistence, and troubleshooting instructions are in the [Docker development guide](infrastructure/docker/README.md).

### Code quality and testing

NFA-17 records the following tool selection:

| Area | Tool | Purpose |
|---|---|---|
| Frontend linting | ESLint with Next.js Core Web Vitals and TypeScript rules | Finds React, Next.js, accessibility, and TypeScript-related mistakes. |
| Frontend formatting | Prettier | Applies one consistent format to frontend source and configuration files. |
| Frontend type checking | TypeScript | Detects incompatible types without creating build output. |
| Frontend testing | Vitest, React Testing Library, and jsdom | Tests React components in a lightweight simulated browser environment. |
| Backend linting and formatting | Ruff | Finds Python errors and common bug patterns, sorts imports, and formats Python. |
| Backend testing | Pytest | Runs API, configuration, readiness, and error-handling tests. |

Run the frontend checks from `apps/web`:

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

Run the backend checks from `apps/api` after installing the development dependencies:

```bash
ruff check .
ruff format --check .
pytest
```

Detailed commands and automatic-formatting instructions are in the [frontend guide](apps/web/README.md#quality-checks) and [backend guide](apps/api/README.md#code-quality).

## Key delivery gates

- **CNN access gate:** document a written, authorised feed, API, licensed service, or other permitted route before connecting the ingestion service to live CNN content. CNN International Commercial provides a route for licensing enquiries, and its published terms restrict unapproved reuse.
- **Grounding gate:** a post cannot be generated when the source fact pack is insufficient. Every factual claim must be traceable to the selected article data.
- **Safety gate:** generated imagery must not copy CNN photographs or branding, and sensitive stories must use non-deceptive illustration treatment with appropriate AI-generated labelling.
- **Release gate:** automated tests, security checks, user acceptance tests, documentation, and a rollback procedure must pass before release.

## Technical references

- [OpenAI API overview](https://developers.openai.com/api/reference/overview)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [OpenAI image generation](https://developers.openai.com/api/docs/guides/tools-image-generation)
- [OpenAI production best practices](https://developers.openai.com/api/docs/guides/production-best-practices)
- [argon2-cffi password hashing](https://argon2-cffi.readthedocs.io/en/stable/argon2.html)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [CNN International Commercial terms](https://commercial.cnn.com/terms-of-use/)
- [CNN International Commercial contact](https://commercial.cnn.com/contact-us/)

## Current next step

Review the NFA-23 authentication endpoints, session expiry, cookie controls, CSRF protection, rate limiting, and automated test evidence. Commit and merge the implementation through the normal GitHub workflow, then record the pull-request, implementation-commit, and merge-commit links in Jira. The backend can now register and authenticate users and load an OpenAI API key securely, but it does not yet make OpenAI API requests or connect to a live news source.

## Licence

No software licence has been selected yet. Add one before public distribution.
