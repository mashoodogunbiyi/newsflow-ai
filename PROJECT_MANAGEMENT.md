# NewsFlow AI — Project Management Guide

- **Recommended tool:** Jira Software
- **Method:** lightweight Scrum with two-week sprints; three-sprint team target, reforecast for solo delivery
- **Hierarchy:** Epic → Task → Subtask (only when a Task needs a smaller implementation step)

## 1. Recommendation: Jira rather than Trello

Use Jira Software for this project. Jira natively supports the hierarchy needed here: Epics group Tasks, Stories, and Bugs, and Tasks can contain Subtasks. That gives the plan stable ownership, estimates, dependencies, sprint reporting, and traceability from the brief to delivery. See Atlassian's [work type hierarchy](https://support.atlassian.com/jira-cloud-administration/docs/what-are-issue-types).

Trello is a good choice for a very small visual to-do list, but its basic model is boards, lists, cards, and checklists. Epic relationships would be a naming/label convention rather than the project's native structure. Atlassian also notes that Trello has no single native import tool, which makes a structured backlog less convenient to initialise. See [Trello cards and lists](https://support.atlassian.com/trello/docs/add-and-customize-cards-and-lists/).

If the project is strictly solo and Jira feels too heavy after the first sprint, the backlog can be exported and represented in Trello as one card per Task with an Epic label. Start in Jira because it fits the requested Epic/Task model without workarounds.

## 2. Jira project setup

Create a Jira Software project with these settings:

| Setting | Recommended value |
|---|---|
| Project name | NewsFlow AI |
| Project key | `NFAI` |
| Template | Scrum software project |
| Management style | Company-managed if available; team-managed is acceptable for a solo project |
| Sprint length | Two weeks; add sprints when capacity requires it |
| Estimation | Story points using 1, 2, 3, 5, 8 |
| Releases | `v0.1 Foundation`, `v0.2 Vertical Slice`, `v1.0 MVP` |

Create these components:

- `Web`
- `API`
- `Data`
- `Auth`
- `CNN Source`
- `OpenAI Text`
- `OpenAI Image`
- `Storage`
- `DevOps`
- `Security & QA`
- `Documentation`

Create these labels:

- `mvp`
- `compliance-gate`
- `external-dependency`
- `grounding`
- `ai-safety`
- `security`
- `accessibility`
- `tech-debt`
- `blocked-live-source`

Useful fields, if the Jira plan permits custom fields:

| Field | Type | Purpose |
|---|---|---|
| External ID | Short text | Preserve `E0`/`T0.1` plan IDs independently of Jira numbers |
| Acceptance Criteria | Paragraph | Testable completion conditions |
| Dependency | Issue link | `blocks` / `is blocked by` relationships |
| Risk | Select | None, Low, Medium, High, Critical |
| Evidence | URL/paragraph | Link to test run, ADR, screenshot, or review record |

Do not put API keys, source credentials, licensed CNN text, contracts, or personal data in Jira.

## 3. Work item rules

### Epic

An Epic is a major deliverable or control boundary. It should have:

- A measurable goal and business value.
- Entry dependencies and exit criteria.
- An owner and target release.
- Linked Tasks that can be completed and tested independently.

### Task

A Task is the primary unit of planned work. It should be small enough to complete in two or three working days, carry one clear outcome, and include acceptance criteria. Split any 8-point Task before starting it when practical.

Use a **Bug** when observed behaviour fails an agreed requirement. Use a **Spike** label on a time-boxed Task when its output is evidence or a decision rather than production code. Use Subtasks only for implementation steps that genuinely need separate tracking; do not duplicate the checklist in `PROJECT_PLAN.md` as dozens of administrative Subtasks.

## 4. Workflow

Configure this workflow:

```text
Backlog -> Ready -> In Progress -> In Review -> Verification -> Done
                       |              |             |
                       +----------> Blocked <-------+
```

Status policies:

| Status | Meaning | Exit condition |
|---|---|---|
| Backlog | Valid work, not yet refined or scheduled | Priority, owner, dependencies, and rough estimate reviewed |
| Ready | Meets Definition of Ready and may be pulled | Capacity exists and dependencies are satisfied |
| In Progress | Active implementation or investigation | Work is ready for review |
| In Review | Code/design/evidence is being reviewed | Review comments resolved and checks pass |
| Verification | Integrated testing, acceptance, or compliance check | Acceptance criteria and Definition of Done pass |
| Blocked | No safe progress is possible | Blocker and owner recorded; item returns to its prior active status when cleared |
| Done | Outcome is complete and evidenced | Definition of Done met |

Set a work-in-progress limit of **two active Tasks per developer** across In Progress and In Review. A blocked item does not justify starting unlimited work; review it at every stand-up.

## 5. Definitions

### Definition of Ready

A Task may enter Ready when:

- Its outcome and acceptance criteria are clear.
- The parent Epic, owner, component, priority, and estimate are set.
- Required design/API/data decisions are resolved or explicitly part of the Task.
- External dependencies are linked and currently satisfied.
- Test approach, rights, security, privacy, and accessibility implications are understood.
- It can reasonably finish within one sprint.

### Definition of Done

A Task may enter Done when:

- Acceptance criteria are demonstrated.
- Relevant code is reviewed, merged, formatted, typed, and passing CI.
- Unit/integration/end-to-end tests are updated at the appropriate layer.
- Security, rights, privacy, accessibility, error handling, and logging are addressed.
- Documentation, OpenAPI, ADRs, migrations, and configuration examples are updated where affected.
- Evidence is linked and no hidden release-blocking defect remains.

## 6. Issue templates

### Epic template

```markdown
## Goal

## Business value

## In scope

## Out of scope

## Dependencies / entry criteria

## Exit criteria

## Risks

## Evidence / links
```

### Task template

```markdown
## Outcome

## Context

## Acceptance criteria

- [ ] Given ..., when ..., then ...
- [ ] Error/empty/unauthorised behaviour is defined and tested where relevant.
- [ ] Documentation and observability are updated where relevant.

## Technical notes

## Test approach

## Dependencies

## Rights / security / privacy / accessibility notes

## Evidence
```

### Bug template

```markdown
## Observed behaviour

## Expected behaviour

## Reproduction steps

1.
2.
3.

## Environment

## Severity and user impact

## Evidence

## Regression acceptance criteria
```

## 7. Epic backlog

Create these Epic issues first. Copy the exact `External ID` and summary so Task parent mapping stays unambiguous.

| External ID | Epic summary | Target | Exit signal |
|---|---|---|---|
| E0 | Product discovery, rights, and governance | Sprint 1 | CNN access decision and source data contract recorded |
| E1 | Engineering foundation and developer experience | Sprint 1 | Reproducible local stack and CI checks |
| E2 | Data model, authentication, and authorisation | Sprint 1 | Secure login and user ownership tests pass |
| E3 | Authorised CNN discovery and article catalogue | Sprints 1–2 | Approved sync and deduplicated catalogue work |
| E4 | Grounded LinkedIn post generation | Sprint 2 | Validated, traceable draft generation works |
| E5 | Safe AI image generation and storage | Sprint 2 | Safe generate/regenerate/download works |
| E6 | News dashboard, generator, editor, and preview | Sprints 1–2 | Responsive complete creation flow works |
| E7 | Content library and export | Sprint 3 | User-owned saved-content lifecycle works |
| E8 | Security, quality, reliability, and user acceptance | All sprints | Release gates and UAT pass |
| E9 | Packaging, documentation, demonstration, and closure | Sprint 3 | Reproducible delivery and handover complete |

## 8. Task import/copy table

The table is the execution index. Full Task descriptions and Epic exit criteria are in [PROJECT_PLAN.md](PROJECT_PLAN.md). Create Tasks in this order within each sprint, then link dependencies using Jira's `blocks` relationship.

The sections below are **candidate sprint backlogs grouped by dependency**, not commitments to complete every row in one sprint. During planning, move only the amount supported by real team capacity into the active sprint and leave the rest in the ordered backlog. The six-week target assumes parallel work by a small cross-functional team. A solo developer should use the same order but add sprints after measuring initial velocity.

Priorities: **P0** blocks the product or release, **P1** is required for the MVP, and **P2** is valuable but should yield before a P0/P1 item when time is constrained.

### Sprint 1 candidates — permission and foundation

**Sprint goal:** prove the project can be built compliantly and establish a secure, fixture-backed application foundation.

| ID | Parent | Task summary | Priority | Points | Component | Depends on |
|---|---|---|---|---:|---|---|
| T0.1 | E0 | Baseline requirements and acceptance criteria | P0 | 3 | Documentation | — |
| T0.2 | E0 | Investigate CNN access options | P0 | 5 | CNN Source | — |
| T0.3 | E0 | Obtain and record authorisation | P0 | 3 | CNN Source | T0.2; external CNN response |
| T0.4 | E0 | Define the source data contract | P0 | 3 | CNN Source | T0.2 |
| T0.5 | E0 | Complete privacy, copyright, and AI safety review | P0 | 3 | Security & QA | T0.1, T0.2 |
| T0.6 | E0 | Record go/no-go ADR | P0 | 2 | Documentation | T0.3, T0.4, T0.5 |
| T0.7 | E0 | Create the initial risk register | P1 | 2 | Documentation | T0.1 |
| T1.1 | E1 | Initialise the repository structure | P0 | 3 | DevOps | T0.1 |
| T1.2 | E1 | Document architecture decisions | P1 | 3 | Documentation | T0.1 |
| T1.3 | E1 | Establish configuration and secret handling | P0 | 3 | Security & QA | T1.1 |
| T1.4 | E1 | Add local containers | P0 | 5 | DevOps | T1.1 |
| T1.5 | E1 | Add code quality tooling | P1 | 3 | DevOps | T1.1 |
| T1.6 | E1 | Add continuous integration | P1 | 5 | DevOps | T1.5 |
| T1.7 | E1 | Create test fixtures and provider fakes | P0 | 3 | Security & QA | T0.4, T1.1 |
| T1.8 | E1 | Add health and readiness endpoints | P1 | 2 | API | T1.1 |
| T2.1 | E2 | Design the database schema | P0 | 5 | Data | T0.4, T1.2 |
| T2.2 | E2 | Implement migrations and seed data | P0 | 5 | Data | T2.1, T1.4 |
| T2.3 | E2 | Implement registration | P0 | 5 | Auth | T2.2 |
| T2.4 | E2 | Implement login, logout, and session lifecycle | P0 | 5 | Auth | T2.3 |
| T2.5 | E2 | Add frontend auth flows | P1 | 5 | Web | T2.3, T2.4 |
| T2.6 | E2 | Enforce object-level authorisation | P0 | 3 | Security & QA | T2.4 |
| T2.7 | E2 | Add account and session tests | P0 | 5 | Security & QA | T2.3–T2.6 |
| T3.1 | E3 | Define a source-provider interface | P0 | 3 | CNN Source | T0.4, T1.2 |
| T6.1 | E6 | Establish the design shell | P1 | 5 | Web | T1.1 |

The Sprint 1 list is intentionally ambitious. During planning, select only the points the team can actually complete. E0 P0 items, secure foundations, and one fixture-backed vertical slice take precedence over velocity targets.

### Sprint 2 candidates — generation vertical slice

**Sprint goal:** complete the authorised article-to-review workflow for text and images.

| ID | Parent | Task summary | Priority | Points | Component | Depends on |
|---|---|---|---|---:|---|---|
| T3.2 | E3 | Implement the authorised CNN adapter | P0 | 8 | CNN Source | T0.6 approval, T3.1 |
| T3.3 | E3 | Normalise and sanitise permitted fields | P0 | 5 | CNN Source | T3.1, T0.4 |
| T3.4 | E3 | Implement identity and deduplication | P0 | 3 | Data | T3.3 |
| T3.5 | E3 | Persist provenance and rights metadata | P0 | 3 | Data | T2.2, T3.3 |
| T3.6 | E3 | Build scheduled and manual synchronisation | P1 | 5 | CNN Source | T3.2–T3.5 |
| T3.7 | E3 | Build article REST endpoints | P0 | 5 | API | T3.4, T3.5 |
| T3.8 | E3 | Add ingestion observability | P1 | 3 | DevOps | T3.6 |
| T3.9 | E3 | Test the catalogue pipeline | P0 | 5 | Security & QA | T3.2–T3.8 |
| T4.1 | E4 | Integrate the OpenAI SDK server-side | P0 | 3 | OpenAI Text | T1.3, T1.7 |
| T4.2 | E4 | Build the fact-pack service | P0 | 5 | OpenAI Text | T0.4, T3.5 |
| T4.3 | E4 | Implement the sufficiency gate | P0 | 3 | Grounding | T4.2 |
| T4.4 | E4 | Design and version prompt templates | P0 | 5 | OpenAI Text | T4.2, T0.5 |
| T4.5 | E4 | Define the Structured Output schema | P0 | 3 | OpenAI Text | T4.4 |
| T4.6 | E4 | Implement the generation endpoint | P0 | 5 | API | T4.1–T4.5 |
| T4.7 | E4 | Validate and render responses | P0 | 5 | Grounding | T4.5, T4.6 |
| T4.8 | E4 | Add idempotency, caching, and concurrency controls | P1 | 5 | API | T4.6 |
| T4.9 | E4 | Implement text regeneration | P1 | 3 | OpenAI Text | T4.6, T4.7 |
| T4.10 | E4 | Build the grounding evaluation suite | P0 | 8 | Security & QA | T4.3–T4.7 |
| T4.11 | E4 | Add usage and reliability telemetry | P1 | 3 | DevOps | T4.6 |
| T5.1 | E5 | Build the image-prompt composer | P0 | 3 | OpenAI Image | T4.2, T0.5 |
| T5.2 | E5 | Add sensitive-news rules | P0 | 5 | OpenAI Image | T5.1, T0.5 |
| T5.3 | E5 | Integrate OpenAI image generation | P0 | 5 | OpenAI Image | T1.3, T5.1 |
| T5.4 | E5 | Validate and store output | P0 | 5 | Storage | T5.3 |
| T5.5 | E5 | Implement image regeneration | P1 | 3 | OpenAI Image | T5.3, T5.4 |
| T5.6 | E5 | Implement secure image delivery | P0 | 3 | Storage | T2.6, T5.4 |
| T5.7 | E5 | Add image tests | P0 | 5 | Security & QA | T5.1–T5.6 |
| T6.2 | E6 | Build the article dashboard | P0 | 5 | Web | T3.7, T6.1 |
| T6.3 | E6 | Add category filter and browsing state | P1 | 3 | Web | T6.2 |
| T6.4 | E6 | Build article selection and source panel | P0 | 3 | Web | T6.2 |
| T6.5 | E6 | Build generation controls | P0 | 3 | Web | T6.4, T4.6 |
| T6.6 | E6 | Build asynchronous generation states | P0 | 5 | Web | T4.6, T5.3, T6.5 |
| T6.7 | E6 | Build the content editor | P0 | 5 | Web | T4.7, T4.9 |
| T6.8 | E6 | Build the LinkedIn-style preview | P0 | 5 | Web | T6.7, T5.4 |
| T6.9 | E6 | Add image controls | P0 | 5 | Web | T5.5, T5.6, T6.8 |
| T6.10 | E6 | Complete responsive and accessibility review | P1 | 5 | Web | T6.2–T6.9 |

Split any 8-point item during refinement. If CNN approval is still pending, keep T3.2 Blocked, apply `blocked-live-source`, and run the rest of the sprint against the fake provider; G6 remains blocked.

### Sprint 3 candidates — management, assurance, and delivery

**Sprint goal:** complete saved-content management, pass release assurance, and deliver a reproducible MVP.

| ID | Parent | Task summary | Priority | Points | Component | Depends on |
|---|---|---|---|---:|---|---|
| T7.1 | E7 | Implement save and update semantics | P0 | 5 | Data | T4.9, T5.5 |
| T7.2 | E7 | Build content-library endpoints | P0 | 5 | API | T7.1, T2.6 |
| T7.3 | E7 | Build content history UI | P0 | 5 | Web | T7.2 |
| T7.4 | E7 | Add edit and regeneration history | P1 | 5 | Data | T7.1–T7.3 |
| T7.5 | E7 | Implement copy and download | P0 | 3 | Web | T5.6, T6.7 |
| T7.6 | E7 | Implement deletion and retention | P0 | 5 | Data | T7.2, T0.5 |
| T7.7 | E7 | Test ownership and lifecycle | P0 | 5 | Security & QA | T7.1–T7.6 |
| T8.1 | E8 | Threat-model the system | P0 | 5 | Security & QA | Architecture and feature designs |
| T8.2 | E8 | Apply API security controls | P0 | 5 | Security & QA | T8.1; feature APIs |
| T8.3 | E8 | Review data protection | P0 | 3 | Security & QA | T0.5; persistence features |
| T8.4 | E8 | Complete automated test layers | P0 | 8 | Security & QA | All feature Tasks |
| T8.5 | E8 | Test external-service resilience | P0 | 5 | Security & QA | E3–E5 integrations |
| T8.6 | E8 | Measure critical-path performance | P1 | 3 | DevOps | Integrated workflow |
| T8.7 | E8 | Run grounding and image-safety evaluation | P0 | 5 | Security & QA | T4.10, T5.7 |
| T8.8 | E8 | Conduct user acceptance testing | P0 | 5 | Security & QA | Feature complete candidate |
| T8.9 | E8 | Complete regression and release-candidate review | P0 | 5 | Security & QA | T8.2–T8.8 |
| T9.1 | E9 | Finalise Docker delivery | P0 | 5 | DevOps | Integrated application |
| T9.2 | E9 | Prepare environment and deployment runbook | P1 | 5 | Documentation | T9.1 |
| T9.3 | E9 | Finalise CI/CD release gates | P0 | 5 | DevOps | T8.4, T9.1 |
| T9.4 | E9 | Complete the README | P0 | 3 | Documentation | Final behaviour known |
| T9.5 | E9 | Publish API and schema documentation | P1 | 3 | Documentation | Final API known |
| T9.6 | E9 | Write the technical report | P0 | 5 | Documentation | E0–E8 evidence |
| T9.7 | E9 | Prepare and rehearse the demonstration | P0 | 3 | Documentation | Release candidate |
| T9.8 | E9 | Release and verify | P0 | 5 | DevOps | T8.9, T9.1–T9.7 |
| T9.9 | E9 | Close the project | P1 | 2 | Documentation | T9.8 |

## 9. Ceremonies and cadence

For a solo project, keep ceremonies brief but preserve the decisions they are meant to produce.

| Cadence | Activity | Output |
|---|---|---|
| Sprint start, 45 minutes | Planning | Sprint goal, selected Ready Tasks, capacity, and dependencies |
| Daily, 10 minutes | Personal stand-up | What changed, next pull, blockers, and risk update in Jira |
| Twice weekly, 20 minutes | Backlog refinement | Clear acceptance criteria, dependencies, estimates, and split large Tasks |
| Weekly, 30 minutes | Risk and access review | Updated CNN gate, AI quality, cost, security, and schedule risks |
| Sprint end, 45 minutes | Review/demo | Working increment and acceptance evidence |
| Sprint end, 30 minutes | Retrospective | One or two concrete process improvements for the next sprint |

## 10. Reporting and dashboards

Create a Jira dashboard with:

- Sprint burndown or burnup.
- Work by status and WIP age.
- Blocked Tasks and blocker age.
- Epic progress.
- Open Bugs by severity.
- Tasks labelled `compliance-gate`, `grounding`, `ai-safety`, or `security`.

Track these weekly:

| Metric | Why it matters |
|---|---|
| Sprint goal met/not met | Outcome is more useful than point completion alone |
| Cycle time and ageing WIP | Shows oversized or stuck Tasks |
| Escaped/reopened defects | Reveals weak acceptance or regression testing |
| Grounding evaluation failures | Direct measure of the core product risk |
| Provider error and retry rates | Shows external integration health |
| OpenAI usage/cost per successful generation | Supports budget and model decisions |
| CNN access gate status | Makes the release dependency impossible to overlook |

Story points measure relative complexity and uncertainty; they are not hours and should not be used to compare people.

## 11. Dependency and change control

- Link blocking issues in Jira instead of mentioning them only in comments.
- A Task with an unmet dependency cannot enter Ready.
- Any change to CNN access, permitted fields, source retention, or attribution must reopen E0 review before implementation.
- Any OpenAI model or prompt-template change must run the evaluation suite before release.
- A scope change must state its effect on acceptance criteria, schedule, security/rights, and documentation.
- Protect the core vertical slice first: authorised source → grounded post → safe image → human review → save/export.
- Never recover schedule by bypassing licensing, source sufficiency, authorisation, secret handling, or critical tests.

## 12. Manual Jira creation order

1. Create the Jira project, workflow, components, labels, releases, and fields in Section 2.
2. Create E0–E9 from Section 7 using the Epic template.
3. Create Sprint 1–3 and add their sprint goals.
4. Create the Tasks from Section 8, copying the detailed description from the matching Task in [PROJECT_PLAN.md](PROJECT_PLAN.md).
5. Set each Task's parent Epic, priority, estimate, component, sprint, and External ID.
6. Add `blocks` links from the dependency column; do not rely only on order in the backlog.
7. Apply `mvp` to P0/P1 release work and the risk-specific labels where relevant.
8. Move only Definition-of-Ready Tasks into Ready, then start Sprint 1.

Jira also supports CSV work-item import, so this manual table can be converted later if the backlog is too slow to enter by hand. Review parent links after any import before starting the sprint.

## 13. Initial decision log

| Decision | Status | Rationale |
|---|---|---|
| Use Jira Software | Accepted | Native Epic → Task → Subtask hierarchy and stronger delivery traceability than a convention-based Trello board |
| Use three two-week sprints | Proposed | Matches the brief's 4–6 week estimate while retaining explicit quality gates |
| Use synthetic fixtures before CNN approval | Accepted | Enables safe parallel development without implying permission to scrape or reuse content |
| Block live release without CNN authorisation | Accepted | Required by the brief and current published content-use restrictions |
| Keep all OpenAI calls on the backend | Accepted | Protects credentials and centralises validation, cost, retry, and audit controls |
