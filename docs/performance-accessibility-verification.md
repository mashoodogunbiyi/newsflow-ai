# NFA-80 Performance and Accessibility Verification

## Outcome

NFA-80 establishes repeatable performance budgets and verifies the NewsFlow AI frontend and backend against representative local workloads and applicable WCAG 2.2 Level AA requirements.

The automated work is complete and ready for review. The local guardrails pass, one serious accessible-name defect found by real-browser testing has been fixed, and no automated release blocker remains. This report does not claim production-scale performance or complete WCAG conformance. Staging PostgreSQL query plans, Lighthouse on a deployment-like build, and a human VoiceOver journey remain release-readiness gates.

## Scope and safety

The verification covers:

- The authenticated article dashboard and its API request count.
- Article catalogue and content-library API latency and payload size.
- Bounded pagination and representative concurrent article requests.
- Authenticated private-image delivery.
- Production JavaScript bundle size.
- Generation timeout recovery and preservation of user selections.
- Browser accessibility, colour contrast, focus, keyboard use, form errors, mobile and tablet overflow, and reduced motion.
- Article and saved-content query structure and supporting indexes.

All workloads use synthetic articles, synthetic users, mocked provider responses, temporary or in-memory storage, and a deterministic local API. They do not call CNN, OpenAI, LinkedIn, a production database, or production object storage.

## Test environment

Measurements were taken on 4 November 2026 using:

| Component           | Local environment                                                         |
| ------------------- | ------------------------------------------------------------------------- |
| Computer            | Apple MacBook Air                                                         |
| Operating system    | macOS 26.5.2, build 25F84                                                 |
| Python              | 3.12.15 in `apps/api/.venv`                                               |
| Node.js             | 26.11.1 locally; CI remains pinned to Node.js 22                          |
| Next.js             | 16.4.2 production build using Webpack                                     |
| Browser runner      | Playwright 1.64.1 with Chromium                                           |
| Backend measurement | FastAPI `TestClient`, in-process ASGI, synthetic in-memory repositories   |
| Browser measurement | Production Next.js server on localhost with deterministic mock API        |
| PostgreSQL          | Static query and index review only; no local PostgreSQL timing is claimed |

Local in-process and localhost results are regression baselines. They exclude deployment networking, managed database latency, object-storage latency, cold starts, and real user-device constraints.

## Performance targets

The targets below are development guardrails. Deployment acceptance targets must be confirmed on staging with production-like data and infrastructure.

| Area                          | Workload                                                         |                                                                                                    Guardrail |
| ----------------------------- | ---------------------------------------------------------------- | -----------------------------------------------------------------------------------------------------------: |
| Article API                   | 100 synthetic records, 30 measured requests after 5 warmups      |                                                   p95 at or below 150 ms; response at or below 150,000 bytes |
| Content library API           | 100 synthetic saved drafts, 30 measured requests after 5 warmups |                                                   p95 at or below 200 ms; response at or below 250,000 bytes |
| Private image API             | Authenticated 1 MiB image, 12 measured requests after 2 warmups  |                                                           p95 at or below 250 ms; exact byte count preserved |
| Concurrent article API        | 24 requests using 8 workers                                      |                                                                              all 200; p95 at or below 750 ms |
| Dashboard browser navigation  | Production Next.js plus deterministic local API                  |                                           DOM content loaded at or below 3,000 ms; load at or below 4,000 ms |
| Dashboard request count       | One fresh dashboard navigation                                   |                                                    exactly one article-list request; no library-list request |
| Private image browser request | Authenticated deterministic image                                |                                                      response at or below 1,000 ms; private no-store caching |
| Production JavaScript         | All `.next/static/chunks` JavaScript                             | raw at or below 1,500,000 bytes; gzip at or below 500,000 bytes; largest raw chunk at or below 350,000 bytes |
| Accessibility                 | Dashboard at 375 x 812, 768 x 1024, and 1440 x 900               |                                zero selected WCAG 2.0, 2.1, and 2.2 A or AA axe violations; no page overflow |

## Measured results

### Backend and payload baseline

| Workload                  |                          Result | Budget result |
| ------------------------- | ------------------------------: | ------------- |
| Article list p95          |                        1.217 ms | Pass          |
| Article list response     |                    47,611 bytes | Pass          |
| Content library p95       |                        1.437 ms | Pass          |
| Content library response  |                    91,225 bytes | Pass          |
| 1 MiB private image p95   |                        1.012 ms | Pass          |
| Concurrent article p95    | 6.422 ms; 24 of 24 returned 200 | Pass          |
| Article maximum page size |           101 rejected with 422 | Pass          |
| Library maximum page size |           101 rejected with 422 | Pass          |

These results measure application code and serialisation with in-memory repositories. They do not include PostgreSQL or network latency and must not be presented as production API response times.

### Browser and bundle baseline

| Workload                     |                                  Result | Budget result |
| ---------------------------- | --------------------------------------: | ------------- |
| Dashboard response start     |                                  1.7 ms | Informational |
| Dashboard DOM content loaded |                                 22.7 ms | Pass          |
| Dashboard load               |                                 25.1 ms | Pass          |
| Dashboard article requests   |                                       1 | Pass          |
| Dashboard library requests   |                                       0 | Pass          |
| Private image                | 68 bytes in 2.4 ms, `private, no-store` | Pass          |
| Production JavaScript raw    |        1,041,667 bytes across 42 chunks | Pass          |
| Production JavaScript gzip   |                           326,988 bytes | Pass          |
| Largest raw chunk            |                           243,671 bytes | Pass          |

The browser numbers use a warm local computer and deterministic localhost API. They are useful for catching regressions, not predicting public internet performance.

## Database query review

### Article catalogue

- The repository uses one bounded joined select for catalogue records rather than one query per article.
- The API limit is bounded at 100 and the normal dashboard asks for 9 records.
- Pagination uses a signed cursor and keyset conditions based on publication time and stable identifiers. It does not use an ever-growing row offset.
- Migrations provide article publication, category, identity, rights, and active-record indexes required by filtering and stable ordering.
- Rights and retention checks remain in the query path; no security condition was removed for speed.

### Content library

- The list path uses one owner-scoped count query and one bounded joined list query. It avoids an N+1 query for selected image metadata.
- Page size is bounded at 100 and owner filtering is mandatory.
- `ix_saved_content_owner_updated` supports the owner and updated-time listing order.
- The current library contract uses offset pagination. This is acceptable for the MVP's bounded personal dataset, but high page numbers can become slower as a user's library grows. Keyset pagination is a documented follow-up before high-volume production use.

### Required staging evidence

No isolated PostgreSQL service was active during these local timings. Before production approval, run `EXPLAIN (ANALYZE, BUFFERS)` on representative article and library queries using synthetic production-scale data. Record query duration, row estimates, actual rows, index use, buffers, and any sequential scans. Private or production user content must not be copied into the report.

## Frontend and network review

- The dashboard is server-rendered and makes one article-list request per fresh navigation in the measured scenario.
- The catalogue, library, and image routes have bounded payload or storage limits.
- The production bundle has an executable budget check rather than a manually copied size.
- Authenticated images continue through the same-origin private gateway. They are not moved to public URLs or the default Next.js image optimiser because authentication headers must be preserved.
- Image delivery is integrity checked and marked private and no-store. The current local adapter reads the bounded object before returning it; production object-storage range or streaming behaviour remains an infrastructure follow-up.
- Text-generation timeout handling keeps the selected article, tone, and length and exposes a deliberate retry. No automatic paid retry was introduced.

## Accessibility verification

The production browser suite runs axe-core with applicable WCAG 2.0, 2.1, and 2.2 A and AA tags. Unlike the jsdom component audit, the real-browser audit leaves axe colour-contrast checking enabled.

Automated Chromium evidence confirms:

- Zero selected axe violations on the complete dashboard at 375 x 812, 768 x 1024, and 1440 x 900.
- No page-level horizontal overflow at those viewports.
- The accessibility tree exposes the main heading and dashboard form controls.
- The skip link is keyboard reachable, visibly focused, and moves focus to workspace content.
- The mobile navigation receives focus on open and returns it to the toggle on Escape.
- Invalid form fields expose associated errors and receive focus.
- Authentication failures use an assertive alert and receive programmatic focus.
- Generation timeouts use an alert, preserve choices, and expose a deliberate retry.
- Reduced-motion emulation reduces non-essential transition and animation duration to the enforced near-zero value.
- The private-image response preserves authenticated, no-store delivery.

The browser accessibility tree is useful evidence but is not the same as using VoiceOver or another assistive technology. A representative human VoiceOver journey remains required before claiming complete accessibility acceptance.

## Defect record

| ID            | Severity | Finding                                                                                                                                                                                                  | Resolution                                                                                                                 | Status                         |
| ------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| NFA80-A11Y-01 | Serious  | The article card displayed `View source`, while its longer accessible name did not contain that visible text as a contiguous label. This failed axe's label-content-name-mismatch rule at desktop width. | Changed the accessible name to `View source: [article title] (opens in a new tab)` and updated the focused component test. | Resolved and regression tested |

The initial NFA-80 browser run also exposed test-harness issues: a non-specific `main` selector, a framework-owned alert, a nonexistent tone label, and accessibility-tree inspection before streamed catalogue content completed. These were corrected in the test without weakening the application requirements.

## Automated commands

From `apps/api`:

```bash
.venv/bin/pytest tests/performance -s
.venv/bin/ruff check tests/performance
.venv/bin/ruff format --check tests/performance
```

From `apps/web`:

```bash
npm run lint
npx next typegen
npm run typecheck
npm test
npm run test:e2e
npm run performance:bundle
npm run format:check
```

`npm run test:e2e` now builds and starts the production Next.js application before running Chromium. GitHub Actions runs the focused backend performance guardrails and the production bundle budget automatically.

## Remaining limitations and release gates

1. Run PostgreSQL query plans and API timings on an approved staging environment with production-like synthetic volume.
2. Run Lighthouse against a deployment-like URL and retain the report with the browser, device emulation, throttling, and build identifier.
3. Complete the documented VoiceOver journey on macOS, including login errors, dashboard navigation, generation status, editor, preview, and image designation.
4. Repeat measurements on a representative lower-powered mobile device and typical network profile.
5. Confirm production object-storage image latency and caching without weakening private access controls.
6. Revisit offset pagination if a representative personal library grows beyond the MVP workload.

## Acceptance decision

- Automated implementation status: Complete and ready for review.
- Automated performance guardrails: Passed in the documented local environment.
- Automated accessibility and responsive checks: Passed in Chromium.
- Release-blocking defects from this review: None unresolved.
- Production performance decision: Pending staging measurements.
- Full accessibility decision: Pending human VoiceOver review.
- Jira recommendation: Move NFA-80 to Review after the branch is pushed and CI passes. Move it to Done after Mashood Ogunbiyi reviews this report and records any required manual release evidence.
