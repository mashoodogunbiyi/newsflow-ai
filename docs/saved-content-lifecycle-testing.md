# NFA-73 Saved Content Lifecycle Testing

## Purpose

NFA-73 verifies that NewsFlow AI's saved-content features operate as one secure lifecycle. The suite covers saving, retrieving, listing, editing, versioning, restoring, copying, downloading, deleting, cleanup, and retention without using real users, live news, production data, or external AI services.

## Test strategy

The lifecycle is tested at complementary layers:

- Backend unit and API tests validate each request contract, error response, ownership rule, concurrency rule, cleanup failure, and retention operation.
- `test_saved_content_lifecycle_e2e.py` runs one joined HTTP journey through FastAPI, PostgreSQL, authentication cookies, CSRF protection, private image storage, deletion, and retention.
- Frontend component tests verify current edited-text copy, private image download, library browsing, version review and restoration, explicit delete confirmation, and controlled failures.
- GitHub Actions runs the backend suite, the isolated PostgreSQL lifecycle suite, and the complete frontend suite for every pull request and push to `main`.

## Isolated fixtures

The joined test uses:

- two synthetic accounts using the reserved `example.com` documentation domain;
- one synthetic, explicitly permitted article and source snapshot;
- one synthetic AI draft, one synthetic image record, and temporary image bytes;
- the disposable `newsflow_saved_draft_test` PostgreSQL database;
- a per-test temporary private-storage directory;
- no CNN request, OpenAI request, API key, real credential, or personal information.

The database name and `ALLOW_DATABASE_RESET_FOR_TESTS=true` safety gate are both required before migrations can rebuild the test database.

## Coverage matrix

| Requirement | Automated evidence |
| --- | --- |
| Authentication and CSRF | Unauthenticated reads fail; state changes use the authenticated CSRF token |
| Save and duplicate handling | Initial save, idempotent replay, and different-key duplicate conflict |
| Retrieve, list, and pagination | Owned detail, page metadata, first page, and empty second page |
| Edit and concurrency | Successful edit plus stale-version conflict with unchanged current content |
| Version history | Initial and manual versions, paginated history, detail retrieval, restoration tests, and immutable associations |
| Text copy | Frontend copies the current edited text and preserves line breaks |
| Image download | Backend delivers owner-authorised bytes with a safe attachment name; frontend handles download feedback |
| Ownership | A second user cannot read, edit, delete, download, or inspect history for the first user's objects |
| Image and history ownership | Cross-user image and version routes return the same private not-found response |
| Delete and deleted access | Explicit frontend confirmation, owner-only backend deletion, immediate 404 responses, and empty library results |
| Cleanup and partial failure | Successful object cleanup plus focused retry tests for storage failures |
| Retention | Due saved data and history are removed while content-free audit evidence follows its separate policy |
| Security | No storage key, password, password hash, session identifier, or secret appears in public content responses |
| CI | Normal backend and frontend suites plus the isolated PostgreSQL E7 lifecycle command |

## Commands

From the repository root, run the focused backend checks:

```bash
apps/api/.venv/bin/ruff check apps/api/tests/test_saved_content_lifecycle_e2e.py
apps/api/.venv/bin/ruff format --check apps/api/tests/test_saved_content_lifecycle_e2e.py
```

Run the isolated PostgreSQL lifecycle tests only against the disposable database:

```bash
cd apps/api
TEST_DATABASE_URL=postgresql://newsflow_test:newsflow_test_password@localhost:5432/newsflow_saved_draft_test \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
.venv/bin/pytest -m integration \
  tests/test_saved_draft_integration.py \
  tests/test_saved_content_lifecycle_e2e.py
```

Run the related frontend checks:

```bash
cd apps/web
npm test -- \
  __tests__/content-library.test.tsx \
  __tests__/version-history.test.tsx \
  __tests__/content-export.test.tsx \
  __tests__/draft-deletion.test.tsx
```

Run the complete quality gates before merging:

```bash
cd apps/api
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -m "not live_ai" --cov=app --cov-report=term-missing --cov-fail-under=75

cd ../web
npm run lint
npm run format:check
npx next typegen
npm run typecheck
npm test
npm run build
```

## Expected failures and limitations

- A missing session returns `401`.
- A missing or differently owned private object returns the same `404` response.
- Missing or invalid CSRF evidence returns `403` for state-changing requests.
- Duplicate saves and stale edits return controlled `409` responses.
- Storage failures remain retryable and do not restore deleted content to active access.
- Browser clipboard permission behavior is represented by component tests because it depends on the browser security model.
- Database reset and migration tests are intentionally opt-in because they destroy only the explicitly named disposable test database.

All fixtures are synthetic and deterministic. The normal suite never calls CNN, OpenAI, LinkedIn, or another live external service.

## Verification result

- Isolated E7 PostgreSQL tests: 3 passed.
- Complete backend suite: 441 passed, 16 skipped, and 1 optional live-model test deselected.
- Backend branch-aware coverage: 78.15 percent, above the required 75 percent.
- Focused E7 frontend tests: 18 passed across 4 files.
- Complete frontend suite: 163 passed across 34 files.
- Backend Ruff checks, frontend ESLint, Prettier, TypeScript, route generation, and the Next.js production build passed.

Implementation status: Ready for Mashood Ogunbiyi's review.
