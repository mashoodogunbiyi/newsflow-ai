# NewsFlow AI Reproducibility Results

## 1. Record metadata

| Field | Value |
| --- | --- |
| Jira issue | NFA-90 |
| Verification date | 9 November 2026 |
| Tested pre-NFA-90 baseline | `375cdcb2557b8953a8776654b563ae9001f0b9e2` |
| Candidate branch | `nfa-90-reproducibility-handover` |
| Application version | `0.1.0` |
| Release tag | None |
| Final merged commit | `14c97464be98d7d6a4275158b7215401122974c7` through [PR #82](https://github.com/mashoodogunbiyi/newsflow-ai/pull/82) |
| Data boundary | Synthetic records and mocked providers only |

## 2. Verification environment

The NFA-90 candidate was prepared on macOS in the local development repository. Docker verification uses isolated Compose project names, synthetic credentials, loopback-only ports, fixture source mode, disposable volumes, and automatic cleanup. The documentation clean-checkout test uses a temporary directory and excludes ignored local state.

No real OpenAI request, CNN request, production database, production user record, production storage service, or public deployment is required by the handover verification.

## 3. Executed results

The result table is completed only from commands executed against this candidate.

| Area | Command or evidence | Result |
| --- | --- | --- |
| Handover contract | `python3 scripts/verify_handover_package.py` | Passed |
| Isolated candidate checkout | `python3 scripts/verify_handover_clean_checkout.py` | Passed |
| Documentation contracts | Architecture, deployment, demonstration, report, and README verifiers | Passed in the isolated candidate checkout |
| Secret protection | `python3 scripts/scan_secrets.py` and `.env` ignore check | Passed; `.gitignore` rule `**/.env` excludes the local file |
| Backend quality | Ruff, formatting, deterministic Pytest, and `pip-audit` | Passed; 489 tests passed, 16 safety-gated tests skipped, 1 optional live-provider test deselected, and no known dependency vulnerability found |
| Frontend quality | ESLint, Prettier, TypeScript, Vitest, build, and production dependency audit | Passed; 173 tests across 36 files, successful Next.js production build, and 0 production npm vulnerabilities |
| Browser workflow | `CI=1 npm run test:e2e` | Passed all 13 Chromium scenarios after environment-only startup retries |
| Docker lifecycle | Isolated `verify_docker_packaging.sh` project on ports 43200 to 43202 | Passed; configuration fail-closed, builds, migration `20261102_0015`, seed, health, non-root users, restart, stop/start, persistence, and cleanup verified |
| Patch integrity | `git diff --check` | Passed |

## 4. Reproducibility conclusions

The NFA-90 technical candidate is reproducible within its documented local and synthetic-data boundary:

- Required source, configuration template, documentation, migration, seed, test, and workflow files were present in an isolated candidate checkout.
- Routine tests passed without reading the developer's ignored `.env` or contacting a live news or AI provider.
- Docker built the application, migrated and seeded a fresh PostgreSQL volume, reported service health, survived restarts and stop/start, preserved its marker, and cleaned up.
- The deterministic browser suite completed the primary workflow and access-control, failure, accessibility, responsive, and private-delivery scenarios.
- Documentation links, commands, implementation claims, source-rights restrictions, and production limitations matched the repository contracts.

This result supports owner review and merge of the handover candidate. It does not prove a public production environment, live-provider availability, human acceptance, or a final immutable version.

## 5. Gaps and unresolved items

The following items cannot be marked complete by code changes alone:

1. A release tag has not been created.
2. Final project closure is reviewed under NFA-91.
3. Human UAT and representative screen-reader acceptance remain incomplete.
4. Public hosting, production secrets, managed private storage, monitoring, backups, restore testing, and incident operations are not implemented.
5. Live CNN ingestion remains No-Go without written authorisation.
6. Live OpenAI calls depend on a separately configured key, approved model access, available credit, and external provider availability.

These are reported limitations, not passing test results.

## 6. Failure and retest record

Record any NFA-90 failure here with the failed command, cause, changed file, rerun result, and date. Do not delete a useful failure record merely because a later run passes.

Two Playwright startup attempts failed before tests executed:

1. The restricted execution sandbox rejected the loopback mock API with `listen EPERM` on port 4100.
2. The first approved local-port rerun timed out while Playwright was reusing or starting its web-server environment. No browser assertion ran or failed.

The suite was rerun with `CI=1`, which forces fresh Playwright web servers. All 13 Chromium scenarios passed. No application code or assertion was weakened.

During the clean Docker build, npm reported 10 moderate advisories across the full installation, including development dependencies. The repository's production threshold was then checked explicitly with `npm audit --omit=dev --audit-level=high`; it passed with 0 production vulnerabilities. `pip-audit` reported no known Python dependency vulnerability and correctly skipped the local unpublished `newsflow-api` package itself.

