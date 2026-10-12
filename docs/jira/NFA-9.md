# NFA-9 - Initial Project Risk Register

## 1. Document control

| Field | Value |
|---|---|
| Project | NewsFlow AI |
| Jira issue | NFA-9 |
| Project-plan task | T0.7 - Create the initial risk register |
| Version | 1.0 |
| Status | Approved initial risk register |
| Baseline date | 12 October 2026 |
| Approved | 12 October 2026 |
| Next scheduled review | 19 October 2026 |
| Risk coordinator | Mashood Ogunbiyi |
| Requirements baseline | [NFA-3 - Baseline Requirements and Acceptance Criteria](NFA-3.md) |
| Authorisation record | [NFA-5 - CNN Authorisation Record](NFA-5.md) |
| Risk and safeguards review | [NFA-7 - Privacy, Copyright, and AI Safety Review](NFA-7.md) |
| Architecture decision | [NFA-8 - Live CNN Integration ADR](NFA-8.md) |
| Repository path | `docs/jira/NFA-9.md` |

### Revision history

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 12 October 2026 | Identified, assessed, assigned, and approved the initial development, delivery, security, cost, AI, and legal risks | Mashood Ogunbiyi |

### Approval

Mashood Ogunbiyi has reviewed and approved this initial risk register as the project and document owner. The register establishes the current risk baseline and the controls that must guide planning and implementation.

Approval of this register does not accept uncontrolled critical risks and does not authorise live CNN integration. NFA-8 remains the controlling No-Go decision for live CNN integration.

| Role | Name | Decision | Date |
|---|---|---|---|
| Project and document owner | Mashood Ogunbiyi | Approved | 12 October 2026 |
| Risk coordinator | Mashood Ogunbiyi | Accepted ownership for the current solo phase | 12 October 2026 |
| Technical reviewer | Mashood Ogunbiyi | Self-reviewed and accepted for the current solo phase | 12 October 2026 |

## 2. Purpose and scope

This document records the main uncertainties that could affect NewsFlow AI's development, delivery, security, operating cost, AI quality, legal compliance, and reputation. It assigns responsibility, defines early warning indicators, and records preventive and contingency actions.

The register is a living project-management document. A risk describes an uncertain event that may occur. A problem that has already occurred is tracked as an issue or blocker, while its remaining uncertainty can continue to appear in this register.

This document is not legal, financial, or data-protection advice. Specialist review may be required before a live or commercial release.

## 3. Risk-management method

### 3.1 Likelihood scale

| Score | Label | Working definition |
|---:|---|---|
| 1 | Rare | Not expected, but possible in exceptional circumstances |
| 2 | Unlikely | Could occur, but there is limited evidence that it will |
| 3 | Possible | A realistic event during the project |
| 4 | Likely | Expected to occur unless actively controlled |
| 5 | Almost certain | Already materialising or expected in most plausible conditions |

### 3.2 Impact scale

| Score | Label | Working definition |
|---:|---|---|
| 1 | Negligible | Minor inconvenience with no meaningful delivery or user effect |
| 2 | Minor | Small rework, limited delay, or low contained cost |
| 3 | Moderate | Sprint disruption, noticeable cost, or limited user impact |
| 4 | Major | Material schedule, scope, security, compliance, or reputation impact |
| 5 | Severe | Release blocked, major breach or claim, serious user harm, or project failure |

### 3.3 Rating and response rules

Risk score equals likelihood multiplied by impact.

| Score | Rating | Required response |
|---:|---|---|
| 1 to 4 | Low | Accept with monitoring or apply a proportionate control |
| 5 to 9 | Medium | Assign an owner, implement mitigation, and review regularly |
| 10 to 15 | High | Prioritise treatment, track in sprint planning, and escalate deterioration |
| 16 to 25 | Critical | Stop or block the affected activity until exposure is reduced |

The initial rating assumes no planned mitigation. The residual rating estimates exposure after every listed control is implemented and verified. If a control is absent or fails, use the initial rating.

### 3.4 Risk status

| Status | Meaning |
|---|---|
| Open | The risk is active and requires treatment or monitoring |
| Active blocker | The event is currently preventing a defined activity |
| Monitoring | Controls are operating and indicators are being watched |
| Escalated | The risk exceeds tolerance and requires a project decision |
| Closed | The risk no longer applies or has become a separately managed issue |

## 4. Ownership model

Mashood Ogunbiyi is the named accountable owner for the current solo phase. The responsibility label indicates which project viewpoint must manage each risk.

| Owner code | Named owner | Responsibility label | Responsibility |
|---|---|---|---|
| O-01 | Mashood Ogunbiyi | Project and Product Owner | Scope, schedule, budget, external dependencies, provider decisions, and release acceptance |
| O-02 | Mashood Ogunbiyi | Technical Owner | Architecture, implementation, reliability, data, infrastructure, dependencies, and technical quality |
| O-03 | Mashood Ogunbiyi | AI and Safety Owner | Grounding, model behaviour, moderation, image safety, evaluation, and human-review controls |
| O-04 | Mashood Ogunbiyi | Security and Privacy Owner | Authentication, authorisation, secrets, personal information, logging, incidents, and privacy controls |

When another person accepts one of these responsibilities, the register must be updated with that person's name, acceptance date, and handover notes. A team name or unassigned role must not replace a named accountable owner.

## 5. Risk register summary

| ID | Category | Risk event | L | I | Initial score | Rating | Named owner | Status | Next review |
|---|---|---|---:|---:|---:|---|---|---|---|
| R-001 | Legal and delivery | A suitable CNN licence or authorised access route is not obtained | 5 | 5 | 25 | Critical | Mashood Ogunbiyi - O-01 | Active blocker for live integration | 19 October 2026 |
| R-002 | Product and legal | Permitted provider fields are too limited to ground reliable posts | 3 | 5 | 15 | High | Mashood Ogunbiyi - O-01 | Open | 19 October 2026 |
| R-003 | Cost and delivery | Provider licensing cost or negotiation time exceeds project limits | 4 | 4 | 16 | Critical | Mashood Ogunbiyi - O-01 | Open | 19 October 2026 |
| R-004 | Delivery | MVP scope exceeds available time or solo capacity | 4 | 4 | 16 | Critical | Mashood Ogunbiyi - O-01 | Open | 19 October 2026 |
| R-005 | People and delivery | Key-person dependency or weak handover delays the project | 4 | 4 | 16 | Critical | Mashood Ogunbiyi - O-01 | Open | 19 October 2026 |
| R-006 | Development | A future provider is incompatible with the assumed interface or data contract | 3 | 4 | 12 | High | Mashood Ogunbiyi - O-02 | Open | 19 October 2026 |
| R-007 | AI quality | Generated text contains unsupported or distorted factual claims | 4 | 5 | 20 | Critical | Mashood Ogunbiyi - O-03 | Open | 19 October 2026 |
| R-008 | Copyright | Source text, images, branding, or other protected material is used beyond permission | 3 | 5 | 15 | High | Mashood Ogunbiyi - O-01 | Open | 19 October 2026 |
| R-009 | Privacy | Unnecessary, sensitive, or private personal information is collected, exposed, or sent to a provider | 3 | 5 | 15 | High | Mashood Ogunbiyi - O-04 | Open | 19 October 2026 |
| R-010 | Security | Broken object-level authorisation exposes another user's posts, images, or history | 3 | 5 | 15 | High | Mashood Ogunbiyi - O-04 | Open | 19 October 2026 |
| R-011 | Security | API keys, credentials, confidential evidence, or sensitive logs are exposed | 3 | 5 | 15 | High | Mashood Ogunbiyi - O-04 | Open | 19 October 2026 |
| R-012 | Security and AI | Prompt injection or malicious source content changes model behaviour | 3 | 4 | 12 | High | Mashood Ogunbiyi - O-03 | Open | 19 October 2026 |
| R-013 | AI safety and reputation | A generated image is deceptive, unsafe, biased, or rights-infringing | 3 | 5 | 15 | High | Mashood Ogunbiyi - O-03 | Open | 19 October 2026 |
| R-014 | Reliability | OpenAI, storage, database, or a future news provider is unavailable or changes behaviour | 3 | 4 | 12 | High | Mashood Ogunbiyi - O-02 | Open | 19 October 2026 |
| R-015 | Cost | OpenAI, storage, hosting, or data-provider usage exceeds the budget | 3 | 3 | 9 | Medium | Mashood Ogunbiyi - O-01 | Open | 19 October 2026 |
| R-016 | Data and delivery | Data, generated content, or project state is lost or corrupted | 3 | 4 | 12 | High | Mashood Ogunbiyi - O-02 | Open | 19 October 2026 |
| R-017 | Security and development | A vulnerable or compromised dependency affects the application or build pipeline | 3 | 4 | 12 | High | Mashood Ogunbiyi - O-02 | Open | 19 October 2026 |
| R-018 | Quality and delivery | Insufficient testing allows a serious defect into a demonstration or release | 3 | 4 | 12 | High | Mashood Ogunbiyi - O-02 | Open | 19 October 2026 |
| R-019 | Legal and governance | Provider terms, AI rules, privacy requirements, or other applicable obligations change | 3 | 5 | 15 | High | Mashood Ogunbiyi - O-01 | Open | 19 October 2026 |
| R-020 | Reputation and users | A user publishes generated content without adequate review or misunderstands it as verified journalism | 3 | 5 | 15 | High | Mashood Ogunbiyi - O-03 | Open | 19 October 2026 |

## 6. Risk treatments, triggers, and residual exposure

| ID | Response | Early warning or trigger | Preventive mitigation | Contingency or response | Residual L x I | Residual rating |
|---|---|---|---|---|---:|---|
| R-001 | Avoid and reduce | No written provider response, agreement, approved fields, or credentials | Enforce NFA-8 No-Go; use fixtures; maintain a provider boundary; prepare a precise licensing enquiry | Keep live release blocked; continue fixture product; investigate an authorised provider or formally re-scope the source | 4 x 3 = 12 | High |
| R-002 | Reduce | Licence excludes article body, sufficient facts, AI processing, or derivative output | Define source sufficiency; request exact fields and operations; prototype with thin fixtures | Refuse generation for insufficient records; negotiate more data or re-scope output to link curation | 2 x 4 = 8 | Medium |
| R-003 | Reduce and accept | Quote exceeds budget, negotiation misses a milestone, or approval becomes indefinite | Set a licensing budget and decision deadline; compare direct and licensed-provider routes; protect fixture work | Re-plan schedule, reduce live-source scope, seek funding, use an alternative authorised source, or keep a fixture-only demonstration | 3 x 3 = 9 | Medium |
| R-004 | Reduce | Sprint carry-over rises, blockers age, or the Must-have path misses milestones | Prioritise P0 work; limit work in progress; estimate and review velocity; defer polish and optional scope | Re-baseline the plan and release date; remove P2 work; never remove rights, security, privacy, or grounding controls | 3 x 3 = 9 | Medium |
| R-005 | Reduce | Knowledge exists only in chat or one person's memory; collaboration begins without onboarding | Maintain README, ADRs, Jira evidence, setup instructions, code review, and small documented changes | Pause risky changes; complete a handover checklist; assign a named replacement owner and review open decisions | 2 x 3 = 6 | Medium |
| R-006 | Reduce | Provider schema, authentication, pagination, rights metadata, or rate rules differ from assumptions | Use a source-provider interface; isolate adapters; validate against NFA-6; avoid hard-coded CNN assumptions | Revise NFA-6 and the adapter; run contract tests in an approved sandbox; delay live enablement | 2 x 3 = 6 | Medium |
| R-007 | Reduce | Evaluation finds invented facts, altered names, quotations, dates, or numbers | Use immutable numbered fact packs, structured claims, fact-ID mapping, insufficiency refusal, evaluation, and manual review | Block the output; preserve safe diagnostics; correct prompts or validation; rerun evaluations before release | 2 x 4 = 8 | Medium |
| R-008 | Avoid and reduce | Similarity checks, review, complaint, or provider notice indicates unauthorised copying | Apply field and rights allowlists; use original summaries; exclude CNN media and branding; lock attribution; monitor licence expiry | Disable affected generation; remove output; preserve evidence securely; follow takedown and provider-notification duties | 2 x 4 = 8 | Medium |
| R-009 | Reduce | Personal data appears in prompts or logs, a privacy complaint occurs, or the data flow changes | Minimise and redact data; define lawful purposes, retention, access, deletion, and provider settings; complete DPIA screening | Stop affected processing; restrict access; investigate; delete or correct data; follow incident and notification requirements | 2 x 4 = 8 | Medium |
| R-010 | Reduce | A two-user test accesses another user's object or an ownership check is missing | Enforce server-side object ownership on every read and mutation; use private object storage; automate two-user tests | Disable the affected endpoint; revoke sessions if required; investigate scope; repair and retest before restoration | 1 x 5 = 5 | Medium |
| R-011 | Avoid and reduce | Secret scanning alert, credential in client output, sensitive log, or confidential file in Git | Use backend-only environment secrets, secret management, `.gitignore`, redacted logs, least privilege, and repository scanning | Revoke and rotate immediately; remove exposure safely; inspect access logs; notify affected parties where required | 1 x 5 = 5 | Medium |
| R-012 | Reduce | Source text or user instructions attempt to override system rules, reveal data, or invoke tools | Treat source as untrusted data; separate instructions; sanitise markup; allow no source-controlled tools; red-team fixtures | Reject the request; disable affected path; update filters and prompts; rerun adversarial evaluation | 2 x 3 = 6 | Medium |
| R-013 | Avoid and reduce | Output depicts a false event or real person, copies branding, contains graphic harm, or fails moderation | Default to conceptual images; prohibit CNN assets and branding; moderate input and output; label AI images; require review | Block download; remove unsafe output; log a safe reason; update prompts and tests; do not retry blocked prompts unchanged | 2 x 4 = 8 | Medium |
| R-014 | Reduce and accept | Error rate, latency, rate limits, deprecation notice, or provider status alert crosses threshold | Isolate provider clients; use timeouts, bounded retry, idempotency, queues where useful, fakes, and health monitoring | Show recoverable status; pause affected jobs; switch to approved fallback or fixture mode; avoid duplicate charges or output | 2 x 3 = 6 | Medium |
| R-015 | Reduce | Spend reaches 50 percent early, request volume spikes, or repeated generation increases unit cost | Set budgets, alerts, per-user quotas, output limits, capped retries, idempotency, usage metrics, and model configuration | Throttle or disable costly operations; lower approved limits or model cost; investigate abnormal usage before restoring | 2 x 2 = 4 | Low |
| R-016 | Reduce | Failed migration, missing object, restore-test failure, or inconsistent database record | Use migrations, constraints, transactions, versioned source snapshots, backups, retention rules, and restore tests | Stop writes if needed; restore the verified backup; reconcile objects and records; document recovery and data loss | 1 x 4 = 4 | Low |
| R-017 | Reduce | Dependency scanner reports a serious issue, lockfile changes unexpectedly, or build provenance fails | Pin supported versions; review updates; scan dependencies and containers; protect CI and branches; minimise packages | Remove or upgrade the dependency; disable affected release; rotate exposed credentials; rerun security and regression tests | 2 x 3 = 6 | Medium |
| R-018 | Reduce | Critical path lacks tests, failures are ignored, or release criteria are waived | Define unit, contract, integration, end-to-end, security, and AI evaluations; run CI; require acceptance evidence | Stop release; reproduce and prioritise the defect; fix or roll back; add a regression test before proceeding | 2 x 3 = 6 | Medium |
| R-019 | Reduce and avoid | Terms, provider documentation, privacy guidance, or project use changes materially | Record source and review dates; monitor before live testing and release; use change control; obtain specialist advice where needed | Pause the affected processing; reassess NFA-5 to NFA-9; revise controls and contracts; issue a superseding decision | 2 x 4 = 8 | Medium |
| R-020 | Reduce | User skips review, output is presented as CNN-authored, or harmful content is reported | Label outputs as AI-generated suggestions; show source and limitations; require manual review; prohibit automatic LinkedIn publishing | Remove or correct content where possible; support reports and takedown; suspend misuse; investigate and improve controls | 2 x 4 = 8 | Medium |

## 7. Risk tolerance and escalation

NewsFlow AI has no tolerance for:

- Live CNN retrieval without suitable written authorisation.
- Deliberate access-control bypass or scraping outside approved terms.
- Cross-user data exposure.
- Exposed production credentials or confidential provider evidence.
- Unsupported factual claims presented as verified news.
- Automatic publication of generated LinkedIn content.
- Unresolved critical security, privacy, copyright, or safety defects at release.

Any risk rated Critical must block the affected activity. A High residual risk requires a written owner decision and additional treatment before release. Medium risks may proceed with implemented controls and scheduled monitoring. Low risks may be accepted and monitored.

The owner must escalate a risk when:

- Its likelihood or impact increases.
- A mitigation is late, missing, or ineffective.
- The event occurs and becomes an issue.
- A residual score remains High or Critical near a release gate.
- The risk requires new funding, authority, specialist advice, or a material scope change.

## 8. Review process

The risk coordinator will review this register:

- Weekly during active development.
- During sprint planning and sprint review.
- Before enabling a new external provider or processing new data.
- Before user testing, demonstration, deployment, and release.
- After a security, privacy, AI safety, copyright, availability, or cost incident.
- When requirements, architecture, provider terms, team membership, budget, or schedule materially change.

At each review:

1. Confirm each risk owner.
2. Review triggers and new evidence.
3. Recalculate initial or residual scores when conditions change.
4. Check that mitigation actions are implemented and tested.
5. Convert occurred risks into tracked issues or incidents.
6. Add newly identified risks and link related Jira work.
7. Record the review date, decisions, and next review date in the revision history.

Risk changes that affect requirements, authorisation, the source contract, safeguards, or architecture must also update the relevant NFA document and README.

## 9. Immediate priority actions

| Priority | Action | Related risks | Owner | Target |
|---:|---|---|---|---|
| 1 | Keep the NFA-8 live CNN No-Go control in force | R-001, R-008, R-019 | Mashood Ogunbiyi - O-01 | Continuous |
| 2 | Begin engineering with the `fixture-v1` provider and original synthetic data | R-001, R-006 | Mashood Ogunbiyi - O-02 | Engineering foundation |
| 3 | Protect the P0 MVP path and establish measured sprint capacity | R-004, R-005 | Mashood Ogunbiyi - O-01 | Next sprint planning |
| 4 | Configure secret handling, automated scanning, and object-level authorisation tests | R-010, R-011, R-017 | Mashood Ogunbiyi - O-04 | Before shared or hosted testing |
| 5 | Build grounding, prompt-injection, moderation, and image-safety evaluations | R-007, R-012, R-013, R-020 | Mashood Ogunbiyi - O-03 | Before user testing |
| 6 | Set OpenAI and infrastructure usage budgets and alerts | R-015 | Mashood Ogunbiyi - O-01 | Before paid integration testing |
| 7 | Test database migration, backup, restore, and object retention | R-016, R-018 | Mashood Ogunbiyi - O-02 | Before deployment |

## 10. Acceptance-criteria traceability

| Acceptance criterion | Evidence in this document | Result |
|---|---|---|
| Major project risks identified | Sections 5 and 6 | Complete |
| Each risk assigned a likelihood and impact | Sections 3 and 5 | Complete |
| Mitigation strategies documented | Sections 6 and 9 | Complete |
| Risk owners identified | Sections 4, 5, and 9 | Complete |
| Risk register saved in project documentation | Document control and repository path | Complete |

## 11. Review and Jira decision

NFA-9 is complete and approved by Mashood Ogunbiyi. All five Jira acceptance criteria are satisfied by this initial risk register.

The register contains 20 major risks across development, delivery, security, cost, AI safety, copyright, privacy, reliability, and governance. Each risk has a likelihood, impact, rating, named owner, status, review date, trigger, mitigation, contingency, and residual rating.

The next workflow actions are:

1. Review the Markdown preview and request any required changes.
2. Commit and merge this document and the README update through the normal GitHub workflow.
3. Add the document, pull-request, implementation-commit, and merge-commit links to NFA-9 in Jira.
4. Move NFA-9 to Done after the evidence links are recorded.
5. Review Epic E0 exit criteria and close it if the Jira workflow permits.
6. Continue to the engineering foundation, beginning with T1.1 - Initialise the repository structure.
