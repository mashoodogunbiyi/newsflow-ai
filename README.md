# NewsFlow AI

NewsFlow AI is a planned full-stack application that turns authorised CNN International news information into original, source-grounded LinkedIn posts and accompanying AI-generated illustrations.

> Status: engineering foundation, secure accounts, and the provider-neutral news boundary are in progress. NFA-12 to NFA-18 provide the working application foundation and local development environment. NFA-20 and NFA-21 provide the approved schema, migrations, and synthetic seed data. NFA-22 to NFA-26 provide the secure account lifecycle, object-level authorisation, regression tests, and automatic quality checks. NFA-28 to NFA-32 provide the fixture-first provider boundary, validation, identity, provenance, and rights enforcement. NFA-33 adds durable article synchronisation. NFA-34 adds an authenticated, rights-aware article catalogue REST API. NFA-35 adds safe structured ingestion logs, job and provider durations, operational metrics, protected status APIs, and configurable health thresholds. NFA-36 adds a complete synthetic provider-to-PostgreSQL-to-REST test suite with an enforced backend coverage floor. NFA-38 adds a secure, reusable, bounded, and fully mocked OpenAI Responses API service in FastAPI. NFA-39 adds versioned, rights-aware, source-grounded LinkedIn prompt construction with injection safeguards and factual evaluation examples. NFA-40 connects those controls through an authenticated, rate-limited, owner-scoped LinkedIn draft generation service with strict structured-output validation and PostgreSQL metadata. NFA-41 adds the secure frontend-facing `POST /api/generations` contract with narrow responses and documented failure handling. NFA-42 adds deterministic factual-grounding checks, safe review warnings, trusted source-reference validation, and persisted validation evidence while keeping human verification mandatory. NFA-43 adds shared daily, concurrency, and duplicate generation controls, safe failure categories, token tracking, and operational guidance. NFA-44 adds a synthetic AI-quality dataset, explainable generation scoring, prompt-version regression detection, and an isolated optional live-model evaluation. NFA-45 adds content-free generation lifecycle auditing, request correlation, duration and token metrics, retention, and administrator-only monitoring endpoints. NFA-46 completes the E4 architecture, joined HTTP-to-draft acceptance verification, final acceptance record, and exact E6 frontend integration contract. NFA-48 adds a rights-aware, versioned image-prompt composer with controlled illustration choices, article-or-draft context, injection separation, restricted-photography protection, and non-deception rules. NFA-49 adds the central pre-provider image safety policy, sensitive-news classifications, documentary-evidence and real-person safeguards, conservative uncertainty, provider-control requirements, AI designation, and content-free decisions. ADR-001 continues to block all live CNN access.

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
- [docs/authorization.md](docs/authorization.md) - NFA-25 ownership rules, protected endpoints, safe failure behaviour, reusable implementation pattern, and automated evidence.
- [docs/testing.md](docs/testing.md) - NFA-26 test strategy, coverage map, isolated fixtures, local commands, PostgreSQL safety gates, and GitHub quality workflow.
- [docs/source-provider-interface.md](docs/source-provider-interface.md) - NFA-28 provider contract, normalised article model, pagination, safe errors, synthetic adapter, and future authorised-provider instructions.
- [docs/cnn-adapter.md](docs/cnn-adapter.md) - NFA-29 disabled CNN adapter, No-Go enforcement, acceptance status, test evidence, and future activation gates.
- [docs/article-normalisation.md](docs/article-normalisation.md) - NFA-30 field allowlist, rights policy, normalisation, validation, sanitisation, safe errors, and automated evidence.
- [docs/article-identity-and-deduplication.md](docs/article-identity-and-deduplication.md) - NFA-31 identity strategy, canonical URL fallback, PostgreSQL constraints, atomic ingestion, safe updates, and tests.
- [docs/article-provenance-and-rights.md](docs/article-provenance-and-rights.md) - NFA-32 provenance events, versioned rights, attribution, retention, fail-closed checks, and automated evidence.
- [docs/article-synchronisation.md](docs/article-synchronisation.md) - NFA-33 scheduled and manual synchronisation, durable jobs, checkpoints, leases, retries, security, and tests.
- [docs/article-catalogue-api.md](docs/article-catalogue-api.md) - NFA-34 article list and detail endpoints, authentication, public fields, cursor pagination, rights filtering, errors, and tests.
- [docs/ingestion-observability.md](docs/ingestion-observability.md) - NFA-35 structured logs, safe fields, metrics, administrator endpoints, health indicators, thresholds, and operational response.
- [docs/article-pipeline-testing.md](docs/article-pipeline-testing.md) - NFA-36 pipeline test strategy, synthetic fixtures, isolated PostgreSQL environment, automation, results, and limitations.
- [docs/openai-integration.md](docs/openai-integration.md) - NFA-38 backend-only OpenAI service, configuration, structured results, safe errors, limits, mocked tests, and next steps.
- [docs/linkedin-prompting.md](docs/linkedin-prompting.md) - NFA-39 prompt versions, grounding rules, rights gates, preferences, injection safeguards, output contract, tests, and evaluation examples.
- [docs/linkedin-generation-service.md](docs/linkedin-generation-service.md) - NFA-40 authenticated generation workflow, rights checks, structured output, persistence, request controls, errors, and tests.
- [docs/generation-api.md](docs/generation-api.md) - NFA-41 frontend-facing generation request, response, authentication, rights, limit, error, OpenAPI, and test contract.
- [docs/factual-grounding-validation.md](docs/factual-grounding-validation.md) - NFA-42 deterministic grounding rules, validation statuses, safe warnings, persistence, limitations, and tests.
- [docs/generation-operations.md](docs/generation-operations.md) - NFA-43 shared usage limits, duplicate protection, safe generation errors, token records, retry policy, tests, and troubleshooting.
- [docs/ai-generation-evaluation.md](docs/ai-generation-evaluation.md) - NFA-44 synthetic dataset, quality scoring, deterministic tests, prompt regression procedure, optional live evaluation, and limitations.
- [docs/generation-monitoring.md](docs/generation-monitoring.md) - NFA-45 generation lifecycle events, request correlation, protected audit and metrics APIs, retention, tests, and troubleshooting.
- [docs/architecture/ai-generation-architecture.md](docs/architecture/ai-generation-architecture.md) - NFA-46 complete E4 component architecture, request lifecycle, controls, monitoring, limitations, and readiness statement.
- [docs/e4-generation-acceptance.md](docs/e4-generation-acceptance.md) - NFA-46 acceptance criteria, joined scenarios, verification results, known limitations, and E4 decision.
- [docs/e6-generation-integration-contract.md](docs/e6-generation-integration-contract.md) - exact E6 request, response, security, error, review, and accessibility handoff for the future Next.js interface.
- [docs/image-prompt-composer.md](docs/image-prompt-composer.md) - NFA-48 supported styles and layouts, source-rights gates, article-or-draft context, prompt separation, non-deception controls, errors, tests, and limitations.
- [docs/image-safety-policy.md](docs/image-safety-policy.md) - NFA-49 sensitive categories, central decisions, documentary and real-person restrictions, provider controls, safe records, tests, and limitations.
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
├── .github/workflows/      # Automated pull-request and main-branch quality checks
├── compose.yaml             # Frontend, backend, and PostgreSQL development stack
├── apps/
│   ├── api/                 # FastAPI application, Alembic migrations, seed data, and Dockerfile
│   └── web/                 # Next.js application and development Dockerfile
├── packages/                # Shared contracts, schemas, or generated clients
├── infrastructure/
│   ├── database/            # Future hosted database, backup, and restore configuration
│   └── docker/              # Container and local-service configuration
├── docs/
│   ├── authorization.md     # Object-level authorisation rules and evidence
│   ├── article-identity-and-deduplication.md # Stable identity and atomic ingestion rules
│   ├── article-normalisation.md # Rights-aware article processing rules and tests
│   ├── article-provenance-and-rights.md # Provenance and versioned permission rules
│   ├── article-synchronisation.md # Scheduled and manual ingestion workflow
│   ├── article-catalogue-api.md # Authenticated rights-aware article REST API
│   ├── ingestion-observability.md # Ingestion logs, metrics, health, and operations
│   ├── article-pipeline-testing.md # Complete synthetic pipeline test strategy and results
│   ├── openai-integration.md # Secure backend OpenAI integration and test evidence
│   ├── linkedin-prompting.md # Grounded LinkedIn prompt contract and evaluations
│   ├── linkedin-generation-service.md # Authenticated private draft generation workflow
│   ├── generation-api.md # Secure frontend-facing LinkedIn generation REST API
│   ├── generation-operations.md # Generation usage limits, failures, and operations
│   ├── ai-generation-evaluation.md # AI quality scoring and regression framework
│   ├── generation-monitoring.md # Generation audit, metrics, retention, and troubleshooting
│   ├── image-prompt-composer.md # Safe versioned illustration prompt construction
│   ├── image-safety-policy.md # Central sensitive-news illustration safety policy
│   ├── e4-generation-acceptance.md # E4 joined verification and acceptance record
│   ├── e6-generation-integration-contract.md # Future frontend generation contract
│   ├── cnn-adapter.md       # Disabled CNN adapter decision and test evidence
│   ├── development-setup.md # Complete local development guide
│   ├── source-provider-interface.md # Provider-neutral news boundary
│   ├── testing.md           # Automated test strategy and commands
│   ├── architecture/        # Architecture Decision Records and E4 system design
│   └── jira/                # Jira task deliverables and approved baselines
├── tests/                   # Cross-service and end-to-end tests
├── .editorconfig            # Shared text-formatting defaults
├── .env.example             # Safe local configuration template
├── .gitignore               # Excludes secrets, dependencies, builds, and local files
├── README.md
├── PROJECT_PLAN.md
└── PROJECT_MANAGEMENT.md
```

The frontend and backend directories contain working application foundations. PostgreSQL connection configuration and readiness checking are implemented in the backend. Environment variables are validated centrally, secret values are masked, and unsafe example placeholders are rejected. Docker Compose can run the frontend, backend, and database together with health-based startup ordering and persistent PostgreSQL storage. NFA-20 to NFA-32 provide the database, secure accounts, provider boundary, safe article ingestion, provenance, and rights controls. NFA-33 connects those components through a reusable synchronisation workflow with durable operational evidence. NFA-34 gives authenticated frontend users a rights-aware REST boundary for browsing current permitted article metadata. NFA-35 makes ingestion operations inspectable through safe structured logs, durable timing and failure dimensions, protected monitoring endpoints, and configurable health indicators. NFA-36 proves the joined pipeline with reusable synthetic records, isolated PostgreSQL, rights and failure checks, authenticated REST retrieval, and automated coverage enforcement. NFA-38 adds a server-only OpenAI SDK boundary with validated limits, structured results, safe failure mapping, usage metadata, and mocked tests. NFA-39 converts validated preferences and rights-approved source fields into separated trusted instructions and untrusted article input while preserving the exact source reference outside generated prose. NFA-40 exposes authenticated draft creation and owner-only retrieval, verifies current rights before provider access, validates strict JSON and word limits, records auditable generation metadata, and keeps human review mandatory. NFA-41 gives the future Next.js interface a narrow, documented REST contract for requesting those drafts. NFA-42 evaluates generated text against the permitted source fields, preserves safe warning evidence, rejects blocking failures, and never treats automated checks as factual verification. NFA-43 reserves each provider-bound attempt in PostgreSQL, enforces shared daily and concurrent allowances, stops active duplicates, and records safe completion, failure, model, and token evidence. NFA-44 evaluates required generation properties with reusable synthetic fixtures, explicit thresholds, safe findings, and prompt-version comparisons without requiring live external services. NFA-45 correlates safe start, rights, usage, validation, completion, and failure events, exposes administrator-only inspection and aggregate metrics, and applies configurable retention without storing prompts, article content, or drafts. NFA-46 documents this complete E4 architecture, verifies the joined authenticated HTTP-to-private-draft path, records final E4 acceptance, and gives E6 an exact secure integration contract. NFA-48 prepares safe, versioned illustration prompts from authorised article context and an optional associated private draft without calling an image provider. NFA-49 evaluates each composed request before provider access, forces conceptual treatment, blocks deceptive or unresolved requests, and records only safe policy metadata. Shared packages and cross-service tests will be added by their related engineering tasks.

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
| `docs/article-identity-and-deduplication.md` | NFA-31 identity, deduplication, atomic ingestion, update, and test rules |
| `docs/article-normalisation.md` | NFA-30 rights-aware mapping, validation, sanitisation, error rules, and tests |
| `docs/article-provenance-and-rights.md` | NFA-32 provenance, versioned permissions, fail-closed checks, and tests |
| `docs/article-synchronisation.md` | NFA-33 job lifecycle, schedule, manual trigger, checkpoint, retry, and recovery rules |
| `docs/article-catalogue-api.md` | NFA-34 REST endpoints, public schema, authentication, pagination, filtering, rights, and tests |
| `docs/ingestion-observability.md` | NFA-35 safe logs, durations, metrics, administrator status endpoints, health thresholds, and response process |
| `docs/article-pipeline-testing.md` | NFA-36 complete synthetic pipeline strategy, isolation, coverage, results, and limitations |
| `docs/openai-integration.md` | NFA-38 OpenAI service architecture, configuration, security, error handling, tests, and limitations |
| `docs/linkedin-prompting.md` | NFA-39 prompt versions, permitted fields, grounding, preferences, injection protection, evaluations, and tests |
| `docs/linkedin-generation-service.md` | NFA-40 generation orchestration, API, rights, persistence, validation, controls, and tests |
| `docs/generation-api.md` | NFA-41 frontend generation endpoint, public schema, security, failure mapping, OpenAPI, and tests |
| `docs/factual-grounding-validation.md` | NFA-42 grounding requirements, validation policy, safe results, persistence, limitations, and tests |
| `docs/generation-operations.md` | NFA-43 generation limits, duplicate control, retry policy, usage evidence, safe errors, tests, and troubleshooting |
| `docs/ai-generation-evaluation.md` | NFA-44 generation quality criteria, scoring, fixtures, regression process, tests, and limitations |
| `docs/generation-monitoring.md` | NFA-45 lifecycle audit events, request correlation, aggregate metrics, protected access, retention, tests, and troubleshooting |
| `docs/architecture/ai-generation-architecture.md` | NFA-46 complete E4 architecture, lifecycle, security controls, monitoring, limitations, and readiness |
| `docs/e4-generation-acceptance.md` | NFA-46 joined acceptance scenarios, verification results, limitations, and final E4 decision |
| `docs/e6-generation-integration-contract.md` | Secure request, response, CSRF, error, review, and accessibility contract for E6 |
| `docs/image-prompt-composer.md` | NFA-48 illustration parameters, rights and context checks, injection separation, safety rules, tests, and limitations |
| `docs/image-safety-policy.md` | NFA-49 sensitive-news decisions, provider gate, non-deception and person safeguards, metadata, tests, and limitations |
| `docs/authorization.md` | Object ownership rules, protected operations, safe errors, and test evidence |
| `docs/cnn-adapter.md` | NFA-29 disabled CNN boundary, blocked criteria, tests, and future activation gates |
| `docs/source-provider-interface.md` | Provider interface, article contract, fixture adapter, safe errors, and integration instructions |
| `docs/testing.md` | Account-security test layers, coverage, isolation, commands, and CI behaviour |
| `docs/jira` | Approved Jira deliverables and project-governance evidence |
| `docs/development-setup.md` | Software requirements, setup, configuration, testing, verification, and troubleshooting |
| `tests` | Cross-application, integration, and end-to-end tests |
| `compose.yaml` | Local multi-container development configuration |

Start with the complete [local development guide](docs/development-setup.md). The frontend also has its own [setup and structure guide](apps/web/README.md). The generated [Next.js agent instructions](apps/web/AGENTS.md) record version-specific framework rules that contributors and coding tools must follow. The backend has a separate [FastAPI setup and structure guide](apps/api/README.md).

### Frontend application

The frontend uses Next.js 16, React 19, TypeScript, the App Router, and Tailwind CSS 4. It includes a responsive homepage and the NFA-24 authentication experience:

- `/register` creates an account through the FastAPI registration endpoint.
- `/login` starts a secure server-managed session.
- `/dashboard` restores and validates the current session on refresh and redirects unauthenticated visitors.
- The dashboard logout control submits the CSRF token required by FastAPI and ends the session.

Browser authentication requests go through same-origin Next.js route handlers under `/api/auth`. Those handlers forward only authentication cookies and required headers to FastAPI. The HTTP-only session cookie is never read by client-side JavaScript, and no session secret is stored in browser storage.

Run it locally from the repository root:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The backend and PostgreSQL must also be running to register, log in, restore a session, or log out. Run `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`, and `npm run build` before committing frontend changes. Application dependencies, `.next` output, local environment files, and logs remain excluded from Git.

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

Before starting the API, copy `.env.example` to `.env` and replace the PostgreSQL placeholders with the credentials for your local `newsflow` database. Keep the development server running, then open `http://127.0.0.1:8000/health` for API liveness, `http://127.0.0.1:8000/ready` for PostgreSQL readiness, or `http://127.0.0.1:8000/docs` for interactive API documentation. Run `pytest --cov=app --cov-report=term-missing --cov-fail-under=75` before committing backend changes. The virtual environment, Python caches, test caches, local environment files, and logs remain excluded from Git.

Create or update the schema and load the optional development fixture from `apps/api`:

```bash
alembic upgrade head
SEED_DATA_ENABLED=true python -m app.database.seed
```

The seed loader runs only in development or test, contains fictional data on the reserved `example.invalid` domain, and is safe to run repeatedly without creating duplicates. It is disabled by default and refuses staging or production.

NFA-22 adds `POST /api/v1/auth/register`. It validates and normalises the email address, enforces the documented password policy, stores only an Argon2id hash, relies on PostgreSQL uniqueness for race-safe duplicate prevention, and never returns the password or hash. The interactive contract and example request are available at `http://127.0.0.1:8000/docs` while the backend is running.

NFA-23 adds `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, and `POST /api/v1/auth/logout`. A successful login verifies the Argon2id password hash, creates an absolute-expiry PostgreSQL session, and sends a random session identifier in an HTTP-only cookie. PostgreSQL stores only its SHA-256 hash. The current-user endpoint rejects missing, expired, revoked, and disabled-user sessions. Logout requires a session-specific CSRF token, revokes the server record, and expires the browser cookies. Login attempts are rate limited, invalid credentials use one generic response, and deployment cookies automatically require HTTPS in staging and production.

NFA-25 adds private content-library endpoints under `/api/v1/library/items`. Every create, list, read, update, delete, and export operation derives its owner from the active session and includes that owner in the persistence query. Request bodies cannot set `user_id`. State changes require CSRF proof, private responses are not cacheable, and missing resources look identical to another user's resources. The complete rules and test evidence are in [the object-level authorisation guide](docs/authorization.md).

NFA-28 adds a provider-neutral `NewsProvider` interface in the FastAPI backend. The bundled provider maps original synthetic records into the approved NFA-6 article structure, including provenance, attribution, rights, permitted content, timestamps, and safe HTTPS URLs. Provider pages support opaque cursors and incremental publication-date filtering. Application services receive the interface through dependency injection, so a future authorised adapter can replace the fixture provider without spreading provider-specific field names through the application. Live CNN access remains unavailable. See the [source-provider interface guide](docs/source-provider-interface.md).

NFA-29 adds `CnnSourceAdapter` as a disabled implementation of the same provider interface. Both discovery and detail retrieval raise `SOURCE_NOT_AUTHORISED` before an HTTP client can be called. The configuration still rejects a `cnn` mode, and the code contains no CNN endpoint, credential, provider response, or network logic. The [CNN adapter record](docs/cnn-adapter.md) explains why the live acceptance criteria remain blocked.

NFA-30 sends each synthetic provider record through a rights-aware `ArticleNormalisationService` before the fixture provider returns it. The service reads only approved input fields, maps provider-specific names, normalises Unicode, whitespace, UTC timestamps, categories, and canonical URLs, and rejects unsafe markup, invalid data, unapproved hosts, or prohibited rights states. Trusted attribution and provenance come from the source policy rather than the untrusted record. See the [article normalisation guide](docs/article-normalisation.md).

NFA-31 prefers the permitted provider item ID and derives a deterministic canonical-URL hash only when that ID is unavailable. The PostgreSQL repository uses the existing source-identity and canonical-URL uniqueness constraints with atomic conflict handling. Repeated records are skipped, permitted metadata changes create a new immutable snapshot, and the stable article ID and earlier snapshot relationships are preserved. See the [article identity and deduplication guide](docs/article-identity-and-deduplication.md).

NFA-32 records an immutable provenance event for every created, updated, or skipped ingestion and stores permissions as versioned PostgreSQL rights records. The reusable rights service denies missing, unverified, revoked, expired, disabled-source, or ungranted operations by default. AI generation requires both AI-processing and derivative-output permission, and required attribution remains available with the decision. See the [article provenance and rights guide](docs/article-provenance-and-rights.md).

NFA-33 runs the same approved provider, normalisation, deduplication, provenance, and rights pipeline for scheduled and administrator-triggered synchronisation. PostgreSQL stores job statuses, counts, incremental checkpoints, schedule reservations, and expiring worker leases. Only administrators with CSRF proof can start a manual job, temporary provider failures receive bounded retries, and failed or partial jobs do not advance the checkpoint. See the [article synchronisation guide](docs/article-synchronisation.md).

NFA-34 adds authenticated `GET /api/articles` and `GET /api/articles/{article_id}` endpoints. FastAPI validates cursor pagination, permitted metadata search, provider and publication-date filters, and newest or oldest sorting. SQLAlchemy queries only current PostgreSQL snapshots whose article, source, display, verification, attribution, and retention states allow disclosure. Restricted and missing records share the same 404 response. Internal rights versions, provider database identifiers, snapshot identifiers, and stored-content fields are excluded from the public Pydantic schema. See the [article catalogue API guide](docs/article-catalogue-api.md).

NFA-35 adds JSON or console structured logging for ingestion start, provider requests, retries, completion, partial completion, and safe failure events. The existing durable sync-job records now include cumulative provider-request duration, stable error category, and failure stage. Authenticated administrators can inspect recent jobs, individual jobs, aggregate metrics, and threshold-based health through `GET /api/admin/sync/jobs`, `GET /api/admin/sync/jobs/{job_id}`, `GET /api/admin/sync/metrics`, and `GET /api/admin/sync/health`. Logs and responses exclude raw article content, provider payloads, URLs, credentials, and traceback details. See the [ingestion observability guide](docs/ingestion-observability.md).

NFA-36 tests that those article components work together, not only in isolation. Original synthetic fixtures pass through the provider, normalisation, deduplication, PostgreSQL, provenance, rights, synchronisation, observability, and authenticated catalogue layers. Safety-gated tests cover valid, invalid, updated, repeated, concurrent, restricted, disabled-source, and database-failure paths without live CNN access. GitHub Actions now supplies a short-lived `newsflow_pipeline_test` PostgreSQL service and enforces at least 75 percent branch-aware backend coverage. See the [article pipeline testing guide](docs/article-pipeline-testing.md).

NFA-38 adds a reusable `OpenAIService` inside FastAPI. The service uses the official asynchronous OpenAI Python SDK and Responses API, reads the key and model only from backend configuration, enforces timeout, output-token, and retry limits, maps provider failures to safe application errors, and returns structured usage metadata. Its tests inject mocked SDK clients and never make a live or billable request. The service itself remains internal; NFA-40 and NFA-41 now provide the authenticated, rights-aware application workflow and public API boundary around it. See the [OpenAI integration guide](docs/openai-integration.md).

NFA-39 adds the versioned `linkedin_post_v1` template and `LinkedInPromptBuilder`. It requires a current allowed AI-generation rights decision, rejects missing or restricted permitted content, accepts only professional, conversational, or analytical tone and short, medium, or long length enums, and passes only the six approved source fields as untrusted JSON. The prompt package keeps the canonical URL, attribution, provider item ID, and rights version outside generated prose. Its tests and synthetic evaluation cases cover grounding, insufficiency, unsupported preferences, restricted fields, and prompt injection without calling OpenAI. See the [LinkedIn prompting guide](docs/linkedin-prompting.md).

NFA-40 adds authenticated `POST /api/v1/linkedin-drafts` and owner-scoped `GET /api/v1/linkedin-drafts/{draft_id}` endpoints. The service retrieves the current PostgreSQL article snapshot, checks current AI-processing rights, reuses the NFA-39 builder and NFA-38 OpenAI boundary, requests strict JSON Schema output, validates the result and word range, and stores a private draft plus its source reference, rights version, model, prompt version, and token usage. Per-user limits, optional idempotency keys, CSRF protection, safe errors, no-store responses, and mandatory human review prevent uncontrolled or automatic publication. See the [LinkedIn generation service guide](docs/linkedin-generation-service.md).

NFA-41 adds `POST /api/generations` as the smaller frontend-facing contract. FastAPI authenticates the user, validates CSRF proof, article UUID, tone, length, extra fields, and idempotency header, then delegates to NFA-40 so article access and source rights still fail before OpenAI is contacted. The `201` response contains only the generation ID, article and source reference, draft, preferences, review state, safe grounding result, and creation time. Documented safe responses distinguish validation, missing or restricted articles, request limits, invalid provider output, unavailable services, and upstream timeouts without exposing prompts, provider metadata, rights internals, credentials, or traces. See the [generation API guide](docs/generation-api.md).

NFA-42 runs after strict JSON and word-limit validation and before draft persistence. Deterministic checks compare numerical claims, direct quotations, dates, named entities, and factual assertions with only the permitted article fields. Trusted article IDs and canonical URLs remain backend-controlled. Results are `passed_automated_checks`, `review_required`, or `rejected`, but every stored draft still has `review_required = true`. Safe warning codes and counts are persisted without prompt, article, or claim excerpts. A passed status never means factually verified. See the [factual grounding and output validation guide](docs/factual-grounding-validation.md).

NFA-43 adds a shared PostgreSQL reservation before every provider-bound generation. Per-user daily and concurrent allowances, expiring attempt leases, and active idempotency fingerprints prevent uncontrolled or duplicate OpenAI calls across backend instances. Successful attempts record available token counts, while failures record only a safe category. Bounded SDK retries, provider `Retry-After` handling, safe API errors, retention, troubleshooting, and synthetic automated tests are documented in the [generation operations guide](docs/generation-operations.md).

NFA-44 adds a reusable evaluation package that gives each mocked LinkedIn draft an explainable report across structure, factual grounding, source attribution, tone, length, writing quality, and safety. Original synthetic articles and stored mocked OpenAI outputs make routine runs deterministic and free from live CNN or OpenAI access. Prompt versions are compared by property score rather than exact wording, and any lower dimension is reported as a regression. A deliberately gated `live_ai` test remains separate and never runs in normal CI. See the [AI generation evaluation guide](docs/ai-generation-evaluation.md).

NFA-45 adds a random request identifier and content-free audit events around the NFA-40 to NFA-43 generation workflow. PostgreSQL records safe start, rights, usage rejection, validation, completion, and failure evidence plus duration and stable categories. Existing NFA-43 usage events remain the source for token totals. Authenticated administrators can query recent events and aggregate metrics through `/api/admin/generations/audit` and `/api/admin/generations/metrics`; ordinary users are denied. See the [generation monitoring and audit guide](docs/generation-monitoring.md).

NFA-46 brings the E4 work together. The architecture record explains the complete authenticated request lifecycle and component boundaries, while a joined acceptance suite exercises the real FastAPI route, generation orchestration, rights checks, prompt builder, grounding validator, usage tracking, and audit tracking with a mocked OpenAI boundary and synthetic source data. The final acceptance record documents the result and limitations, and the E6 contract defines the exact safe Next.js integration without implementing the future interface. See the [E4 architecture](docs/architecture/ai-generation-architecture.md), [acceptance record](docs/e4-generation-acceptance.md), and [E6 contract](docs/e6-generation-integration-contract.md).

NFA-48 starts the image-generation safety boundary without generating an image. Strict schemas allow four illustration styles, three aspect ratios, and three safe compositions. `ImagePromptComposer` requires current AI-processing and derivative rights, includes only approved article fields, optionally accepts a matching non-rejected private LinkedIn draft as untrusted thematic context, and returns separated masked instructions and data under `image_prompt_v1`. The template prohibits copying CNN or other restricted photography, unsupported real-event detail, recognisable real people, photorealistic documentary treatment, logos, and misleading evidence claims. See the [image-prompt composer guide](docs/image-prompt-composer.md).

NFA-49 evaluates every NFA-48 result before a future provider call. Deterministic rules classify conflict, terrorism, disasters, deaths or serious injuries, health emergencies, elections and political events, criminal allegations, identifiable-person sensitive events, and uncertainty. Only allowed or restricted conceptual decisions can continue. Documentary fabrication, misleading real-person depictions, frontend override attempts, and sensitive requests without essential provider moderation are rejected; uncertain requests stop for review. Every decision keeps photorealism and documentary use disabled, preserves an AI-generated illustration designation, requires human review, and can record only content-free metadata under `image_safety_v1`. See the [image safety policy](docs/image-safety-policy.md).

### Secure local configuration

Copy the safe example when local environment configuration is needed:

```bash
cp .env.example .env
```

Add real values only to `.env`. The `.env` file is ignored by Git and must never be committed. The committed example contains placeholders rather than working credentials. Replace the database and OpenAI placeholders only in `.env`:

```dotenv
DATABASE_URL=postgresql://your_local_user:your_local_password@localhost:5432/newsflow
OPENAI_API_KEY=your_real_openai_api_key
OPENAI_MODEL=your_approved_openai_model
OPENAI_REQUEST_TIMEOUT=30
OPENAI_MAX_OUTPUT_TOKENS=800
OPENAI_MAX_RETRIES=2
GENERATION_RATE_LIMIT_ATTEMPTS=10
GENERATION_RATE_LIMIT_WINDOW_SECONDS=60
GENERATION_DAILY_LIMIT=50
GENERATION_CONCURRENT_LIMIT=2
GENERATION_ATTEMPT_TIMEOUT_SECONDS=180
GENERATION_USAGE_RETENTION_DAYS=90
GENERATION_AUDIT_RETENTION_DAYS=90
GENERATION_MONITORING_WINDOW_HOURS=24
```

The FastAPI backend loads these values through validated settings and stores credentials as masked secret values. `DATABASE_URL` is required at API startup. `OPENAI_API_KEY` and `OPENAI_MODEL` are required only when the OpenAI service is initialised; missing or unchanged example values produce clear errors without revealing a credential. OpenAI keys remain server-side and must never be placed in a `NEXT_PUBLIC_` variable. NFA-38 bounds the request timeout, maximum output tokens, and eligible SDK retries. `API_INTERNAL_BASE_URL` is a server-only Next.js setting for reaching FastAPI and contains no credentials. `NEWS_SOURCE_MODE` remains `fixture` because live CNN integration is not authorised. See the [backend configuration guide](apps/api/README.md#configure-the-application) for the full variable reference and operating rules.

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
| Backend testing and coverage | Pytest and Pytest-cov | Runs backend tests and enforces the documented branch-aware coverage floor. |

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
pytest --cov=app --cov-report=term-missing --cov-fail-under=75
```

Detailed commands and automatic-formatting instructions are in the [frontend guide](apps/web/README.md#quality-checks) and [backend guide](apps/api/README.md#code-quality).

NFA-26 adds a complete account-security regression journey and a safety-gated PostgreSQL ownership test. NFA-28 to NFA-32 test the provider boundary, disabled CNN access, normalisation, identity, provenance, and rights decisions. NFA-33 adds synchronisation tests. NFA-34 adds authenticated catalogue API tests. NFA-35 adds logging safety, duration, metric, health-threshold, protected monitoring API, and migration tests. NFA-36 adds the complete isolated article pipeline suite and branch-aware coverage enforcement. NFA-38 adds mocked OpenAI success, configuration, usage, error, cost-control, retry, and redaction tests. NFA-39 adds prompt construction, field allowlist, rights, preference, insufficiency, injection, versioning, and grounding-evaluation tests. NFA-40 adds complete orchestration, structured-output validation, authentication, rate-limit, idempotency, failure, source-reference, and private-owner retrieval tests. NFA-41 adds frontend API contract, validation, security, response minimisation, failure-mapping, limit, and OpenAPI tests. NFA-42 adds synthetic tests for valid grounding, empty and malformed output, unsupported numbers, quotations, entities and assertions, source-reference integrity, insufficient context, opinion framing, safe warnings, rejection before persistence, response fields, and migration evidence. NFA-43 tests generation usage limits and safe provider failure handling. NFA-44 adds deterministic scoring and property-based prompt regression tests with a separate opt-in live-model marker. NFA-45 adds lifecycle correlation, rights, validation, rejection, duration, token metric, retention, redaction, and protected administrator API tests. NFA-46 adds joined authenticated HTTP-to-draft acceptance coverage across rights, preferences, source sufficiency, provider failures, grounding, usage controls, audit evidence, trusted source references, mandatory review, and absence of automatic publishing. NFA-48 adds synthetic unit coverage for controlled image styles and layouts, source allowlisting, current rights, restricted and insufficient context, draft association, injection separation, non-deception, and prompt versioning. NFA-49 adds sensitive-category, documentary-fabrication, real-person, override, injection, uncertainty, provider-control, decision-record, designation, and provider-gate tests. GitHub automatically runs the backend, pipeline, and frontend quality checks for pull requests and updates to `main`. See the [testing guide](docs/testing.md) and the feature guides above for targeted commands.

## Key delivery gates

- **CNN access gate:** document a written, authorised feed, API, licensed service, or other permitted route before connecting the ingestion service to live CNN content. CNN International Commercial provides a route for licensing enquiries, and its published terms restrict unapproved reuse.
- **Grounding gate:** a post cannot be generated when the source fact pack is insufficient. Every factual claim must be traceable to the selected article data.
- **Safety gate:** generated imagery must not copy CNN photographs or branding, and sensitive stories must use non-deceptive illustration treatment with appropriate AI-generated labelling.
- **Release gate:** automated tests, security checks, user acceptance tests, documentation, and a rollback procedure must pass before release.

## Technical references

- [OpenAI API overview](https://developers.openai.com/api/reference/overview)
- [OpenAI Python SDK](https://developers.openai.com/api/reference/python)
- [OpenAI Responses API create method](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
- [OpenAI prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
- [OpenAI safety in building agents](https://developers.openai.com/api/docs/guides/agent-builder-safety)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [OpenAI image generation](https://developers.openai.com/api/docs/guides/tools-image-generation)
- [OpenAI production best practices](https://developers.openai.com/api/docs/guides/production-best-practices)
- [argon2-cffi password hashing](https://argon2-cffi.readthedocs.io/en/stable/argon2.html)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [CNN International Commercial terms](https://commercial.cnn.com/terms-of-use/)
- [CNN International Commercial contact](https://commercial.cnn.com/contact-us/)

## Current next step

Review the NFA-49 sensitive categories, provider-call gate, decision metadata, provider controls, automated tests, safety rules, and limitations. Then merge the branch and record the final evidence in Jira before implementing an image-provider integration. Live CNN access remains blocked because no authorised method or Go decision exists. Image generation still needs an approved provider and model, secure provider integration, output validation, storage, lifecycle controls, user interface, and human review.

## Licence

No software licence has been selected yet. Add one before public distribution.
