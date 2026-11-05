# NFA-77 - Integration and End-to-End Testing

## 1. Purpose

NFA-77 verifies that NewsFlow AI's main components work together, not only as isolated units. It covers the complete review-first workflow from authentication and synthetic article discovery through mocked AI generation, private saving, export, and deletion.

Routine tests must be deterministic and must not use live CNN content, real OpenAI calls, production credentials, or production records.

## 2. Test layers

### 2.1 Backend integration scope

The backend integration layer uses Pytest, HTTPX or FastAPI's test client, disposable PostgreSQL databases, synthetic records, mocked provider responses, and temporary private image storage.

| Joined behaviour                                                                                                 | Automated evidence                                                                                          |
| ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Authentication, sessions, CSRF, registration, login, logout, and expiry                                          | `apps/api/tests/test_auth_integration.py`, `test_registration_integration.py`, and authentication API tests |
| Provider, validation, deduplication, provenance, rights, synchronisation, PostgreSQL, and article REST catalogue | `apps/api/tests/test_catalogue_pipeline_e2e.py` and `test_article_catalogue_integration.py`                 |
| Mocked OpenAI text generation, rights gates, limits, persistence, and safe errors                                | `apps/api/tests/test_generation_workflow_acceptance.py` and generation integration tests                    |
| Mocked image generation, validation, temporary storage, metadata, regeneration, and owner delivery               | `apps/api/tests/test_image_workflow_integration.py` and `test_image_workflow_acceptance.py`                 |
| Saving, editing, history, restoration, export, deletion, retention, and cross-user denial                        | `apps/api/tests/test_saved_draft_integration.py` and `test_saved_content_lifecycle_e2e.py`                  |

The integration databases are deliberately named test databases. `ALLOW_DATABASE_RESET_FOR_TESTS=true` is required before destructive setup can run. Production and normal development database names are rejected by the test safety gate.

### 2.2 Browser end-to-end scope

Playwright runs the real Next.js application in Chromium against `e2e/support/mock-api.mjs`. The mock boundary behaves like the public FastAPI contract while keeping tests fast, repeatable, and independent of external services.

The browser suite verifies:

- unauthenticated route protection and valid login;
- invalid credentials and safe error text;
- synthetic article browsing and selection;
- mocked LinkedIn draft generation;
- live draft editing and preview;
- mocked illustration generation, regeneration, original-version retention, and selection;
- durable save through the Next.js gateway contract;
- saved-draft reopening with text and selected image;
- clipboard copy and private image download;
- confirmed deletion and the empty library state;
- provider failure and retry presentation;
- empty catalogue presentation; and
- cross-user draft non-disclosure.

The browser mock is not a replacement for backend integration tests. Playwright proves the browser-to-contract journey, while the Pytest integration suites prove that the real FastAPI, PostgreSQL, rights controls, and private storage implement that contract.

## 3. Isolated test environment

| Resource         | Isolation rule                                                                        |
| ---------------- | ------------------------------------------------------------------------------------- |
| News articles    | Original synthetic metadata under the NewsFlow AI fixture identity                    |
| Text generation  | Deterministic mocked draft; no OpenAI credential or request                           |
| Image generation | Deterministic mocked metadata and a one-pixel local PNG                               |
| PostgreSQL       | Disposable, explicitly named test databases only                                      |
| Image storage    | Temporary directories removed by test cleanup                                         |
| Users            | Synthetic `example.com` users and non-production passwords                            |
| Browser state    | Mock API reset before every Playwright test; one worker prevents shared-state races   |
| Reports          | Failure screenshots, trace, and video are written only to ignored test-output folders |

The Playwright mock server binds to `127.0.0.1:4100`. Next.js binds to `127.0.0.1:3100` with its internal API base URL set to the mock. Neither server is exposed externally by the test configuration.

## 4. Primary end-to-end scenario

The primary scenario executes these user-visible steps:

1. Sign in as a synthetic test user.
2. Browse the synthetic authorised catalogue.
3. Select an article and review its attribution.
4. Request a deterministic mocked LinkedIn draft.
5. Edit the draft and confirm the preview changes.
6. Request a deterministic mocked illustration.
7. Regenerate the illustration, verify the original remains available, and select the new version.
8. Save the reviewed text and selected image to the private library.
9. Reopen the saved draft and verify its text and selected regenerated image.
10. Copy the current edited text.
11. Download the private image through the same-origin gateway.
12. Confirm deletion.
13. Verify the draft disappears and the library returns to its empty state.

No step publishes to LinkedIn.

## 5. Commands

Install the browser once on a developer computer:

```bash
cd apps/web
npx playwright install chromium
```

Run browser end-to-end tests:

```bash
cd apps/web
npm run test:e2e
```

Open the last HTML report when one exists:

```bash
cd apps/web
npm run test:e2e:report
```

Run the complete normal frontend quality set:

```bash
cd apps/web
npm run lint
npm run format:check
npx next typegen
npm run typecheck
npm test
npm run test:e2e
npm run build
```

Run the existing backend integration suites against deliberately isolated PostgreSQL databases using the exact commands in the CI workflow:

```bash
cd apps/api
pytest -m integration tests/test_catalogue_pipeline_e2e.py
pytest -m integration tests/test_article_catalogue_integration.py
pytest -m integration tests/test_image_workflow_integration.py
pytest -m integration tests/test_saved_draft_integration.py tests/test_saved_content_lifecycle_e2e.py
```

Each command requires its documented `TEST_DATABASE_URL` and `ALLOW_DATABASE_RESET_FOR_TESTS=true` setting. Do not copy a development or production database URL into these commands.

## 6. CI execution

GitHub Actions performs these deterministic layers on pull requests and pushes to `main`:

1. secret and dependency checks;
2. backend lint, formatting, unit and acceptance tests;
3. isolated PostgreSQL article, image, and saved-content integration suites;
4. frontend lint, formatting, type checking, and Vitest component tests;
5. Playwright Chromium installation and all browser journeys; and
6. a production Next.js build.

If a browser test fails, CI retains the Playwright HTML report for seven days. Failure output includes the exact scenario, assertion, screenshot, trace, and video where available.

## 7. Defect record

| ID           | Finding                                                                                                                                                                                                     | Resolution                                                                                                                                                                                     | Status   |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| NFA77-DEF-01 | The generated-draft editor allowed text editing and image generation but had no control that called the existing E7 save API. The documented article-to-library journey could not complete in the frontend. | Added the same-origin draft-creation gateway, runtime-validated client, CSRF and idempotency forwarding, controlled save errors, a `Save to library` action, and redirect to the saved record. | Resolved |
| NFA77-DEF-02 | Initial Playwright selectors treated the password visibility control and Next.js route announcer as form or alert targets.                                                                                  | Narrowed selectors to the exact password input and exact visible error messages without weakening the user-visible assertions.                                                                 | Resolved |

## 8. Verification record

Verification date: 3 November 2026.

| Check                                                         | Result                                                 |
| ------------------------------------------------------------- | ------------------------------------------------------ |
| Focused save, proxy, editor, and export components            | 22 tests passed across 3 Vitest files                  |
| Complete frontend component suite                             | 167 tests passed across 35 Vitest files                |
| Browser end-to-end suite                                      | 5 Playwright Chromium scenarios passed in 11.8 seconds |
| Frontend lint, formatting, generated routes, and strict types | Passed                                                 |
| Next.js production build                                      | Passed, including the new `/api/drafts` gateway        |
| Production frontend dependency audit                          | 0 known vulnerabilities                                |
| Deterministic backend suite                                   | 462 tests passed                                       |
| Backend lint and formatting                                   | 206 Python files passed                                |
| Article pipeline PostgreSQL integration                       | 3 scenarios passed                                     |
| Article catalogue PostgreSQL integration                      | 1 scenario passed                                      |
| Image workflow PostgreSQL and temporary-storage integration   | 1 scenario passed                                      |
| Saved-draft PostgreSQL and joined lifecycle integration       | 3 scenarios passed                                     |

All verification used synthetic data, mocked external providers, disposable PostgreSQL databases, and temporary or in-memory storage. No live CNN, OpenAI, LinkedIn, production account, production database, or production object-storage access occurred.

## 9. Known limitations

- Routine browser tests use the deterministic FastAPI contract mock. Real FastAPI and PostgreSQL behaviour is verified separately by the integration suites.
- Chromium is the CI browser for this task. Responsive, accessibility, and component checks remain covered by the NFA-65 suite, but native Safari and Firefox are not part of NFA-77 automation.
- CNN access remains disabled under ADR-001, so all article data is synthetic.
- OpenAI text and image responses are mocked. The optional live-model evaluation remains separately gated and is never selected by routine CI.
- Clipboard and download tests verify browser behaviour in the Playwright environment; final release review should still include a manual pass in supported production browsers.
- The tests prove application behaviour in local and CI environments. They do not replace staging deployment, performance, penetration, disaster-recovery, or production monitoring tests.

## 10. Acceptance decision

NFA-77 is ready for Mashood Ogunbiyi's review. The required backend, frontend, browser, PostgreSQL, formatting, type, build, and dependency checks passed, and the two discovered defects are resolved. Final Jira approval, commit, push, pull-request checks, and merge remain user-controlled steps.
