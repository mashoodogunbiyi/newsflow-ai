# NFA-75 - NewsFlow AI Security Threat Model

## 1. Document control

| Field | Value |
| --- | --- |
| Project | NewsFlow AI |
| Jira issue | NFA-75 |
| Version | 1.0 |
| Status | Ready for review |
| Assessment date | 3 November 2026 |
| Security owner | Mashood Ogunbiyi |
| Method | STRIDE supported by current OWASP web, API, logging, and supply-chain guidance |
| Scope | Browser, Next.js, FastAPI, authentication, PostgreSQL, article ingestion, OpenAI, private image storage, GitHub, and CI |
| Next mandatory review | Before production release and after any material architecture or provider change |

This model contains no real credentials, production network details, exploitable secret values, or confidential provider configuration.

## 2. Purpose and security objectives

This threat model identifies what NewsFlow AI must protect, where trust changes, how an attacker could misuse the system, which controls already exist, and which work remains before release.

The review explicitly covers authentication, session management, object-level authorisation, API and SQL injection, Cross Site Scripting, Cross-Site Request Forgery, Server-Side Request Forgery, provider credential exposure, prompt injection, private image access, unsafe file handling, sensitive logging, and software supply chain threats.

The primary objectives are:

- preserve the confidentiality of accounts, sessions, private drafts, histories, and generated images;
- preserve the integrity of article provenance, permissions, prompts, generated content, and deletion state;
- prevent one user or administrator from receiving privileges they do not own;
- keep credentials, database connection information, and provider secrets outside browser code, logs, and Git;
- keep the application available without uncontrolled provider usage or cost;
- treat article data, model output, file data, browser input, and third-party responses as untrusted;
- retain sufficient content-free evidence to investigate important actions without creating a second store of sensitive content; and
- block release when a critical threat lacks an implemented and verified mitigation.

## 3. Method and severity

STRIDE is applied to components, data flows, and trust boundaries:

| Category | Security property under threat | NewsFlow AI example |
| --- | --- | --- |
| Spoofing | Authenticity | Reusing a stolen session cookie |
| Tampering | Integrity | Changing an article rights decision or draft version |
| Repudiation | Accountability | Denying a deletion or generation operation when evidence is absent |
| Information disclosure | Confidentiality | Reading another user's draft or an API key |
| Denial of service | Availability | Exhausting generation quota or database connections |
| Elevation of privilege | Authorisation | A normal user calling an administrator endpoint |

Likelihood and impact use the 1 to 5 scales established in [NFA-9](jira/NFA-9.md). The initial score is likelihood multiplied by impact.

| Score | Severity | Required response |
| ---: | --- | --- |
| 1 to 4 | Low | Accept with monitoring or apply a proportionate control |
| 5 to 9 | Medium | Assign an owner and track the mitigation |
| 10 to 15 | High | Prioritise mitigation and verify it before the affected release |
| 16 to 25 | Critical | Block the affected release or feature until exposure is reduced |

Residual risk is the exposure remaining after the listed existing controls and required mitigation operate. No unresolved critical risk is accepted by this document.

## 4. Architecture and data flows

```text
Untrusted browser
  |
  | HTTPS, forms, cookies, UUIDs, preferences
  v
Next.js frontend and same-origin route handlers
  |
  | restricted cookies, CSRF header, validated JSON
  v
FastAPI authentication and application routes
  |                 |                    |
  | SQL parameters  | official SDK       | private object operations
  v                 v                    v
PostgreSQL       OpenAI API        Private image storage
  ^
  | normalised articles, provenance, rights, checkpoints
  |
Article provider adapter and ingestion service

GitHub repository and pull request
  |
  | pinned manifests, workflow definitions, synthetic CI credentials
  v
GitHub Actions quality pipeline
```

### 4.1 Main flows

| Flow | Data | Security decisions |
| --- | --- | --- |
| F-01 Registration and login | Email, password, password hash, session and CSRF tokens | Validate input, hash with Argon2id, issue server-managed expiring session, return generic login failure |
| F-02 Article ingestion | Provider records, source identity, permitted fields, rights and provenance | Provider adapter, normalisation, deduplication, sanitisation, rights state, atomic persistence |
| F-03 Text generation | Article UUID, preferences, permitted fact pack, prompt, response, usage | Authenticate, require CSRF, verify current rights, separate instructions from untrusted data, validate output, require review |
| F-04 Image generation | Article and draft references, safe preferences, prompt, image bytes | Verify ownership and rights, apply safety policy, validate bytes and dimensions, remove metadata, store privately |
| F-05 Saved-content lifecycle | Draft text, source reference, image reference, history and deletion state | Owner-scoped queries, optimistic concurrency, safe export, deletion, cleanup and retention |
| F-06 Operations and CI | Safe logs, audit events, source code, dependencies and test results | Redaction, least-privilege workflow permission, synthetic credentials, quality gates |

## 5. Sensitive assets

| Asset | Why it matters | Storage or transit location |
| --- | --- | --- |
| A-01 Account credentials | Password disclosure could enable account takeover | Password only in encrypted transit; Argon2id hash in PostgreSQL |
| A-02 Session and CSRF tokens | Session theft could impersonate a user | Browser cookies and hashed server-side session evidence |
| A-03 Private drafts and history | User-created confidential content | PostgreSQL and authenticated responses |
| A-04 Generated images | Private user-owned binary content | Private image storage and PostgreSQL metadata |
| A-05 Provider and database secrets | Disclosure could expose paid services or stored data | Ignored environment file now; approved secret manager required for production |
| A-06 Article provenance and rights | Tampering could permit unauthorised source use | Versioned PostgreSQL records |
| A-07 Prompts and model responses | May contain source context or private derived content | Backend memory, provider transit, and approved persistence only |
| A-08 Audit and deletion evidence | Needed for investigation and lifecycle proof | Content-minimised PostgreSQL records and structured logs |
| A-09 Source code and build workflow | Compromise could affect every user and secret available to CI | GitHub repository, dependencies, Actions runners and images |
| A-10 Availability and provider budget | Abuse can prevent legitimate use or cause unexpected cost | FastAPI, PostgreSQL, OpenAI allowance and deployment resources |

## 6. Trust boundaries

| ID | Boundary | Untrusted input or capability | Required control |
| --- | --- | --- | --- |
| TB-01 | Browser to Next.js | Form data, route parameters, cookies, rendered article and AI text | Validation, escaping, secure cookies, CSRF, no secret in browser code, security headers |
| TB-02 | Next.js to FastAPI | Forwarded cookies, headers, JSON and internal API address | Header and cookie allowlists, exact origin, authentication, CSRF, schema validation, TLS in deployment |
| TB-03 | FastAPI to PostgreSQL | Application queries and stored attacker-controlled text | Bound SQL parameters, least-privilege database role, constraints, migrations, encryption and backups |
| TB-04 | FastAPI to OpenAI | Provider credential, permitted source context, prompts and untrusted response | Backend-only SDK, bounded configuration, timeout, validation, safe logs, approved data use |
| TB-05 | FastAPI to private image storage | Binary files and storage keys | Private namespace, owner authorisation, safe key resolution, validation, integrity digest, no public URL |
| TB-06 | Article provider to ingestion | Untrusted external records, URLs, markup and instructions | Authorised adapter, contract validation, sanitisation, provenance, rights, fail-closed provider mode |
| TB-07 | GitHub and Actions to application assets | Pull-request code, dependencies, workflow actions and runner output | Review, least privilege, lockfiles, dependency scanning, trusted actions, no production secrets on untrusted code |

## 7. External services and dependencies

| Dependency | Security relevance | Current position |
| --- | --- | --- |
| OpenAI API and official Python SDK | Receives approved prompts and returns untrusted text or image data; uses a paid secret | Backend-only integration with mocked routine tests and bounded errors, retries and output validation |
| Future authorised article provider | Supplies untrusted source records and may impose rights and retention duties | Live CNN access remains blocked by ADR-001; fixture provider is the only approved development mode |
| PostgreSQL 16 | Stores accounts, rights, generations, content, history and audit metadata | Local Docker development and disposable CI databases; production hardening is not complete |
| Private image storage | Stores private image bytes referenced by user-owned records | Local private adapter for development; production object-store configuration is not complete |
| GitHub and GitHub Actions | Holds code and executes third-party actions and dependencies | Read-only workflow permission and synthetic database credentials; automated supply-chain scanning remains open |
| npm, PyPI and container registries | Deliver direct and transitive executable dependencies | Lockfile or bounded manifests exist; continuous vulnerability and provenance checking remains open |

## 8. Threat register

| ID | STRIDE | Area or boundary | Threat scenario | L | I | Severity | Existing controls | Required mitigation and responsible task | Verification | Residual risk | Status and owner |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| TM-01 | Spoofing | Authentication, TB-01 | Credential stuffing or password guessing creates an authenticated session | 3 | 5 | High | Argon2id, password rules, generic failures and per-client registration and login limits | Keep limits monitored; add edge abuse controls and consider MFA before a public multi-user release under SEC-03 | `test_authentication.py`, `test_registration.py`, `test_passwords.py`, `test_rate_limit.py` | Medium - distributed attempts can bypass process-local limits | Monitoring - Security Owner |
| TM-02 | Spoofing | Sessions, TB-01 and TB-02 | A stolen, fixed or replayed session impersonates a user | 4 | 5 | Critical | Random opaque token, hashed server record, HttpOnly cookie, SameSite Lax, production Secure flag, expiry, revocation and session-bound CSRF | Verify HTTPS, HSTS, cookie scope, session rotation and proxy behavior in the release environment under SEC-01 | `test_authentication.py`, `test_authentication_integration.py`, plus SEC-01 deployment test | High until production transport is verified - release blocker | Open - Security Owner |
| TM-03 | Elevation of privilege | Drafts, images and history, TB-02 | User B changes a UUID to read, modify, export or delete User A's object | 4 | 5 | Critical | Session-derived owner ID, owner-scoped queries, composite ownership constraints and indistinguishable private 404 responses | Preserve cross-user tests for every new private endpoint under NFA-25 and NFA-73 | `test_authorization.py`, `test_saved_drafts.py`, `test_image_delivery.py`, `test_saved_content_lifecycle_e2e.py` | Low - implementation regression remains possible | Mitigated and monitored - Security Owner |
| TM-04 | Tampering | Cookie-authenticated APIs, TB-01 and TB-02 | A hostile site causes a signed-in browser to perform a state-changing request | 3 | 4 | High | SameSite cookie, session-specific CSRF token hash, custom CSRF header and exact credentialed CORS origin | Keep every state-changing route on the shared CSRF dependency and add a regression test with each route under NFA-23 | `test_authentication.py`, `test_authorization.py`, `test_generation_api.py`, `test_generation_workflow_acceptance.py` | Low - future route omissions remain possible | Mitigated and monitored - Security Owner |
| TM-05 | Tampering | FastAPI and PostgreSQL, TB-02 and TB-03 | SQL, command or mass-assignment input changes unintended records or fields | 3 | 5 | High | Pydantic allowlists with extra fields forbidden, UUID and enum types, SQLAlchemy bound values, no shell construction from API input and database constraints | Continue negative-schema and repository tests; prohibit raw string-built SQL under SEC-06 review | `test_authorization.py`, `test_saved_drafts.py`, `test_article_normalisation.py`, `test_generation_api.py` | Low - raw SQL changes require review | Mitigated and monitored - Technical Owner |
| TM-06 | Information disclosure | Next.js rendering, TB-01 | Article text, draft text or model output executes script and steals session-related data | 3 | 5 | High | React text escaping, plain-text rendering, no generated use of `dangerouslySetInnerHTML`, HttpOnly session cookie and input bounds | Add and verify CSP, frame, MIME and referrer headers; retain malicious-markup UI tests under SEC-01 | `accessibility-audit.test.tsx`, `linkedin-editor.test.tsx`, `linkedin-preview.test.tsx`, plus SEC-01 header test | Medium - CSP is not yet a verified deployment control | Open - Frontend and Security Owner |
| TM-07 | Elevation of privilege | Outbound HTTP, TB-04 and TB-06 | An attacker-controlled or provider-returned URL causes server-side access to internal services | 4 | 5 | Critical | No user-supplied generic fetch endpoint, live article provider disabled, OpenAI image references require HTTPS without embedded credentials | Before URL retrieval, enforce provider hostname allowlist, public address resolution, redirect revalidation and response size limits under SEC-04 | `test_openai_image_service.py` unsafe-URL cases plus new SEC-04 DNS, redirect and private-address tests | Medium while URL retrieval remains unused; critical if enabled without SEC-04 | Open feature gate - Security Owner |
| TM-08 | Tampering | AI prompts, TB-04 and TB-06 | Malicious article instructions override policy, permissions or output constraints | 4 | 4 | Critical | Fixed permitted fields, trusted and untrusted prompt separation, source rights checks, strict response models, grounding checks and mandatory human review | Maintain adversarial evaluation cases for every prompt version under NFA-39, NFA-42 and NFA-49 | `test_prompt_builder.py`, `test_image_prompt.py`, `test_image_safety.py`, `evaluation/test_grounding_and_safety.py` | Medium - model behavior cannot be completely controlled | Mitigated and accepted for reviewed drafts - AI and Safety Owner |
| TM-09 | Information disclosure | Secrets, TB-02, TB-03 and TB-04 | API keys, database credentials or tokens enter Git, browser code, errors or logs | 4 | 5 | Critical | `.env` and key patterns ignored, example values only, `SecretStr`, backend-only keys, redaction and safe errors | Use a managed production secret store, rotation procedure and secret scanning under SEC-05 | `test_config.py`, `test_openai_service.py`, `test_ingestion_observability.py`, plus SEC-05 secret-scan gate | High until managed production secrets and scanning are verified - release blocker | Open - Security Owner |
| TM-10 | Information disclosure | Images, TB-05 | A user bypasses image ownership or a storage key escapes the private root | 4 | 5 | Critical | Owner-scoped metadata and bytes, safe 404, unpredictable internal keys, resolved-path containment, no public URL, digest and size checks | Preserve private-by-default production object-store policy and deny direct bucket access under SEC-06 | `test_image_delivery.py`, `test_image_storage.py`, `test_saved_content_lifecycle_e2e.py` | Medium until a production adapter is reviewed | Open for production; mitigated locally - Security Owner |
| TM-11 | Tampering | Image processing, TB-04 and TB-05 | Corrupt, oversized, mislabeled or metadata-bearing image causes parser abuse or unsafe persistence | 3 | 5 | High | Content signatures, MIME match, byte and pixel limits, Pillow verification, re-encoding, metadata removal, digest validation and cleanup compensation | Run image parsing in constrained deployment resources and patch Pillow promptly under SEC-02 and SEC-06 | `test_image_validation.py`, `test_image_storage.py`, `test_image_workflow_acceptance.py` | Medium - image parsers remain complex dependencies | Mitigated and monitored - Technical Owner |
| TM-12 | Information disclosure | Logging and monitoring | Logs expose passwords, tokens, prompts, article text, drafts or provider response bodies | 3 | 5 | High | Allowlisted structured fields, credential-pattern redaction, content-free audit models and generic public errors | Restrict production log access, retention and export; add log-injection and secret-canary review under SEC-06 | `test_generation_audit.py`, `test_ingestion_observability.py`, `test_openai_service.py`, `test_linkedin_generation_service.py` | Medium - infrastructure log sinks are not yet selected | Open for production - Security Owner |
| TM-13 | Tampering | Article provenance and rights, TB-03 and TB-06 | Forged or stale rights metadata permits unauthorised source display or AI processing | 3 | 5 | High | Provider profile, immutable snapshots, versioned rights, provenance, current-rights link, fail-closed decisions and ADR-001 No-Go | Require written authorisation evidence and provider-specific contract tests before live activation under NFA-5 and NFA-8 | `test_article_rights.py`, `test_article_catalogue_integration.py`, `test_catalogue_pipeline_e2e.py` | Low for fixtures; High for live CNN until authorisation changes | Active live-integration blocker - Product and Security Owner |
| TM-14 | Tampering | Draft and generation requests, TB-02 | Replays, duplicate clicks or stale updates overwrite content or spend twice | 3 | 4 | High | Idempotency keys, duplicate fingerprints, optimistic versions, transactions and concurrent usage reservations | Preserve atomic conflict tests for new workflows under NFA-43, NFA-67 and NFA-70 | `test_generation_usage.py`, `test_saved_drafts.py`, `test_draft_version_history.py`, `test_saved_draft_integration.py` | Low - distributed edge retries require monitoring | Mitigated and monitored - Technical Owner |
| TM-15 | Repudiation | Generation, administration and deletion | A user or administrator disputes a sensitive operation and evidence is incomplete or mutable | 3 | 4 | High | Timestamped session, generation, sync and deletion evidence with request IDs and safe statuses | Export protected audit records to an access-controlled append-resistant production sink under SEC-06 | `test_generation_audit.py`, `test_admin_generation_monitoring.py`, `test_content_deletion.py` | Medium - current database administrators can alter evidence | Open for production - Security Owner |
| TM-16 | Denial of service | Authentication and public APIs, TB-01 | Automated requests exhaust CPU, memory, connection pools or account endpoints | 4 | 4 | Critical | Bounded input, password and endpoint limits, timeouts, pagination limits and application rate limiters | Add reverse-proxy body limits, shared rate limiting, connection limits and alert thresholds under SEC-03 | `test_rate_limit.py`, `test_registration.py`, `test_authentication.py`, plus SEC-03 load and limit tests | High until shared edge controls are deployed - release blocker | Open - Technical Owner |
| TM-17 | Denial of service | OpenAI text and image generation, TB-04 | Repeated costly work exhausts quota, concurrency or budget | 4 | 5 | Critical | Per-user burst, daily and concurrent limits, duplicate protection, bounded tokens, byte limits, timeouts and retries | Add deployment-wide budget alerts, global emergency stop and provider-spend review under SEC-03 | `test_generation_usage.py`, `test_openai_service.py`, `test_openai_image_service.py`, `test_generation_workflow_acceptance.py` | Medium after alerts; High until deployment alerting exists | Open - Product and Technical Owner |
| TM-18 | Denial of service | PostgreSQL, provider and storage, TB-03 to TB-06 | Dependency outage or slow response blocks normal use or leaves partial state | 3 | 4 | High | Health checks, timeouts, transactions, safe retry records, leases, cleanup jobs and controlled 503 responses | Define production availability, backup, alert and recovery procedures under SEC-06 | `test_api.py`, `test_article_sync.py`, `test_image_regeneration.py`, `test_content_deletion.py` | Medium - external outage cannot be eliminated | Open for production - Technical Owner |
| TM-19 | Elevation of privilege | Administrator APIs | A normal user triggers article sync or reads operational generation data | 3 | 5 | High | Active session, database-backed administrator role, CSRF on state change, owner-neutral 403 and bounded query parameters | Require least-privilege admin assignment and review role changes under SEC-06 | `test_admin_article_sync.py`, `test_admin_generation_monitoring.py`, `test_admin_ingestion_observability.py` | Low - administrator account compromise remains possible | Mitigated and monitored - Security Owner |
| TM-20 | Tampering | Dependencies and registries, TB-07 | A vulnerable, typosquatted or compromised dependency executes in build or runtime | 4 | 5 | Critical | npm lockfile, bounded Python versions, reviewed direct dependencies, tests and reproducible install commands | Add Dependabot or equivalent SCA, lock or hash Python resolution, SBOM generation and patch SLA under SEC-02 | New SEC-02 dependency audit, lock reproducibility and SBOM checks | High until continuous scanning is enforced - release blocker | Open - Technical Owner |
| TM-21 | Elevation of privilege | GitHub Actions, TB-07 | Compromised action, workflow or pull request exfiltrates credentials or alters trusted output | 3 | 5 | High | Workflow `contents: read`, synthetic database password, no production key in normal CI and protected quality checks | Pin third-party actions by reviewed commit SHA, protect main, require review and keep production environments approval-gated under SEC-02 | Workflow policy test under SEC-02 plus pull-request branch protection review | Medium after controls; current action tags remain mutable | Open - Technical Owner |
| TM-22 | Information disclosure | PostgreSQL and backups, TB-03 | Database, snapshot or restored backup exposes private data or resurrects deleted content | 3 | 5 | High | Secret connection string, owner-scoped application access, retention worker, redaction and documented restore tombstone requirement | Use encrypted managed PostgreSQL, least-privilege role, network restriction, encrypted expiring backups and restore tests under SEC-06 | `test_migrations_integration.py`, `test_content_deletion.py`, plus SEC-06 backup and restore exercise | High until production data platform is configured - release blocker | Open - Security and Technical Owner |
| TM-23 | Tampering | Deletion and retention, TB-03 and TB-05 | Race, cleanup failure or shared image reference produces false deletion or unintended data loss | 3 | 4 | High | Transactional active-access removal, reference checks, retry jobs, row-lock leases, idempotent object delete and redaction gate | Monitor retry backlog and test production storage behavior under NFA-72 and SEC-06 | `test_content_deletion.py`, `test_saved_draft_integration.py`, `test_saved_content_lifecycle_e2e.py` | Medium - PostgreSQL and object storage cannot share one transaction | Mitigated with monitored residual - Technical Owner |
| TM-24 | Information disclosure | OpenAI data use, TB-04 | More article, personal or private draft content than authorised is sent to the provider | 3 | 5 | High | Permitted field allowlist, current rights check, source sufficiency, minimal prompt contract, no unnecessary user profile and backend-only provider call | Confirm production provider data terms and add data-flow privacy review before release under NFA-5 and SEC-06 | `test_prompt_builder.py`, `test_image_prompt.py`, `test_article_rights.py`, `test_generation_workflow_acceptance.py` | Medium - approved prompt content still leaves the application boundary | Open legal and privacy gate - Product and Security Owner |

## 9. Mitigation plan and responsible tasks

| Task | Priority | Required work | Owner | Release condition |
| --- | --- | --- | --- | --- |
| SEC-01 | Critical | Configure and test HTTPS, HSTS, CSP, frame protection, MIME protection, referrer policy, cookie scope and trusted proxy behavior | Technical and Security Owner | Required before any public deployment |
| SEC-02 | Critical | Add continuous dependency and container scanning, Python resolution locking or hashes, SBOM generation, reviewed action SHA pinning, patch SLA and protected-branch review | Technical Owner | Required before production release |
| SEC-03 | Critical | Add shared edge rate limits, body and connection limits, provider budget alerts, emergency generation stop and abuse monitoring | Technical and Product Owner | Required before public multi-user release |
| SEC-04 | Critical if URL retrieval is enabled | Allowlist provider hosts, reject local and private addresses after DNS resolution, revalidate redirects and bound downloads | Security Owner | Must pass before any server-side provider URL download |
| SEC-05 | Critical | Select a managed secret store, document least-privilege access and rotation, and add secret scanning | Security Owner | Required before production credentials exist |
| SEC-06 | High | Complete deployment review for database roles, network rules, encrypted backups, restore tombstones, object-store privacy, log access, audit export and incident procedures | Technical and Security Owner | Required before release approval |

These task identifiers are security follow-up records for planning. They do not imply the controls are complete. Jira issues should be created or linked before release planning begins.

## 10. Verification requirements

Significant threats require both an implementation control and evidence. The following suites form the current security regression baseline:

```bash
cd apps/api
.venv/bin/pytest \
  tests/test_security_threat_model.py \
  tests/test_authentication.py \
  tests/test_authorization.py \
  tests/test_prompt_builder.py \
  tests/test_image_validation.py \
  tests/test_image_delivery.py \
  tests/test_generation_audit.py \
  tests/test_content_deletion.py

cd ../web
npm test -- \
  __tests__/auth-interface.test.tsx \
  __tests__/auth-proxy.test.ts \
  __tests__/linkedin-editor.test.tsx \
  __tests__/image-download-proxy.test.ts
```

The complete backend and frontend quality suites remain mandatory. The SEC tasks require additional deployment tests that cannot be truthfully passed by local unit tests alone.

## 11. Residual risk and release decision

### 11.1 Accepted for continued development

- Model prompt injection cannot be eliminated completely. It is accepted only for synthetic or authorised source data, constrained prompts, automated checks, mandatory human review, and no automatic LinkedIn publication.
- PostgreSQL and object storage cannot be changed in one transaction. The retryable deletion and retention design is accepted with cleanup monitoring.
- External service outages cannot be eliminated. Bounded retries, safe failure and operational monitoring reduce the effect.

### 11.2 Not accepted for production release

- Production transport, security headers and proxy behavior have not been verified.
- Managed secrets, secret scanning and rotation have not been established.
- Shared edge abuse protection and provider budget alerts have not been deployed.
- Continuous dependency, container and workflow-action scanning has not been enforced.
- Production PostgreSQL, backups, restore deletion handling and private object storage have not been reviewed.
- Server-side provider URL retrieval must remain disabled until SSRF controls pass SEC-04.
- Live CNN access remains blocked until the NFA-8 No-Go decision is formally replaced with documented authorisation.

No unresolved critical threat is marked accepted. These items are release gates, not optional recommendations.

## 12. Review triggers and release checklist

Review this model:

- before any staging or production release;
- when an endpoint, trust boundary, administrator role or data category is added;
- when a new article, AI, storage, database, logging or deployment provider is introduced;
- when authentication or session behavior changes;
- when an incident, serious vulnerability or failed security test occurs; and
- at least once per release cycle while the application remains active.

Before release, the reviewer must confirm:

- all Critical and High threats have a named owner, mitigation and verification result;
- SEC-01 to SEC-06 are complete or an explicit accountable decision records why a non-critical residual risk is accepted;
- no critical risk is accepted without an explicit documented decision;
- cross-user, CSRF, prompt-injection, private-image, unsafe-file, safe-log and retention tests pass;
- dependency and secret scans have no unresolved release-blocking finding;
- live source access is still consistent with the authorisation decision; and
- this document reflects the deployed architecture rather than only the local environment.

## 13. Guidance references

- [OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html)
- [OWASP API1:2023 Broken Object Level Authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/)
- [OWASP Cross Site Scripting Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP Cross-Site Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Server-Side Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OWASP Software Supply Chain Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html)
- [OWASP CI/CD Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/CI_CD_Security_Cheat_Sheet.html)

## 14. Review status

- Jira issue: NFA-75
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
