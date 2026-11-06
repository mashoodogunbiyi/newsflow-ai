# NewsFlow AI Demonstration Evidence

## 1. Evidence status

| Item | Status | Evidence |
| --- | --- | --- |
| Demonstration audience and objectives | Prepared | `docs/demonstration/README.md` |
| Presenter script | Prepared | `docs/demonstration/demo-script.md` |
| Synthetic fixtures and test account | Prepared | `apps/web/e2e/support/mock-api.mjs` |
| Repeatable local launcher | Prepared | `npm run demo` |
| Complete browser workflow | Automated | `apps/web/e2e/content-workflow.spec.ts` |
| Authentication and protected routes | Automated | `apps/web/e2e/authentication.spec.ts` |
| Provider failure and cross-user isolation | Automated | `apps/web/e2e/failure-and-ownership.spec.ts` |
| Responsive and accessibility behaviour | Automated | `apps/web/e2e/performance-accessibility.spec.ts` |
| Screenshots | Prepared | `docs/screenshots/README.md` |
| Architecture explanation | Prepared | `docs/architecture/system-architecture.md` and `data-flow.md` |
| Fallback plan | Prepared | `docs/demonstration/fallback-plan.md` |
| Human narrated rehearsal | Pending project owner | Complete `rehearsal-checklist.md` |
| Video recording | Not required for technical completion | Screenshots and deterministic browser evidence are the current equivalent evidence |

## 2. Automated workflow coverage

The primary Playwright journey verifies:

1. login with a synthetic user;
2. approved URL selection;
3. source review;
4. mocked draft generation;
5. human text editing and preview;
6. mocked image generation and regeneration;
7. preservation of edited text;
8. private draft saving;
9. reopening saved content;
10. text copying;
11. owner-authorised image downloading;
12. confirmed deletion; and
13. the final empty library state.

Separate scenarios verify protected-route redirects, generic invalid-login errors, controlled provider failures, cross-user non-disclosure, keyboard operation, responsive viewports, accessible status messaging, and bounded network requests.

## 3. Verification record

Update this table only with commands that actually ran. Do not copy a CI count from an older branch.

| Date | Environment | Command | Result |
| --- | --- | --- | --- |
| 6 November 2026 | Local macOS branch `nfa-88-demonstration-package` | `npm run demo` plus local health requests | Passed - mock API returned healthy, frontend returned HTTP 200, and `Ctrl+C` released ports 3100 and 4100 |
| 6 November 2026 | Local macOS branch `nfa-88-demonstration-package` | `npm run lint` | Passed |
| 6 November 2026 | Local macOS branch `nfa-88-demonstration-package` | `npm run format:check` | Passed |
| 6 November 2026 | Local macOS branch `nfa-88-demonstration-package` | `npm run typecheck` | Passed |
| 6 November 2026 | Local macOS branch `nfa-88-demonstration-package` | `npm test` | Passed - 36 test files and 173 tests |
| 6 November 2026 | Local macOS branch `nfa-88-demonstration-package` | `npm run test:e2e` | Passed - 13 Playwright Chromium scenarios including the complete content journey |
| 6 November 2026 | Local macOS branch `nfa-88-demonstration-package` | `npm run screenshots:docs` | Passed - all four synthetic screenshots recreated with no tracked image changes |
| 6 November 2026 | Local macOS branch `nfa-88-demonstration-package` | Documentation verifiers and `git diff --check` | Passed |

## 4. Screenshot record

The current screenshots use a 1440 by 960 desktop viewport and contain synthetic data only:

- [Homepage](../screenshots/homepage.png)
- [Article dashboard](../screenshots/article-dashboard.png)
- [Generation workspace](../screenshots/generation-workspace.png)
- [Content library](../screenshots/content-library.png)

Recreate them with:

```bash
cd apps/web
npm run screenshots:docs
```

## 5. Defect record

| ID | Severity | Description | Status | Jira reference |
| --- | --- | --- | --- | --- |
| None recorded | - | No NFA-88 defect recorded at package creation | Open for rehearsal findings | Add if discovered |

## 6. Known limitations

- A human narrated rehearsal and owner approval are still required.
- Live CNN access is unavailable and unauthorised.
- The default demo uses mocked OpenAI responses.
- A real OpenAI key is neither read nor needed by `npm run demo`.
- The public test account exists only in the loopback mock API.
- The demo is local and is not evidence of a production deployment.
- Screenshots are static evidence and must not be presented as a live workflow.
- Human UAT and representative screen-reader review remain pending.

