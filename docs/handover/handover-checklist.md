# NewsFlow AI Final Handover Checklist

## 1. Technical package

- [x] Repository structure is documented.
- [x] Safe environment template exists.
- [x] Real `.env` files and virtual environments are ignored.
- [x] Docker startup, shutdown, health, migration, seed, restart, and persistence procedures are documented.
- [x] Backend and frontend manual setup commands are documented.
- [x] Automated backend, frontend, browser, security, packaging, and documentation checks are documented.
- [x] Architecture and data-flow documents are linked.
- [x] API documentation and local OpenAPI routes are linked.
- [x] Deployment, operations, backup, recovery, and rollback guidance is linked.
- [x] Synthetic demonstration and fallback instructions are linked.
- [x] Source-rights, AI-safety, security, privacy, and production limitations are explicit.
- [x] Maintenance responsibilities and missing production ownership information are recorded.

## 2. NFA-90 verification

- [x] Handover contract passes.
- [x] Isolated candidate-checkout verification passes.
- [x] Secret scan passes and `.env` is confirmed ignored.
- [x] Backend deterministic quality checks pass.
- [x] Frontend deterministic quality checks pass.
- [x] Browser end-to-end workflow passes.
- [x] Docker lifecycle and database persistence proof pass.
- [x] Patch integrity check passes.
- [x] Actual results and any failure or retest are recorded.

These boxes are updated only after their commands execute successfully.

## 3. Final version capture after merge

- [ ] NFA-90 pull request is reviewed and merged.
- [ ] Local `main` is updated with `git pull --ff-only origin main`.
- [ ] Final commit from `git rev-parse HEAD` is recorded below and in Jira.
- [ ] Pull request URL is recorded below and in Jira.
- [ ] Release tag is recorded, or `None` is confirmed.
- [ ] `git status --short --branch` shows a clean, current `main`.
- [ ] `git ls-files docs/handover scripts/verify_handover_package.py scripts/verify_handover_clean_checkout.py` lists the required handover files.

| Final field | Value |
| --- | --- |
| Final commit | Pending merge |
| Pull request | Pending |
| Release tag | None at candidate verification |
| Final version captured by | Pending |
| Final capture date | Pending |

## 4. Owner review

- [ ] Mashood Ogunbiyi has reviewed the handover package.
- [ ] Requested corrections have been completed or recorded.
- [ ] Known limitations and residual risks have been accepted for the controlled local demonstration.
- [ ] Jira NFA-90 contains the repository, pull request, final commit, verification, and approval evidence.
- [ ] The issue is moved to Done only after the acceptance criteria are satisfied.

## 5. Explicit No-Go items

The following must not be represented as complete during handover:

- live CNN ingestion or reuse permission;
- public production deployment;
- production managed secrets, private storage, monitoring, backup, or restore proof;
- completed human UAT or representative screen-reader acceptance;
- automatic LinkedIn publishing; and
- a software licence decision.

## 6. Approval record

| Role | Name | Decision | Date |
| --- | --- | --- | --- |
| Project owner | Mashood Ogunbiyi | Pending review | Pending |
| Technical reviewer | Not assigned | Pending | Pending |

