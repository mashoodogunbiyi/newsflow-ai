# NFA-34 - Article Catalogue REST API

## Purpose

NFA-34 gives the NewsFlow AI frontend a secure way to browse and retrieve authorised article metadata from PostgreSQL.

The frontend never connects directly to PostgreSQL. It sends an HTTP request to FastAPI, FastAPI applies authentication and rights rules, and the repository builds parameterised SQLAlchemy queries against the current stored article records.

No live CNN request is made by these endpoints. They work with the approved synthetic fixtures while ADR-001 continues to block live CNN access.

## Plain-language flow

```text
Logged-in user
    |
    v
FastAPI article route
    |
    v
Article catalogue service
    |
    v
Rights-aware SQLAlchemy repository
    |
    v
PostgreSQL
```

- The route validates the request and requires a valid session.
- The service controls public fields, cursor rules, and defence-in-depth visibility checks.
- The repository performs filtering, searching, sorting, and pagination in PostgreSQL.
- Pydantic validates the JSON response before FastAPI returns it.

## Authentication decision

Both endpoints require the server-managed session cookie created by login:

```text
GET /api/articles
GET /api/articles/{article_id}
```

An unauthenticated request receives HTTP 401. Article catalogue requests are read-only, so they do not require a CSRF token. The responses use `Cache-Control: private, no-store` so browsers and shared caches do not retain catalogue responses unexpectedly.

## List endpoint

```text
GET /api/articles
```

### Query parameters

| Parameter | Default | Rule |
|---|---:|---|
| `limit` | `20` | Integer from 1 to 100 |
| `cursor` | None | Opaque continuation cursor returned by the previous page |
| `search` | None | 1 to 200 characters; searches permitted title and description metadata |
| `provider` | None | Exact approved source-profile key, such as `fixture-v1` |
| `published_from` | None | Inclusive RFC 3339 timestamp with a timezone |
| `published_to` | None | Inclusive RFC 3339 timestamp with a timezone |
| `sort` | `newest` | `newest` or `oldest` |

`published_from` cannot be later than `published_to`. Unknown query parameters, invalid dates, unsupported sort values, blank filters, and out-of-range page sizes receive HTTP 422.

Example:

```text
GET /api/articles?limit=20&search=technology&provider=fixture-v1&sort=newest
```

Example synthetic response:

```json
{
  "items": [
    {
      "id": "10000000-0000-4000-8000-000000000003",
      "title": "Synthetic company announces an energy-efficient data platform",
      "description": "A fictional technology company announced a test platform.",
      "source_url": "https://example.invalid/newsflow-ai/fixture-technology-001",
      "provider": "fixture-v1",
      "published_at": "2026-10-12T09:00:00Z",
      "category": "Technology",
      "attribution": {
        "display_name": "NewsFlow AI synthetic fixture",
        "text": "Source: NewsFlow AI synthetic fixture - not live news",
        "byline": null,
        "copyright_notice": null
      }
    }
  ],
  "next_cursor": null
}
```

## Detail endpoint

```text
GET /api/articles/{article_id}
```

The identifier is the internal stable UUID created by the article identity system. A successful response uses the same public article schema as the list endpoint.

Missing, inactive, restricted, expired, unverified, and disabled-source records all receive the same HTTP 404 response. This prevents the API from revealing that a restricted record exists.

## Public fields and excluded fields

The API returns only the metadata required by the frontend:

- Stable article ID.
- Title and optional description.
- Canonical HTTPS source URL.
- Approved provider profile key.
- Publication timestamp and category.
- Required display name, attribution wording, byline, and copyright notice.

The API does not return:

- Provider credentials or confidential agreement details.
- Source-profile database IDs.
- Provider article identifiers.
- Rights decision references or internal rights versions.
- Snapshot IDs, fingerprints, or retrieval audit records.
- Stored permitted-content text.
- AI-processing or redistribution controls.

These exclusions keep the REST response separate from the internal database and rights models.

## Rights and availability rules

PostgreSQL and the service both fail closed. A record is visible only when:

- The article is active.
- Its source profile is enabled.
- Its current snapshot permits display.
- Its current rights version is verified and effective.
- Display permission is explicitly true.
- The rights verification time is present and not in the future.
- The retention period has not expired.
- Required attribution wording is present.

The database query applies these rules before pagination. The service checks them again before constructing the public response.

## Cursor pagination

The stable ordering is:

1. Publication timestamp.
2. Article UUID as a tie-breaker.

Newest order uses both values descending. Oldest order uses both ascending. This prevents articles with the same publication time from being omitted or repeated between pages.

The cursor is URL-safe, opaque to clients, versioned, and bound to the current search, filters, and sort selection. Changing those values while reusing a cursor returns HTTP 422. Clients should store and return the cursor unchanged rather than trying to edit it.

Migration `20261029_0005` adds a PostgreSQL index on publication time and article ID to support this ordering.

## Search and SQL safety

Search covers only the permitted current title and description. SQLAlchemy sends search text, provider values, dates, IDs, and cursor positions as bound parameters. SQL-like user input is treated as text rather than executable SQL.

The initial MVP uses PostgreSQL case-insensitive metadata matching. A separate search service is not required at this stage.

## Error responses

| Status | Meaning |
|---:|---|
| 200 | The request succeeded |
| 401 | A valid authenticated session is required |
| 404 | The article is missing or cannot be disclosed |
| 422 | A path, query parameter, date range, or cursor is invalid |
| 503 | PostgreSQL or safe catalogue processing is temporarily unavailable |

Database exceptions and unsafe stored data receive a generic 503 response. Credentials, SQL, internal table names, rights details, and provider errors are not returned to the client.

## OpenAPI documentation

With the backend running locally:

- Interactive documentation: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

The `Article catalogue` section documents authentication, parameters, response schemas, and expected error statuses.

## Apply the migration

With Docker Compose running from the repository root:

```bash
docker compose exec backend alembic upgrade head
```

Check the current revision:

```bash
docker compose exec backend alembic current
```

The expected head for NFA-34 is `20261029_0005`.

## Automated tests

Run the focused fast tests from `apps/api`:

```bash
pytest tests/test_article_catalogue.py
```

They cover list and detail responses, public field exclusion, authentication, restricted records, pagination, cursor binding, search input, query validation, safe database errors, and OpenAPI documentation.

The PostgreSQL integration test is destructive and accepts only a separate database whose name contains `newsflow_article_catalogue_test`:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_article_catalogue_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_article_catalogue_integration.py
```

Never point this command at the normal development database, a shared database, staging, or production.

## Verification completed

Verified on 29 October 2026:

- Backend formatting and linting passed.
- The normal backend suite passed 151 tests and safely skipped 8 opt-in integrations.
- The focused article catalogue suite passed 10 tests.
- The PostgreSQL catalogue integration passed against its disposable database.
- The full migration, seed, rollback, and rebuild test passed through revision `20261029_0005`.
- The disposable test databases were removed afterwards.

## Acceptance status

- Article list and detail REST endpoints - complete.
- Cursor pagination, search, provider and publication-date filtering, and sorting - complete.
- Authentication and rights-aware visibility - complete.
- Public response schemas and source attribution - complete.
- Safe SQLAlchemy queries and controlled errors - complete.
- FastAPI OpenAPI documentation - complete.
- Fast and PostgreSQL automated tests - complete.
- Live CNN integration - intentionally disabled under ADR-001.
