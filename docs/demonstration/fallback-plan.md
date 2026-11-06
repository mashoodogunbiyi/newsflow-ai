# NewsFlow AI Demonstration Fallback Plan

## 1. Principle

Preserve accuracy, privacy, and the rights boundary even when the preferred demonstration path fails. A fallback must be identified honestly. Mocked output, screenshots, and recorded evidence must never be described as a live provider response.

## 2. Preferred fallback order

1. Restart the deterministic `npm run demo` environment.
2. Use the four synthetic screenshots and explain the workflow.
3. Run or show the result of the deterministic Playwright journey.
4. Use architecture and data-flow diagrams for a technical walkthrough.
5. Reschedule the live walkthrough if the available evidence cannot support an accurate demonstration.

## 3. Failure playbook

| Failure | Immediate action | Continue with | What to tell the audience |
| --- | --- | --- | --- |
| Docker or PostgreSQL will not start | Do not reset or delete data during a presentation | Deterministic `npm run demo` mode | The integrated environment is unavailable, so the approved local mock is being used |
| OpenAI is unavailable, rate limited, or out of credit | Do not repeatedly submit paid requests | Mocked text and image responses | The shown response is deterministic test output, not a live OpenAI result |
| Network connection is unavailable | Avoid provider dashboards and remote dependencies | Local mock, screenshots, and repository diagrams | The core demonstration is intentionally able to run offline after dependencies are installed |
| Port 3100 or 4100 is busy | Stop the known local process only, or close the conflicting development task | Restart `npm run demo` | The local presentation services are being restarted |
| Browser session is inconsistent | Close the private window and restart the demo command to reset in-memory state | Fresh private window | The synthetic environment has been reset to its known initial state |
| Search URL is not found | Use the exact documented synthetic URL | Valid approved fixture | Arbitrary URLs are deliberately rejected because the product does not scrape unknown pages |
| Draft or image generation shows a controlled failure | Preserve current edits and do not spam retry | Explain error handling, then restart deterministic mode if needed | The product fails safely and does not report false success |
| Screenshot or diagram does not render | Open the file directly from the repository | Presenter script and verbal explanation | The documentation asset is being opened locally |
| A secret or private notification appears | Stop screen sharing immediately | Resume only after the information is closed and exposure is assessed | Do not continue until privacy is protected |
| A rights or safety statement is uncertain | Stop the affected claim | Read the approved limitation from the README or release review | The project will not claim permission or readiness without evidence |

## 4. Prepared offline evidence

The repository stores these safe assets:

- `docs/screenshots/homepage.png`;
- `docs/screenshots/article-dashboard.png`;
- `docs/screenshots/generation-workspace.png`;
- `docs/screenshots/content-library.png`;
- `docs/architecture/system-architecture.md`;
- `docs/architecture/data-flow.md`; and
- `docs/integration-e2e-testing.md`.

The screenshots contain synthetic data only. Review them again before every public recording or portfolio update.

## 5. Recovery commands

Stop deterministic mode with `Ctrl+C`, then restart it:

```bash
cd apps/web
npm run demo
```

Stop the Docker environment without deleting volumes:

```bash
docker compose down
```

Do not use `docker compose down --volumes` during recovery unless intentional data deletion has been separately approved.

## 6. Abort conditions

Stop the demonstration if:

- a real secret, session value, or private record may have been exposed;
- a Critical or High security or data-integrity defect appears;
- the product starts retrieving an unauthorised source;
- the presenter cannot distinguish mocked output from a live result;
- user-owned content appears under the wrong account; or
- the evidence no longer supports an accurate claim.

Record the issue in Jira before another rehearsal.

