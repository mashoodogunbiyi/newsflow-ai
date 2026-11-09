# NewsFlow AI Handover Package

## 1. Purpose

This package gives a future maintainer, reviewer, or project owner the information needed to understand, configure, start, test, demonstrate, and maintain NewsFlow AI without relying on undocumented knowledge from the original developer.

It records what has been verified, what remains manual, and which production and source-rights gates are still closed. It does not claim that NewsFlow AI has been deployed publicly.

## 2. Handover status

| Item | Status |
| --- | --- |
| Tested repository baseline before NFA-90 | `375cdcb2557b8953a8776654b563ae9001f0b9e2` |
| Application version | `0.1.0` |
| Release tag | None created |
| Documentation review date | 9 November 2026 |
| NFA-90 candidate | `nfa-90-reproducibility-handover` |
| Final merged commit | Must be captured after merge with `git rev-parse HEAD` |
| Controlled local demonstration | Supported with synthetic data and mocked providers |
| Public production release | No-Go |
| Live CNN integration | No-Go - written authorisation is not available |

The baseline hash identifies the merged repository from which NFA-90 started. The NFA-90 branch cannot honestly identify its final immutable version until it is reviewed, merged, and pulled to local `main`.

## 3. Package contents

| Document | Purpose |
| --- | --- |
| [Reproducibility checklist](reproducibility-checklist.md) | Clean setup, configuration, startup, migration, seed, testing, workflow, and repeatability procedure |
| [Reproducibility results](reproducibility-results.md) | Executed commands, measured results, failures, retests, and limitations |
| [Maintenance guide](maintenance-guide.md) | Code ownership map, routine maintenance, operational responsibilities, and change controls |
| [Handover checklist](handover-checklist.md) | Transfer status, remaining actions, final version capture, and approval record |
| [Main README](../../README.md) | Project introduction and first-time setup |
| [Developer guide](../developer-guide.md) | Repository structure and daily engineering workflow |
| [API reference](../api-reference.md) | API routes, authentication, errors, pagination, and local OpenAPI access |
| [Architecture package](../architecture/system-architecture.md) | Components, trust boundaries, decisions, and data flows |
| [Deployment package](../deployment/deployment-guide.md) | Proposed hosting, environment, operations, backup, recovery, and rollback guidance |
| [Demonstration package](../demonstration/README.md) | Repeatable synthetic walkthrough, rehearsal, fallback, and evidence |
| [Testing guide](../testing.md) | Test commands, isolation rules, CI coverage, and recorded results |

## 4. Reproducibility boundary

The supported reproducibility target is a controlled local environment:

- Docker Compose runs PostgreSQL 16, Alembic migrations, synthetic seed data, FastAPI, and Next.js.
- The deterministic demonstration runs the real Next.js interface against a loopback mock API.
- Routine tests use synthetic articles, test users, temporary storage, and mocked OpenAI responses.
- The repository does not contain a real OpenAI key, database password, private user record, or restricted CNN content.

The following are not verified by this handover:

- public production deployment;
- a managed secret store, monitoring platform, backup service, or restore proof;
- a production private-object-storage adapter;
- live CNN ingestion or permission to reuse CNN content;
- provider availability, credit, or model access for a live OpenAI request;
- completed human UAT, representative screen-reader acceptance, or production security sign-off.

## 5. First actions for a new maintainer

1. Read the main README and this handover index.
2. Confirm the checked-out revision with `git rev-parse HEAD` and compare it with the final handover record.
3. Copy `.env.example` to the ignored `.env` file and use development-only values.
4. Run the clean-checkout documentation verifier.
5. Start the isolated Docker environment and confirm `/health`, `/ready`, the frontend, migrations, and seed data.
6. Run the deterministic backend, frontend, and browser tests.
7. Run `npm run demo` and complete the primary synthetic workflow.
8. Review the No-Go restrictions before changing any provider, hosting, storage, or production setting.

## 6. Ownership and final acceptance

Mashood Ogunbiyi is the current project owner. Technical preparation of this package does not replace owner review. Final handover acceptance requires the owner to:

1. merge the NFA-90 pull request;
2. pull the merged `main` branch;
3. record the final commit and pull request in Jira;
4. confirm that required files are tracked and the working tree is clean;
5. review the known limitations and outstanding risks; and
6. approve the handover checklist or record requested changes.

