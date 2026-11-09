# NewsFlow AI - Project Closure Report

## 1. Project overview

NewsFlow AI is a full-stack portfolio application that turns permitted news facts into editable LinkedIn drafts and original AI-generated conceptual illustrations. It uses Next.js and React for the frontend, FastAPI for the backend, PostgreSQL for durable data, Docker for reproducible local services and provider interfaces for article and OpenAI integrations.

The project was managed through a Jira backlog containing 10 Epics, Jira-linked branches, pull requests, evidence comments and repository documentation.

## 2. Original objectives

The original plan aimed to:

1. retrieve CNN news only through an authorised method;
2. let users browse, filter and select articles;
3. generate source-grounded LinkedIn drafts with configurable controls;
4. generate and independently regenerate original supporting images;
5. allow human review, editing, preview, saving, retrieval, copying, downloading and deletion;
6. protect user accounts and private content;
7. preserve source provenance, permitted use and AI traceability;
8. provide reliable error, recovery, usage and monitoring controls;
9. make the application reproducible and testable without live providers; and
10. deliver professional technical, operational, demonstration and handover documentation.

## 3. Objective assessment

| Objective | Final result | Closure assessment |
| --- | --- | --- |
| Authorised CNN retrieval | Written authorisation was not obtained; ADR-001 blocks live access | Not delivered and correctly excluded |
| Article discovery | Fixture-backed catalogue, filtering, pagination and approved URL resolution | Delivered for synthetic data |
| LinkedIn generation | Grounded service, prompts, API, controls, editor and deterministic provider tests | Delivered; live provider is optional and not release verified |
| AI illustration | Prompt, safety, generation, regeneration, validation, local private storage and delivery | Delivered locally; production storage is open |
| Human-controlled workflow | Edit, preview, save, reopen, version, copy, download and delete | Delivered and automated end-to-end |
| Accounts and ownership | Registration, Argon2id, sessions, CSRF and owner-scoped access | Delivered and tested |
| Provenance and rights | Provider interface, normalisation, identity, deduplication, provenance and rights versions | Delivered for the fixture contract |
| Reliability and operations | Limits, idempotency, recovery, health, structured evidence and runbooks | Delivered locally; production operations are open |
| Reproducibility and testing | Docker lifecycle, migrations, seed data, component, integration and browser tests | Delivered and verified |
| Documentation and handover | README, API, architecture, deployment, demonstration, report and handover packages | Delivered and verified |

## 4. Final scope

### 4.1 Delivered scope

- Responsive Next.js application with registration, login, protected workspace and logout.
- FastAPI backend with generated OpenAPI documentation and safe error contracts.
- PostgreSQL schema, 15 Alembic revisions and repeatable synthetic seed data.
- Server-managed sessions, CSRF protection and object-level authorisation.
- Provider-neutral article ingestion with synthetic source, validation, normalisation, deduplication, provenance, rights and synchronisation evidence.
- Article catalogue, exact approved URL lookup, filtering, pagination and source details.
- LinkedIn generation controls, source-grounded prompt templates, output validation, usage limits and monitoring evidence.
- AI image prompt composition, sensitive-news policy, generation boundary, validation, private local storage, regeneration and secure delivery.
- Editor, LinkedIn-inspired preview, saved library, immutable versions, export and deletion lifecycle.
- Docker Compose environment for frontend, backend, migrations, synthetic seed and PostgreSQL.
- Automated security, reliability, performance, accessibility, integration and browser tests.
- Technical report, portfolio case study, screenshots, architecture, deployment, demonstration and handover documentation.

### 4.2 Excluded or incomplete scope

- Live CNN ingestion or processing.
- Arbitrary web-page scraping or URL summarisation.
- Public production deployment.
- Automatic LinkedIn publishing or scheduling.
- Human UAT participant execution and product acceptance.
- Representative VoiceOver acceptance.
- Production private object storage, managed secrets, monitoring, backups, restore and incident response.
- Password reset.
- Payments, subscriptions, social analytics, video generation and mobile applications.

## 5. Epic review summary

All 10 Epics were reviewed in the [Epic review](epic-review.md).

| Epic | Closure status |
| --- | --- |
| E0 - Product discovery, rights and governance | Complete; current decision is No-Go for live CNN and Go for fixtures |
| E1 - Engineering foundation | Complete for local development and CI |
| E2 - Data model and authentication | Complete for the agreed MVP; password reset remains future work |
| E3 - Article discovery and catalogue | Complete for the accepted fixture-only scope; live provider excluded |
| E4 - LinkedIn generation | Complete for backend integration and deterministic verification; live-provider release approval open |
| E5 - AI image generation | Complete with local private storage; production storage open |
| E6 - Dashboard, editor and preview | Complete with automated responsive and accessibility evidence; human review open |
| E7 - Content library and export | Complete |
| E8 - Security, quality and acceptance | Conditional for controlled local demonstration; production UAT and environment gates open |
| E9 - Packaging, documentation and closure | Technical closure package complete; NFA-91 merge and owner review pending |

## 6. Delivered functionality

An authenticated user can register, sign in, resolve or browse a synthetic approved article, review source information, configure a draft, receive mocked or configured provider output, edit the draft, generate and select illustration versions, preview the combined content, save it, reopen versions, copy text, download an owner-authorised image and delete the saved draft.

The application does not publish to LinkedIn automatically. It maintains a human-review boundary.

## 7. Technical achievements

- Built a typed full-stack monorepo using Python, FastAPI, TypeScript, Next.js, React and PostgreSQL.
- Created a normalised relational model with migrations, constraints, ownership and version history.
- Isolated article, text-generation, image-generation and storage providers behind testable interfaces.
- Implemented secure session cookies, CSRF controls, Argon2id password hashing and generic private-resource responses.
- Preserved article provenance, rights metadata and fail-closed provider selection.
- Added grounded prompting, output validation, image-safety controls, human editing and no automatic publishing.
- Implemented private image validation, persistence, regeneration, delivery and cleanup behaviour.
- Established deterministic unit, integration, browser, accessibility, security and recovery testing.
- Created reproducible Docker packaging, CI quality gates and extensive technical documentation.
- Used Jira, Git branches, pull requests, evidence comments and retrospectives to practise a professional project-management workflow.

## 8. Testing and quality results

The final NFA-90 handover verification recorded:

- 489 deterministic backend tests passed;
- 16 explicitly safety-gated backend tests skipped;
- 1 optional live-provider test deselected;
- 173 frontend tests passed across 36 files;
- 13 Playwright Chromium scenarios passed;
- the Next.js production build passed;
- Python and production npm dependency audits passed;
- Docker build, migration `20261102_0015`, seed, health, restart, stop/start and database persistence checks passed;
- secret scanning and documentation contracts passed; and
- the isolated candidate-checkout verification passed.

These results use synthetic data and mocked providers. They are not measurements of a public deployment.

The release defect register contains no confirmed open Critical or High software defect in the reviewed automated baseline. Human UAT has not run, so participant-discovered defects cannot be ruled out.

## 9. Release-readiness and demonstration review

The NFA-82 review recorded **Conditional Go** for a controlled local synthetic-data demonstration and **No-Go** for public release. That remains the closure boundary.

The demonstration package contains a repeatable mock launcher, synthetic user, synthetic approved URL, presenter script, fallback plan, screenshots and a complete automated browser journey. A human narrated rehearsal and project-owner demonstration acceptance remain manual items.

## 10. Security, privacy and source-rights status

- Live CNN integration remains No-Go because no written authorisation or licensed provider agreement exists.
- Fixture mode is the only implemented source mode and rejects unauthorised live access.
- No CNN article text, photograph or brand asset is required by routine tests or demonstrations.
- Real keys remain outside source control and provider calls remain backend-only.
- Passwords are hashed, sessions are protected, private records are owner-scoped and state-changing requests require CSRF proof.
- AI output remains subject to grounding, safety checks and human review.
- Production security, privacy, storage, backup, restore, monitoring and incident controls remain release gates.

## 11. Known limitations and remaining risks

The detailed [outstanding-work register](outstanding-work-register.md) transfers rather than hides the remaining work. The highest risks are unauthorised source use, public deployment without operational controls, missing human UAT, missing representative assistive-technology review, and production data or storage controls.

There is no software licence. The repository must not be treated as granting permission to reuse third-party content or the source code beyond applicable law and repository access.

## 12. Project achievements

- Converted a project idea into a structured 10-Epic Jira backlog and 82 merged pull requests before closure.
- Delivered the complete controlled synthetic article-to-content lifecycle.
- Maintained a No-Go decision rather than substituting unauthorised scraping.
- Built extensive evidence alongside the implementation instead of leaving testing and documentation until the end.
- Developed practical experience with Git, GitHub, Jira, Docker, PostgreSQL, FastAPI, Next.js, CI, secure authentication, AI service boundaries and technical writing.

## 13. Engineering challenges

The project encountered real challenges in source authorisation, translating a large plan into safe increments, understanding local services and environment isolation, database credential persistence, authentication and ownership, evolving API contracts, Docker startup order, deterministic external-service testing and browser-test process isolation.

These challenges and their responses are documented in the [retrospective](retrospective.md).

## 14. Lessons learned

- Technical access is not legal permission.
- A database, backend and frontend are separate services with separate responsibilities and startup dependencies.
- A branch should normally be created before making a focused change.
- Commit messages, pull requests and Jira evidence serve different traceability purposes.
- Environment files and virtual environments are local tools and must not be committed.
- Deterministic provider fakes are essential for reliable and affordable CI.
- Automated tests must preserve useful assertions when contracts evolve.
- A project can be successfully closed with explicit limitations without pretending it is production-ready.

## 15. Future improvements

Priority future work is listed in the outstanding register. Important opportunities include an authorised provider, human UAT, production storage and operations, password reset, approved live-model evaluation, more advanced search and generation evaluation, more illustration styles and deployment to an approved environment.

These are future possibilities, not delivered features.

## 16. Final project decision

The final technical closure decision is:

> **Project completed with documented limitations.**

This means the agreed controlled local portfolio application, technical evidence, documentation and handover are complete enough to close the active delivery project after NFA-91 review and merge.

It does not mean:

- public production release is approved;
- live CNN access is authorised;
- human UAT is complete;
- every original production-oriented task is Done; or
- outstanding security, accessibility, storage and operations work can be discarded.

The outstanding work remains recorded for any future phase.

## 17. Jira closure actions

1. Review NFA-91 and its linked package.
2. Commit, push, review and merge the NFA-91 branch.
3. Add the pull request, implementation commit, merge commit and closure-package links to Jira.
4. Move NFA-91 to Done only after acceptance.
5. Apply the Epic status recommendations in `epic-review.md`.
6. Keep incomplete release gates open or create explicit follow-up issues.
7. Do not mark live CNN, public production, UAT or representative screen-reader work complete.
8. Archive the active project only after Jira accurately reflects those boundaries.

## 18. Approval record

| Role | Name | Decision | Date |
| --- | --- | --- | --- |
| Technical closure review | NewsFlow AI closure package | Project completed with documented limitations | 9 November 2026 |
| Project owner | Mashood Ogunbiyi | Pending review of NFA-91 | Pending |

Project-owner approval must be recorded after review. The technical decision above is evidence-based but does not invent owner sign-off.

