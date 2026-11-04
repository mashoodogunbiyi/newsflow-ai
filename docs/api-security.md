# NFA-76 - API Security Hardening

## Outcome

NewsFlow AI's backend endpoints have been reviewed and strengthened against the threats recorded in the NFA-75 threat model. This baseline covers authentication, object-level authorisation, CSRF, request validation, abuse controls, external URLs, response headers, secret detection, dependency auditing, and safe errors.

Review date: 3 November 2026

## Security model

The browser communicates with FastAPI through an exact configured CORS origin. Authentication uses an opaque server-managed session identifier in an HTTP-only cookie. The readable CSRF cookie must match the `X-CSRF-Token` header on state-changing authenticated operations. The backend derives the user identity from the active session and never accepts an owner ID from browser input.

Public health, registration, and login endpoints are deliberately narrow. Every content, generation, image, source, and operational endpoint requires authentication. Private-resource services query by both resource ID and authenticated owner ID and return the same not-found result for absent and cross-user records. Administrator routes perform a separate database-backed role check.

## Endpoint inventory

The security inventory is tied to the generated OpenAPI contract by an automated test. Adding a new API operation requires adding it here and reviewing its access, CSRF, validation, and abuse controls.

| Endpoint | Access and controls |
|---|---|
| `GET /health` | Public liveness result with no configuration or dependency detail. |
| `GET /ready` | Public readiness result limited to generic PostgreSQL and configuration states; safe error on failure. |
| `POST /api/v1/auth/register` | Public; validated JSON, Argon2id password hashing, duplicate protection, and per-client rate limiting. |
| `POST /api/v1/auth/login` | Public; generic credential failure, server-side session creation, secure cookies, and per-client rate limiting. |
| `POST /api/v1/auth/logout` | Authenticated; CSRF proof required; current server-side session is revoked. |
| `GET /api/v1/auth/me` | Authenticated; returns a minimal current-user response without credentials or password hashes. |
| `GET /api/articles` | Authenticated; bounded query fields and rights-filtered catalogue results. |
| `GET /api/articles/{article_id}` | Authenticated; UUID path validation and current rights check; non-disclosable records return not found. |
| `POST /api/generations` | Authenticated and CSRF-protected; article rights, request key, per-window, daily, concurrent, and duplicate controls. |
| `POST /api/v1/linkedin-drafts` | Authenticated and CSRF-protected; rights-aware generation, idempotency, output validation, and owner-scoped persistence. |
| `GET /api/v1/linkedin-drafts/{draft_id}` | Authenticated; UUID validation and owner-scoped retrieval. |
| `POST /api/images` | Authenticated and CSRF-protected; rights and safety policy checks, rate and concurrency controls, idempotency, and private storage. |
| `POST /api/images/{image_id}/regenerate` | Authenticated and CSRF-protected; UUID and parent ownership checks, rate and duplicate controls, immutable version creation. |
| `GET /api/images/{image_id}` | Authenticated; owner-scoped metadata only; private storage keys are not returned. |
| `GET /api/images/{image_id}/content` | Authenticated; owner-scoped, integrity-checked private content delivery. |
| `GET /api/images/{image_id}/download` | Authenticated; owner-scoped, integrity-checked attachment delivery with a server-generated filename. |
| `POST /api/v1/library/items` | Authenticated and CSRF-protected; session-derived ownership and referenced-resource checks. |
| `GET /api/v1/library/items` | Authenticated; owner-scoped collection only. |
| `GET /api/v1/library/items/{item_id}` | Authenticated; UUID validation and owner-scoped retrieval. |
| `PATCH /api/v1/library/items/{item_id}` | Authenticated and CSRF-protected; strict partial input and owner-scoped update. |
| `DELETE /api/v1/library/items/{item_id}` | Authenticated and CSRF-protected; owner-scoped deletion. |
| `GET /api/v1/library/items/{item_id}/export` | Authenticated; owner-scoped text export with no automatic publishing. |
| `POST /api/v1/drafts` | Authenticated and CSRF-protected; strict input, idempotency, generation lineage, and owner-scoped creation. |
| `GET /api/v1/drafts` | Authenticated; bounded pagination and owner-scoped collection. |
| `GET /api/v1/drafts/{saved_draft_id}` | Authenticated; UUID validation and owner-scoped retrieval. |
| `PATCH /api/v1/drafts/{saved_draft_id}` | Authenticated and CSRF-protected; strict partial input and stale-write protection. |
| `PUT /api/v1/drafts/{saved_draft_id}` | Authenticated and CSRF-protected; strict replacement input and stale-write protection. |
| `DELETE /api/v1/drafts/{saved_draft_id}` | Authenticated and CSRF-protected; owner-scoped deletion and controlled retention workflow. |
| `GET /api/v1/drafts/{saved_draft_id}/versions` | Authenticated; owner-scoped history and bounded pagination. |
| `GET /api/v1/drafts/{saved_draft_id}/versions/{version_id}` | Authenticated; both UUIDs and ownership relationship validated. |
| `POST /api/v1/drafts/{saved_draft_id}/versions/{version_id}/restore` | Authenticated and CSRF-protected; owner check and restoration as a new immutable version. |
| `POST /api/v1/admin/articles/sync` | Authenticated administrator plus CSRF; database role check, rate limit, and single-active-job control. |
| `GET /api/v1/admin/articles/sync/{job_id}` | Authenticated administrator; UUID validation and safe job metadata. |
| `GET /api/admin/sync/jobs` | Authenticated administrator; bounded filters and safe operational records. |
| `GET /api/admin/sync/jobs/{job_id}` | Authenticated administrator; UUID validation and safe job metadata. |
| `GET /api/admin/sync/metrics` | Authenticated administrator; bounded aggregation window. |
| `GET /api/admin/sync/health` | Authenticated administrator; safe status indicators without credentials. |
| `GET /api/admin/generations/audit` | Authenticated administrator; bounded filters and content-free audit events. |
| `GET /api/admin/generations/metrics` | Authenticated administrator; bounded aggregation window and content-free metrics. |

FastAPI also exposes `/docs`, `/redoc`, and `/openapi.json` for local developer documentation. Production deployment may disable or separately restrict these routes according to the hosting policy.

## Request controls

- FastAPI and Pydantic validate path, query, header, and JSON body values using strict UUIDs, enumerations, lengths, numeric bounds, and forbidden extra fields where defined.
- `API_MAX_REQUEST_BODY_BYTES` defaults to 1,048,576 bytes and is bounded between 1 KiB and 10 MiB. The API rejects an oversized declared body and also counts streamed chunks so a missing or false `Content-Length` cannot bypass the limit.
- Non-empty `POST`, `PUT`, `PATCH`, and `DELETE` bodies must use `application/json` or a `+json` media type. Unsupported content types fail before business processing.
- Oversized and unsupported requests use the standard content-free JSON error envelope and do not echo input.
- Image provider bytes have separate stricter response, decoded-file, pixel, media-signature, and digest limits.

## Abuse and duplicate controls

- Registration and login are limited per client before body validation.
- Manual ingestion is limited per administrator and prevents concurrent active jobs.
- Text and image generation are limited per authenticated user and time window.
- PostgreSQL-backed daily and concurrent generation reservations work across application instances. Attempt leases recover abandoned work.
- Idempotency keys and request fingerprints return an existing result for matching retries and reject reuse with different inputs.
- Provider calls have bounded deadlines and retries. Safe `429`, quota, timeout, and unavailable categories do not reveal provider credentials or private prompt content.

The short-window in-memory rate limiter is process-local. A production deployment with multiple API instances must also use a shared gateway or distributed rate limiter. The PostgreSQL daily and concurrency limits remain the authoritative cost boundary.

## CORS, cookies, CSRF, and response headers

- Credentialed CORS requests are accepted only from the exact `FRONTEND_ORIGIN`. Methods and headers use an explicit allowlist; wildcard origins are not used.
- Session cookies are HTTP-only, `SameSite=Lax`, scoped to the application, and marked `Secure` in staging and production. Session records expire and logout revokes them server-side.
- State-changing authenticated routes require the matching CSRF header. CORS is not treated as the CSRF control.
- API responses use `Cache-Control: no-store`, `Content-Security-Policy: default-src 'none'`, `Cross-Origin-Resource-Policy: same-site`, `Permissions-Policy`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `X-Permitted-Cross-Domain-Policies: none`.
- HSTS is enabled in staging and production. It is deliberately absent in local HTTP development. The interactive documentation omits the API-only CSP so its scripts and styles remain usable, while the remaining headers still apply.

## External URLs and private files

News article URLs are validated HTTPS references and are not fetched by backend endpoints. Provider-returned image references now reject credentials, fragments, non-HTTPS schemes, non-standard ports, local names, reserved test names, loopback, private, link-local, multicast, and other non-global IP addresses.

No general URL downloader is exposed to users. The image storage workflow refuses a provider URL unless a future approved bounded downloader has supplied validated bytes. Such a downloader must add a provider-host allowlist, resolve and recheck every address, reject redirects outside the allowlist, cap time and bytes, and prevent DNS rebinding before production use.

Generated images are stored behind a private storage adapter. Delivery always authenticates the user, checks owner-scoped metadata, resolves a controlled storage key, verifies integrity, and sends content through the backend. Local filesystem storage is permitted only for development and tests.

## Secrets, dependencies, and safe failures

- `.env` and virtual environments are excluded from Git; `.env.example` contains placeholders only.
- `scripts/scan_secrets.py` scans every tracked text file for high-confidence OpenAI, GitHub, AWS, and private-key patterns and fails if a real `.env` file is tracked.
- CI runs the tracked-file secret scan, `pip-audit` for Python advisories, and `npm audit --omit=dev --audit-level=high` for production frontend dependencies.
- API exceptions use consistent safe codes and messages. Validation details identify fields and rules but never include passwords, session identifiers, API keys, prompts, article content, database URLs, or stack traces.
- Structured logs use allowlisted fields and redact credential-like values. Generation audit events intentionally exclude prompts and generated content.

Secret scanning is a guardrail, not proof that history is clean. GitHub secret scanning or another history-aware scanner should also be enabled in the hosted repository. Any exposed secret must be revoked immediately before history cleanup is considered.

## Automated verification

Run the focused NFA-76 checks:

```bash
cd apps/api
source .venv/bin/activate
pytest tests/test_api_security.py tests/test_openai_image_service.py tests/test_config.py
ruff check app/security/api.py app/security/urls.py tests/test_api_security.py
ruff format --check app/security/api.py app/security/urls.py tests/test_api_security.py
cd ../..
python scripts/scan_secrets.py
```

Run dependency checks with network access:

```bash
cd apps/api
pip-audit
cd ../web
npm audit --omit=dev --audit-level=high
```

The complete backend suite additionally covers unauthenticated access, cross-user access, CSRF, rate limiting, safe errors, private image delivery, duplicate requests, output validation, and joined PostgreSQL workflows.

### Verification record

Verified locally on 3 November 2026:

- The focused NFA-76 configuration, middleware, CORS, endpoint-inventory, provider-URL, and image-service run passed 61 tests.
- The complete backend run passed 462 tests, skipped 16 opt-in integration tests, deselected the optional live-model test, and measured 78.34 percent branch-aware coverage against the enforced 75 percent floor.
- Ruff linting and formatting passed across all 206 backend Python files.
- The project secret scan passed and Git confirmed that `.env` and `.venv` are ignored.
- The first Python advisory scan identified fixed advisories in Pillow 12.3.0 and certifi 2026.7.22. The runtime constraints were upgraded to Pillow 13.0.0 or newer and certifi 2026.10.18 or newer instead of suppressing the findings.
- The repeated `pip-audit` scan reported no known vulnerabilities. The local editable `newsflow-api` package was correctly listed as not published on PyPI and therefore not independently auditable.
- `npm audit --omit=dev --audit-level=high` reported zero known production dependency vulnerabilities.
- Tests and audits used synthetic inputs and local dependencies. No live CNN, OpenAI, production database, or production object-storage request was made.

## Threat-model traceability and residual risk

This work directly strengthens NFA-75 controls `SEC-01` (endpoint authorisation), `SEC-03` (request and provider validation), `SEC-04` (external URL and private delivery controls), and `SEC-05` (limits and duplicate protection). It adds verification around `T-01`, `T-02`, `T-04`, `T-05`, `T-09`, `T-11`, `T-15`, `T-18`, `T-20`, and `T-22`.

The following production responsibilities remain open release gates rather than hidden assumptions:

- Terminate trusted HTTPS before enabling real users and retain the production cookie and HSTS settings.
- Add a shared gateway or distributed short-window limiter for multi-instance deployments.
- Configure a production private object store, malware scanning where required, backup access controls, and restoration tests.
- Enable history-aware hosted secret scanning and repository branch protections.
- Keep dependency advisories reviewed and upgrade vulnerable packages without bypassing failed audits.
- Obtain explicit CNN authorisation before enabling any live CNN adapter.

## References

- [OWASP API1:2023 Broken Object Level Authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/)
- [OWASP Cross-Site Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Server-Side Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Software Supply Chain Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html)
- [pip-audit on PyPI](https://pypi.org/project/pip-audit/)
- [npm audit documentation](https://docs.npmjs.com/cli/v11/commands/npm-audit/)
