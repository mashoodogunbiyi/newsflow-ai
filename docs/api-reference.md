# NewsFlow AI API reference

## 1. Interactive documentation

FastAPI generates the API contract from the running application.

| Interface | Local URL | Purpose |
| --- | --- | --- |
| Swagger UI | [http://localhost:8000/docs](http://localhost:8000/docs) | Browse and exercise the OpenAPI operations |
| ReDoc | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Read a structured API reference |
| OpenAPI JSON | [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) | Machine-readable contract |
| Health | [http://localhost:8000/health](http://localhost:8000/health) | Process liveness |
| Readiness | [http://localhost:8000/ready](http://localhost:8000/ready) | Configuration and PostgreSQL readiness |

These addresses work only while the local backend is running. They are not public deployment URLs.

Start the complete local application from the repository root:

```bash
docker compose up --build --detach --wait
```

## 2. API boundaries

The browser normally calls same-origin Next.js route handlers. Those gateways forward selected cookies and headers to FastAPI. FastAPI remains authoritative for authentication, CSRF, source rights, object ownership, validation, limits and persistence.

OpenAI credentials, database credentials and private image-storage keys are never part of the public API contract.

## 3. Authentication model

- Registration and login accept JSON over the authentication endpoints.
- Passwords are stored only as Argon2id hashes.
- Login creates a random server-managed session.
- The browser receives the raw session value in an HTTP-only cookie.
- PostgreSQL stores only a SHA-256 session-token hash.
- Protected reads require the active session cookie.
- State-changing operations also require the matching `X-CSRF-Token` header.
- Login, registration and generation operations have bounded rate and usage controls.
- Private resources always use the authenticated account as their ownership scope.

## 4. Main endpoint groups

This table is an onboarding summary. The generated OpenAPI document is the authoritative list of current methods, schemas and responses.

| Group | Representative FastAPI routes | Access |
| --- | --- | --- |
| System | `GET /health`, `GET /ready` | Public, safe status only |
| Accounts | `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout` | Public registration and login; session required for account state and logout |
| Article catalogue | `GET /api/articles`, `GET /api/articles/{article_id}` | Authenticated; returns display-permitted metadata only |
| Article synchronisation | `POST /api/v1/admin/articles/sync`, `GET /api/v1/admin/articles/sync/{job_id}` | Administrator; mutations require CSRF |
| Text generation | `POST /api/generations` | Authenticated session, CSRF, rights, limits and idempotency controls |
| Generated images | `POST /api/images`, `POST /api/images/{image_id}/regenerate` | Authenticated session, CSRF, rights, safety and ownership controls |
| Image delivery | `GET /api/images/{image_id}`, `GET /api/images/{image_id}/content`, `GET /api/images/{image_id}/download` | Authenticated owner only |
| Saved drafts | `POST /api/v1/drafts`, `GET /api/v1/drafts`, `GET /api/v1/drafts/{draft_id}`, `PATCH /api/v1/drafts/{draft_id}`, `DELETE /api/v1/drafts/{draft_id}` | Authenticated owner; mutations require CSRF |
| Draft history | `GET /api/v1/drafts/{draft_id}/versions`, `POST /api/v1/drafts/{draft_id}/versions/{version_id}/restore` | Authenticated owner; restoration requires CSRF |
| Ingestion monitoring | `/api/admin/sync/*` | Authenticated administrator |
| Generation monitoring | `/api/admin/generations/*` | Authenticated administrator |

The backend also retains earlier service-specific routes used by existing internal tests and compatibility contracts. Consult `/docs` rather than guessing a path.

## 5. Request controls

### CSRF

Send the non-secret CSRF cookie value in `X-CSRF-Token` for a state-changing authenticated request. The HTTP-only session cookie is sent by the browser but is not readable by client-side JavaScript.

### Idempotency

Generation and creation operations that document duplicate protection accept an `Idempotency-Key` header. Reusing a key for the same completed request returns the existing result; reusing it for different content produces a conflict.

### Content type and size

JSON endpoints require the correct content type and bounded bodies. The backend and deployment edge must reject oversized input. Image responses are restricted to approved media types and private no-store delivery.

### Pagination

Article catalogue endpoints use bounded opaque-cursor pagination. Saved-draft lists use bounded page and page-size parameters. Clients must not alter opaque cursors or request unbounded collections.

## 6. Response and error behavior

Private responses use `Cache-Control: private, no-store` or `no-store` as appropriate. Provider and database details are not returned.

Application failures use a safe JSON structure:

```json
{
  "error": {
    "code": "stable_safe_code",
    "message": "A safe message suitable for the user."
  }
}
```

Common status meanings:

| Status | Meaning |
| ---: | --- |
| `400` | Request cannot be processed |
| `401` | Authentication missing or expired |
| `403` | CSRF, rights, safety or permission denied |
| `404` | Resource missing or not owned by the active user |
| `409` | Duplicate, idempotency or optimistic-version conflict |
| `422` | Schema, preference or permitted-source validation failed |
| `429` | Rate or usage limit exceeded |
| `502` | External provider returned an invalid or rejected result |
| `503` | Required application service is unavailable |
| `504` | External provider timed out |

## 7. Safe local checks

No credential is required for liveness and readiness checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Expected liveness response:

```json
{"status":"ok"}
```

Expected ready response:

```json
{"status":"ready","database":"connected","configuration":"valid"}
```

Use Swagger UI for schemas and controlled local requests. Do not paste a production credential into a development Swagger interface, screenshot or Jira comment.

## 8. Source locations

- Application and OpenAPI metadata: `apps/api/app/main.py`
- HTTP routes: `apps/api/app/api/routes`
- Authentication dependencies: `apps/api/app/api/dependencies.py`
- Request and response models: `apps/api/app/models`
- Application workflows: `apps/api/app/services`
- Same-origin browser gateways: `apps/web/app/api` and `apps/web/lib/*-proxy.ts`
- Detailed generation contract: [generation-api.md](generation-api.md)
- Article contract: [article-catalogue-api.md](article-catalogue-api.md)
- Saved-content contract: [content-library-api.md](content-library-api.md)
- Image contract: [image-delivery.md](image-delivery.md)

## 9. Limitations

- Live CNN access is not authorised and is not exposed through the API.
- The fixture provider returns synthetic development records only.
- OpenAI routes require approved server-side configuration; normal tests use mocks.
- Private image storage supports a local adapter for development and test only.
- No endpoint automatically publishes content to LinkedIn.
- Production hosting, transport, shared abuse controls, monitoring and recovery remain release gates.
