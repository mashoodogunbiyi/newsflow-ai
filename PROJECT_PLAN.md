# NewsFlow AI — Project Plan

- **Plan version:** 1.0
- **Last updated:** 11 October 2026
- **Delivery model:** two-week sprints; three-sprint target for a small cross-functional team, subject to capacity and the CNN access gate
- **Project status:** planning

## 1. Purpose

Deliver a full-stack application that uses an authorised CNN International data source to create original, factual LinkedIn posts and original AI-generated illustrations. The plan converts the project brief into traceable Epics and Tasks from discovery through handover.

The six-week target is a planning baseline, not a promise. It assumes a small cross-functional team can work on web, API/data, and assurance tasks in parallel. A solo developer should reforecast after the first sprint and should expect additional sprints rather than cutting rights, security, grounding, or test work. The largest external dependency is obtaining a permitted CNN access method. Development can continue with synthetic fixtures while that decision is pending, but a release claiming live CNN integration cannot pass without authorisation.

## 2. Outcomes and success measures

The release is successful when:

- A user can register, sign in, sign out, and access only their own content.
- Recent CNN items are obtained only through a documented, permitted access method.
- A user can browse and filter articles, select one, and view its source link and metadata.
- A user can choose tone, length, and audience and generate a LinkedIn post.
- Generated factual claims are supported by the stored source fact pack; insufficient data produces a clear refusal to generate.
- Every post visibly attributes and links to the original CNN page.
- A user can generate and independently regenerate an original, suitable image.
- A user can edit, preview, save, retrieve, copy, download, and delete their own content.
- The complete workflow runs locally from documented commands and passes the agreed test and security gates.

Suggested operational targets for the MVP:

| Measure | Target |
|---|---|
| Source-grounding evaluation | 100% of sampled factual claims mapped to supplied fact IDs; no unsupported claim accepted in release UAT |
| Duplicate article rate | 0 duplicate canonical URLs in the active catalogue |
| API error handling | All external API failures return a safe user message and a traceable server log |
| Accessibility | Core workflow usable by keyboard with labelled controls and visible focus states |
| Test gate | All critical-path tests pass; no open critical/high security defect |
| Secrets | No API key in client bundles, logs, fixtures, source control, or screenshots |

## 3. Scope

### In scope

- Authorised CNN news discovery and processing.
- Article browsing and category filtering.
- OpenAI-backed LinkedIn post and image generation.
- Tone, length, and audience controls.
- Grounding, source sufficiency, attribution, and source lineage.
- Authentication and user-specific saved content.
- Editing, regeneration, LinkedIn-style preview, copy, image download, and deletion.
- PostgreSQL persistence, object storage, REST API, Docker, tests, and documentation.

### Out of scope for the first release

- Direct LinkedIn publishing or scheduling.
- News sources other than CNN.
- Video generation, subscriptions, payments, or social analytics.
- Reuse of CNN photographs, CNN branding, or bulk article copying.
- Bypassing paywalls, robots controls, authentication, rate limits, or other access restrictions.

## 4. Delivery principles

1. **Permission before ingestion.** Store and process only fields permitted by the agreed CNN route. The access decision is recorded in an Architecture Decision Record (ADR).
2. **Facts before fluency.** The generation input is a bounded fact pack, never unconstrained browsing or model memory.
3. **Human review before export.** The product generates a draft; the user reviews and edits it before manual publication.
4. **Backend-only secrets.** External APIs are called from FastAPI, with credentials supplied by environment variables or a secret manager.
5. **Replaceable adapters.** CNN access, OpenAI, and object storage sit behind interfaces so they can be tested with fakes and changed independently.
6. **Traceability.** Every generation stores its source snapshot/version, prompt-template version, model identifier, parameters, status, and request trace ID.
7. **Minimal permitted retention.** Do not retain full copyrighted article bodies unless the licence explicitly permits it.

## 5. Target architecture

```text
Browser / Next.js
        |
        | HTTPS + secure session cookie
        v
FastAPI REST API
  |-- Authentication and authorisation
  |-- Article catalogue service ------> CNN source adapter (authorised route only)
  |-- Fact-pack and grounding service
  |-- Post generation service --------> OpenAI Responses API
  |-- Image generation service -------> OpenAI image generation
  |-- Content library service
        |                    |
        v                    v
   PostgreSQL          S3-compatible storage
        ^
        |
  Worker / scheduler
```

Core planned entities:

- `users` and `sessions`
- `articles` for permitted metadata and canonical URL identity
- `source_snapshots` for the exact permitted facts used by a generation
- `posts` and `post_versions` for editable content and regeneration history
- `generated_images` for prompt metadata, storage key, and safety labelling
- `generation_runs` for provider/model, template version, latency, token/usage metadata, status, error class, and trace ID

## 6. OpenAI implementation plan

### Text generation

- Use the official Python SDK from the FastAPI backend and the **Responses API** for new text-generation work.
- Keep `OPENAI_API_KEY`, `OPENAI_TEXT_MODEL`, and the OpenAI project identifier in server-side configuration. Select a model available to the project, pin its version for repeatable evaluation, and change models only through configuration plus regression tests.
- Convert permitted CNN fields into a numbered fact pack containing only the article headline, publication date, canonical URL, description, category, and any additional text the licence allows.
- Run a deterministic pre-check for minimum source sufficiency. Missing or thin data returns `INSUFFICIENT_SOURCE` without a generation call.
- Use a versioned prompt template that specifies tone, length, audience, attribution, separation of opinion from reported fact, and a prohibition on invented numbers, quotes, people, or events.
- Request **Structured Outputs** with a strict JSON schema, for example: `hook`, `summary`, `insights`, `call_to_action`, `hashtags`, `source_attribution`, `claims[]`, and `warnings[]`. Each factual claim must reference one or more fact IDs.
- Validate the returned schema, permitted fact IDs, source URL, length band, hashtag limits, and required attribution. Reject or retry safely on invalid output; do not silently publish it.
- Render the validated structure into editable post text and retain the internal claim map for quality review.
- Use an idempotency key and input hash to prevent accidental duplicate calls. Add timeouts, bounded exponential backoff for retryable failures, rate limiting, and user-visible error states.
- Log OpenAI request IDs and internal trace IDs, but redact source text, post content, credentials, and personal data from standard logs.

Official references: [API overview](https://developers.openai.com/api/reference/overview), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), and [production best practices](https://developers.openai.com/api/docs/guides/production-best-practices).

### Image generation

- Build an image prompt from the validated fact pack and final post, then add a policy layer: professional editorial illustration, no CNN marks, no imitation of source photography, and no unverified visual claims.
- Classify sensitive stories. For disasters, conflict, crime, health, elections, and identifiable real people, default to a clearly labelled conceptual illustration instead of a photorealistic depiction of an event.
- Call OpenAI image generation from the backend. Keep the image model configurable, validate MIME type and dimensions, and store the returned file in object storage rather than the database.
- Save the user instruction, composed prompt, model, creation time, source lineage, and `ai_generated=true` flag.
- Permit independent regeneration. Each request creates a new immutable image record; old assets remain linked until explicitly deleted by the user or retention policy.

Official reference: [OpenAI image generation](https://developers.openai.com/api/docs/guides/tools-image-generation).

### Evaluation and cost controls

- Build a small, rights-safe evaluation set spanning Technology, Business, World, Science, thin sources, sensitive news, and adversarial source text.
- Score factual support, source attribution, tone, length, audience fit, originality, and safe image-prompt behaviour.
- Pin prompt and model versions for each evaluation run and compare results before promotion.
- Capture usage and latency metadata, configure spend alerts, cap retries, limit generation frequency, and avoid duplicate calls through caching/idempotency.

## 7. Epics and Tasks

The IDs below are stable planning IDs and should be copied into Jira labels or an `External ID` field.

### Epic E0 - Product discovery, rights, and governance

**Goal:** remove ambiguity, confirm the legal data path, and establish go/no-go criteria before live ingestion.

**Exit criteria:** the brief is baselined; CNN access and permitted fields are documented; unresolved access blocks live-source release.

- [ ] **T0.1 - Baseline requirements and acceptance criteria.** Turn the brief into a signed-off scope, glossary, primary user journey, non-functional requirements, and explicit exclusions.
- [ ] **T0.2 - Investigate CNN access options.** Review current CNN terms, licensing/contact routes, any authorised feeds or licensed services, rate constraints, permitted fields, caching, retention, attribution, and display rules.
- [ ] **T0.3 - Obtain and record authorisation.** Save written evidence of the selected access route and name the owner responsible for compliance review. No credential or confidential contract term belongs in Git.
- [ ] **T0.4 - Define the source data contract.** Specify each permitted field, provenance, refresh interval, retention rule, canonical URL rule, and behaviour when full text is not permitted.
- [ ] **T0.5 - Complete privacy, copyright, and AI safety review.** Define user-data handling, deletion, generated-image labelling, sensitive-news treatment, and prohibited outputs.
- [ ] **T0.6 - Record go/no-go ADR.** Approve the live adapter, continue with fixtures while approval is pending, or stop/re-scope if no compliant path exists.
- [ ] **T0.7 - Create the initial risk register.** Assign owners, triggers, mitigations, and review dates to the risks in Section 10.

### Epic E1 — Engineering foundation and developer experience

**Goal:** create a reproducible, secure project skeleton.

**Exit criteria:** a new developer can start web, API, database, and storage dependencies locally and run quality checks.

- [ ] **T1.1 — Initialise the repository structure.** Create `apps/web`, `apps/api`, shared contracts, infrastructure, docs, and test locations with supported runtime versions.
- [ ] **T1.2 — Document architecture decisions.** Record monorepo, REST, authentication, database, worker, storage, CNN adapter, and OpenAI integration decisions.
- [ ] **T1.3 — Establish configuration and secret handling.** Add typed settings, `.env.example`, ignored local environment files, startup validation, and secret-manager guidance.
- [ ] **T1.4 — Add local containers.** Provide Dockerfiles and Compose services for web, API, PostgreSQL, object-storage emulator, and any required worker.
- [ ] **T1.5 — Add code quality tooling.** Configure formatting, linting, type checking, pre-commit hooks, and consistent task commands.
- [ ] **T1.6 — Add continuous integration.** Run lint, types, unit tests, migration checks, build checks, and secret/dependency scanning on pull requests.
- [ ] **T1.7 — Create test fixtures and provider fakes.** Use synthetic news records and fake AI responses so normal development never requires live content or paid API calls.
- [ ] **T1.8 — Add health and readiness endpoints.** Report application health without exposing credentials or sensitive configuration.

### Epic E2 — Data model, authentication, and authorisation

**Goal:** provide secure user access and durable domain storage.

**Exit criteria:** users can authenticate; ownership boundaries are enforced; migrations recreate the database.

- [ ] **T2.1 — Design the database schema.** Model users, sessions, articles, source snapshots, posts, versions, images, and generation runs with timestamps and constraints.
- [ ] **T2.2 — Implement migrations and seed data.** Create reversible migrations and synthetic development seeds; test migration from an empty database.
- [ ] **T2.3 — Implement registration.** Validate email/password, hash passwords with an approved adaptive algorithm, handle duplicate accounts, and avoid account enumeration.
- [ ] **T2.4 — Implement login, logout, and session lifecycle.** Use secure, `HttpOnly`, appropriately scoped cookies, expiry, rotation, and invalidation.
- [ ] **T2.5 — Add frontend auth flows.** Build accessible registration/login forms, validation, error states, protected navigation, and logout.
- [ ] **T2.6 — Enforce object-level authorisation.** Every saved post, generation, image, edit, and delete query must be scoped to the authenticated user.
- [ ] **T2.7 — Add account and session tests.** Cover success, invalid credentials, expired/revoked sessions, duplicate registration, CSRF protection, and cross-user access denial.

### Epic E3 — Authorised CNN discovery and article catalogue

**Goal:** retrieve, normalise, deduplicate, and present only the CNN information permitted by Epic E0.

**Dependency:** E0 access gate.

**Exit criteria:** the catalogue syncs through the authorised adapter, rejects duplicates, retains provenance, and exposes article endpoints.

- [ ] **T3.1 — Define a source-provider interface.** Isolate listing, detail retrieval, cursors, errors, and rate metadata from the rest of the application.
- [ ] **T3.2 — Implement the authorised CNN adapter.** Use only the approved feed/API/licensed mechanism and its documented credentials, limits, and terms.
- [ ] **T3.3 — Normalise and sanitise permitted fields.** Convert dates/time zones, categories, URLs, and text encoding; strip unsafe markup without expanding retained content beyond the licence.
- [ ] **T3.4 — Implement identity and deduplication.** Prefer provider ID plus canonical URL; add a content fingerprint only where permitted; enforce database uniqueness.
- [ ] **T3.5 — Persist provenance and rights metadata.** Record source name, provider ID, retrieval time, licence/access method ID, permitted-use flags, and source URL.
- [ ] **T3.6 — Build scheduled and manual synchronisation.** Use cursors, bounded retries, backoff, rate awareness, last-success state, and overlap protection.
- [ ] **T3.7 — Build article REST endpoints.** Add paginated list, allowed category filter, sort, detail, source availability, and safe empty/error responses.
- [ ] **T3.8 — Add ingestion observability.** Track sync duration, item counts, duplicates, rejections, last successful run, and provider failure class without logging restricted text.
- [ ] **T3.9 — Test the catalogue pipeline.** Cover mapping, malformed records, changed records, duplicates, time zones, unavailable details, provider limits, and licence-field enforcement.

### Epic E4 — Grounded LinkedIn post generation

**Goal:** produce editable, original LinkedIn drafts whose factual statements are traceable to the selected source.

**Dependencies:** E2 and E3 data contracts.

**Exit criteria:** all supported combinations generate schema-valid drafts or a clear insufficiency/error response, with lineage and evaluation evidence.

- [ ] **T4.1 — Integrate the OpenAI SDK server-side.** Add typed configuration, connection timeouts, error mapping, request IDs, a fake client, and environment-specific project/model settings.
- [ ] **T4.2 — Build the fact-pack service.** Create numbered facts only from permitted source fields and store an immutable source snapshot for each generation.
- [ ] **T4.3 — Implement the sufficiency gate.** Define minimum evidence rules and return `INSUFFICIENT_SOURCE` before generation when the source cannot support a useful post.
- [ ] **T4.4 — Design and version prompt templates.** Cover five tones, three length bands, four audiences, attribution, opinion labelling, originality, and injection resistance.
- [ ] **T4.5 — Define the Structured Output schema.** Require post components, attribution, warnings, and a claim-to-fact-ID map; reject unknown fields and invalid enums.
- [ ] **T4.6 — Implement the generation endpoint.** Validate article access and controls, call the Responses API, persist the run, and return the editable draft and status.
- [ ] **T4.7 — Validate and render responses.** Check schema, fact IDs, source URL, required components, approximate length, hashtag limits, and prohibited unsupported claims before rendering.
- [ ] **T4.8 — Add idempotency, caching, and concurrency controls.** Prevent duplicate submissions, cap simultaneous requests per user, and avoid unnecessary repeat calls.
- [ ] **T4.9 — Implement text regeneration.** Preserve source lineage, create a new post version, apply new controls, and never overwrite the previously saved version.
- [ ] **T4.10 — Build the grounding evaluation suite.** Include ordinary, thin, conflicting, sensitive, and prompt-injection fixtures with expected pass/refuse outcomes.
- [ ] **T4.11 — Add usage and reliability telemetry.** Capture model/template version, latency, usage, retry count, outcome, and provider request ID with content redaction.

### Epic E5 — Safe AI image generation and storage

**Goal:** create downloadable original illustrations that support the post without copying or misleading.

**Dependency:** E4 validated fact pack.

**Exit criteria:** a user can generate/regenerate an image, see appropriate disclosure, and download a validated stored asset.

- [ ] **T5.1 — Build the image-prompt composer.** Derive subject, composition, style, colour, and aspect requirements from validated facts and user instructions.
- [ ] **T5.2 — Add sensitive-news rules.** Detect configured sensitive categories, disallow deceptive documentary framing, avoid unverified likenesses, and select conceptual illustration language.
- [ ] **T5.3 — Integrate OpenAI image generation.** Call it from the backend with configurable model/quality/size, timeout, error mapping, request tracing, and fake responses for tests.
- [ ] **T5.4 — Validate and store output.** Verify size, MIME type, byte limit, and decoding; use unpredictable object keys, correct content headers, and private-by-default storage.
- [ ] **T5.5 — Implement image regeneration.** Accept bounded additional instructions, create a new immutable image record, and retain lineage to the article and post version.
- [ ] **T5.6 — Implement secure image delivery.** Authorise ownership, use a short-lived signed URL or streamed download, supply a safe filename, and label the asset as AI-generated in the UI.
- [ ] **T5.7 — Add image tests.** Cover prompt constraints, sensitive stories, invalid/oversized provider output, storage failure, ownership, regeneration, and download.

### Epic E6 — News dashboard, generator, editor, and preview

**Goal:** deliver an accessible end-to-end user interface.

**Dependencies:** E2–E5 APIs or their fakes.

**Exit criteria:** the complete create/review flow works responsively with loading, empty, success, and error states.

- [ ] **T6.1 — Establish the design shell.** Build navigation, page layout, typography, responsive breakpoints, notifications, error boundary, and protected dashboard shell.
- [ ] **T6.2 — Build the article dashboard.** Display headline, category, date, description when permitted, CNN link, pagination, empty states, and Generate action.
- [ ] **T6.3 — Add category filter and browsing state.** Keep filters and page state shareable where appropriate and accessible by keyboard/screen reader.
- [ ] **T6.4 — Build article selection and source panel.** Show permitted details, attribution, source link, availability status, and generation eligibility.
- [ ] **T6.5 — Build generation controls.** Provide typed options for tone, length, and audience with sensible defaults, help text, and validation.
- [ ] **T6.6 — Build asynchronous generation states.** Prevent duplicate submission and communicate queued/loading, timeout, rate limit, insufficiency, provider failure, and retry states.
- [ ] **T6.7 — Build the content editor.** Support manual text edits, unsaved-change warnings, regeneration, and source link without losing prior saved versions.
- [ ] **T6.8 — Build the LinkedIn-style preview.** Present the post and image together while clearly stating that it is a preview, not LinkedIn publishing.
- [ ] **T6.9 — Add image controls.** Generate, regenerate with extra instructions, show disclosure/status, handle failures independently, and download.
- [ ] **T6.10 — Complete responsive and accessibility review.** Test keyboard order, labels, focus, contrast, announcements, error association, mobile layout, and reduced motion.

### Epic E7 — Content library and export

**Goal:** let users manage their generated work safely.

**Dependencies:** E2, E4, and E5.

**Exit criteria:** a user can list, open, edit, version, regenerate, copy, download, and delete only their own content.

- [ ] **T7.1 — Implement save and update semantics.** Separate draft edits from immutable AI generation records and use optimistic concurrency to prevent lost updates.
- [ ] **T7.2 — Build content-library endpoints.** Add user-scoped pagination, filters, summaries, detail, update, and delete behaviour.
- [ ] **T7.3 — Build content history UI.** Show saved items, associated image, source article, updated time, status, and empty/loading/error states.
- [ ] **T7.4 — Add edit and regeneration history.** Keep clear version lineage and allow the current version to be selected without deleting past audit records unexpectedly.
- [ ] **T7.5 — Implement copy and download.** Use the Clipboard API with fallback/status feedback and authorised image download with safe filenames.
- [ ] **T7.6 — Implement deletion and retention.** Confirm destructive actions, soft-delete immediately where useful, remove storage objects according to policy, and document recoverability.
- [ ] **T7.7 — Test ownership and lifecycle.** Cover cross-user denial, stale updates, deleted source/image cases, repeated regeneration, copy failure, and storage cleanup.

### Epic E8 — Security, quality, reliability, and user acceptance

**Goal:** demonstrate that the application is safe, correct, supportable, and ready for delivery.

**Dependencies:** all feature epics.

**Exit criteria:** all release gates in Section 9 pass and no release-blocking defect remains.

- [ ] **T8.1 — Threat-model the system.** Review authentication, broken object-level authorisation, CSRF, XSS, injection, prompt injection, SSRF, unsafe files, secret leakage, abuse, and dependency risk.
- [ ] **T8.2 — Apply API security controls.** Enforce schemas and length limits, safe URL handling, CORS/CSRF policy, security headers, rate limits, safe errors, and least privilege.
- [ ] **T8.3 — Review data protection.** Confirm log redaction, retention, account/content deletion, storage access, backups, and handling of personal data.
- [ ] **T8.4 — Complete automated test layers.** Run unit, component, integration, contract, migration, end-to-end, accessibility, and provider-failure tests.
- [ ] **T8.5 — Test external-service resilience.** Exercise timeouts, 429s, transient 5xx errors, invalid responses, duplicate callbacks/submissions, database outages, and storage failures.
- [ ] **T8.6 — Measure critical-path performance.** Establish a baseline for catalogue browsing, post generation, image generation, and history; fix user-blocking regressions.
- [ ] **T8.7 — Run grounding and image-safety evaluation.** Record prompt/model versions, test set, scores, failures, reviewer, and release decision.
- [ ] **T8.8 — Conduct user acceptance testing.** Run the scenarios in Section 11, capture evidence, triage defects, and obtain sign-off.
- [ ] **T8.9 — Complete regression and release-candidate review.** Re-run the full gate after fixes and freeze the evaluated configuration for delivery.

### Epic E9 — Packaging, documentation, demonstration, and closure

**Goal:** make the system reproducible, understandable, and handover-ready.

**Dependency:** E8 release candidate.

**Exit criteria:** a reviewer can set up, run, test, understand, demonstrate, and recover the application using the delivered material.

- [ ] **T9.1 — Finalise Docker delivery.** Build deterministic images, run as non-root where practical, add health checks, and validate a clean-machine Compose setup.
- [ ] **T9.2 — Prepare environment and deployment runbook.** Document required services, secret setup, migrations, TLS/proxy assumptions, storage, backup, restore, monitoring, and rollback.
- [ ] **T9.3 — Finalise CI/CD release gates.** Require tests, builds, scans, migration validation, environment approval, and tagged/versioned artifacts.
- [ ] **T9.4 — Complete the README.** Add prerequisites, installation, configuration, local run, test, troubleshooting, architecture, limitations, and licensing instructions.
- [ ] **T9.5 — Publish API and schema documentation.** Ensure OpenAPI reflects real endpoints and provide data-model and error-code notes.
- [ ] **T9.6 — Write the technical report.** Explain architecture, authorised source method, AI grounding, image safety, key decisions, testing, limitations, and future work.
- [ ] **T9.7 — Prepare and rehearse the demonstration.** Cover sign-in, article discovery, generation choices, grounded post, image, edit, save, history, export, and one handled failure.
- [ ] **T9.8 — Release and verify.** Apply migrations, run smoke tests, verify monitoring/backups, record the release version, and keep rollback ready.
- [ ] **T9.9 — Close the project.** Archive evidence, capture known issues and lessons learned, transfer ownership, and convert deferred work into a prioritised backlog.

## 8. Six-week delivery roadmap

Tasks may move as evidence changes; dependencies and quality gates take precedence over dates. The table is a target sequence for a small team, not an instruction to overload a solo sprint. Confirm actual capacity in Jira, measure the first sprint's velocity, and reforecast the remaining work from evidence.

| Period | Primary outcomes | Planned Epic focus | Gate |
|---|---|---|---|
| Week 1 | Requirements baseline, rights investigation, architecture, repository and local stack | E0, E1 | G1 CNN access decision documented or explicitly pending with live release blocked |
| Week 2 | Authentication, schema, source adapter contract, catalogue/API foundation | E2, E3 | G2 secure sign-in and fixture-backed article catalogue demonstrated |
| Week 3 | Authorised sync where approved, dashboard, fact pack, text-generation vertical slice | E3, E4, E6 | G3 one grounded text-generation path passes schema and lineage checks |
| Week 4 | Image generation, editor, preview, regeneration, storage | E5, E6 | G4 full create/review flow demonstrated with provider failure handling |
| Week 5 | Content library, export, security hardening, automated tests and evaluation | E7, E8 | G5 feature complete; release blockers and evaluation failures visible |
| Week 6 | UAT, regression, packaging, documentation, report, demo, release/closure | E8, E9 | G6 acceptance criteria signed off and delivery package reproducible |

If the authorised CNN path is not available by G1, continue UI and AI work only with synthetic fixtures. Escalate the project decision; do not quietly substitute scraping or another news source.

## 9. Release gates and Definition of Done

### Task Definition of Done

A Task is Done only when:

- Its acceptance criteria are demonstrably met.
- Code and configuration are reviewed and merged through the agreed branch process.
- Relevant tests are added and passing locally and in CI.
- Security, privacy, rights, and accessibility implications are addressed.
- User-visible errors and operational logs are useful and do not expose secrets or restricted content.
- Documentation/OpenAPI/ADR is updated where behaviour or a decision changed.
- No unresolved release-blocking defect is hidden inside the task.

### Release checklist

- [ ] Written evidence confirms the live CNN access path and permitted use.
- [ ] The entire brief is traceable to delivered Tasks or explicitly accepted exclusions.
- [ ] Critical-path end-to-end tests pass in the release environment.
- [ ] Grounding and sensitive-image evaluations meet the agreed threshold.
- [ ] No open critical/high security issue or cross-user data exposure exists.
- [ ] OpenAI keys are backend-only, rotated as needed, and excluded from source/logs/client bundles.
- [ ] Rate limits, spend alerts, timeouts, retries, and external-provider error states are configured.
- [ ] Database migration, backup/restore, object retention, and rollback are tested.
- [ ] README, API docs, technical report, limitations, and demonstration are complete.
- [ ] Product owner/UAT reviewer signs off the release candidate.

## 10. Risk register

| ID | Risk | Likelihood / impact | Mitigation and response | Owner |
|---|---|---|---|---|
| R1 | No suitable CNN licence/feed is available in time | High / Critical | Make E0 the first gate; contact CNN; keep a provider interface; develop with synthetic fixtures; block live release or formally re-scope | Product owner |
| R2 | Permitted fields are too thin for grounded posts | Medium / High | Define sufficiency thresholds; refuse generation; request licensed detail access; never fill gaps from model memory | Product + AI owner |
| R3 | Model creates unsupported factual claims | Medium / Critical | Numbered fact pack, strict schema, claim mapping, validation, evals, human review, and version pinning | AI owner |
| R4 | Generated image misrepresents sensitive news | Medium / High | Sensitive-topic rules, conceptual illustration defaults, disclosure, tests, user review, and regeneration controls | AI/Product owner |
| R5 | Copyrighted CNN text/image is retained or reproduced | Medium / Critical | Field allowlist, retention controls, originality prompts/evals, no CNN image input, rights audit | Product owner |
| R6 | API usage cost grows unexpectedly | Medium / Medium | Spend alerts/limits, quotas, caching, idempotency, capped retries, usage telemetry, configurable models | Technical owner |
| R7 | OpenAI/CNN/storage outage breaks the workflow | Medium / High | Timeouts, bounded retry/backoff, circuit/queue behaviour where useful, clear status, fakes and resilience tests | Technical owner |
| R8 | User data or credentials leak | Low / Critical | Backend-only secrets, secure sessions, least privilege, log redaction, scans, dependency updates, security review | Technical owner |
| R9 | Six-week scope is too large for capacity | High / High | Protect the Must-have path, measure weekly, limit WIP, remove polish before core controls, never cut rights/security/grounding | Project owner |
| R10 | External API/model behaviour changes | Medium / Medium | Pin evaluated versions, isolate adapters, contract tests, change through configuration and regression evaluation | Technical owner |

## 11. User acceptance scenarios

1. A new user registers, logs in, refreshes the browser, logs out, and cannot access the protected dashboard afterward.
2. The dashboard shows recent authorised CNN items with correct metadata, filters by category, links to CNN, and contains no duplicate canonical URL.
3. The user selects an eligible article, chooses every supported control type, and receives a structured, editable draft with attribution.
4. A reviewer can map each factual claim in a sampled draft to the stored source fact IDs.
5. A thin or incomplete article returns an insufficiency message and does not invent a post.
6. The user generates an original image, adds bounded instructions, regenerates it independently, sees an AI-generated disclosure, and downloads it.
7. A sensitive-news fixture produces conceptual, non-deceptive image treatment without copied branding or source photography.
8. The user edits and saves a post, returns later, sees the latest content and image, and can access the original CNN URL.
9. User A cannot read, edit, download, regenerate, or delete any object owned by User B.
10. The user copies post text and downloads the image; a blocked Clipboard API or failed download produces clear recovery guidance.
11. CNN/OpenAI/storage timeout and rate-limit cases show useful errors, do not duplicate work, and remain traceable in redacted logs.
12. A clean environment follows the README and runs the complete demo workflow with the approved source configuration or documented test fixtures.

## 12. Dependencies and assumptions

- CNN authorisation, credentials, permitted fields, and retention rules are external dependencies and are not presumed.
- The project owner will provide or approve OpenAI account/project access, budgets, and models available to that project.
- Generated LinkedIn content is manually reviewed and published; the application does not authenticate with LinkedIn.
- A local S3-compatible adapter is acceptable for development; the delivery environment determines the production storage provider.
- One product owner/UAT reviewer is available at each weekly gate.
- Any material change to source, platform, scope, or schedule is recorded in Jira and, if architectural, in an ADR.

## 13. Reference links

- [CNN International Commercial terms](https://commercial.cnn.com/terms-of-use/)
- [CNN International Commercial licensing contact](https://commercial.cnn.com/contact-us/)
- [OpenAI API overview](https://developers.openai.com/api/reference/overview)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [OpenAI image generation](https://developers.openai.com/api/docs/guides/tools-image-generation)
- [OpenAI production best practices](https://developers.openai.com/api/docs/guides/production-best-practices)
- [Atlassian Jira work type hierarchy](https://support.atlassian.com/jira-cloud-administration/docs/what-are-issue-types)
