# NFA-8 - Architecture Decision Record for Live CNN Integration

## 1. Document control

| Field | Value |
|---|---|
| Project | NewsFlow AI |
| Jira issue | NFA-8 |
| Project-plan task | T0.6 - Record go/no-go ADR |
| ADR ID | ADR-001 |
| Version | 1.0 |
| Status | Approved architecture decision |
| Decision | No-Go for live CNN integration |
| Decision date | 12 October 2026 |
| Approved | 12 October 2026 |
| Owner | Mashood Ogunbiyi |
| Requirements baseline | [NFA-3 - Baseline Requirements and Acceptance Criteria](NFA-3.md) |
| Access research | [NFA-4 - CNN Data Access Research](NFA-4.md) |
| Authorisation record | [NFA-5 - CNN Authorisation Record](NFA-5.md) |
| Source data contract | [NFA-6 - Source Data Contract](NFA-6.md) |
| Risk and safeguards review | [NFA-7 - Privacy, Copyright, and AI Safety Review](NFA-7.md) |
| Repository path | `docs/jira/NFA-8.md` |

### Revision history

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 12 October 2026 | Recorded and approved the No-Go decision for live CNN integration and the Go decision for fixture-based development | Mashood Ogunbiyi |

### Approval

Mashood Ogunbiyi has reviewed and approved this Architecture Decision Record as the project and document owner.

This approval accepts the No-Go decision for live CNN integration and permits continued development with original synthetic fixtures. It does not authorise retrieval, storage, OpenAI processing, transformation, or publication of live CNN content.

| Role | Name | Decision | Date |
|---|---|---|---|
| Project and document owner | Mashood Ogunbiyi | Approved | 12 October 2026 |
| Technical reviewer | Mashood Ogunbiyi | Self-reviewed and accepted for the current solo phase | 12 October 2026 |

## 2. ADR summary

| ADR field | Recorded value |
|---|---|
| Decision question | Can NewsFlow AI proceed with live CNN integration now? |
| Live CNN decision | No-Go |
| Fixture-based development decision | Go |
| Public release using live CNN data | No-Go |
| Decision status | Accepted and active |
| Primary blocker | No written authorisation or suitable signed provider agreement |
| Technical readiness | Architecture is feasible in principle, but no approved live provider, credentials, schema, or service terms exist |
| Reconsideration trigger | Suitable written authorisation and the required technical evidence are obtained |

## 3. Context

NewsFlow AI is intended to retrieve authorised CNN news information, build a bounded source fact pack, generate an original LinkedIn draft and supporting illustration with the OpenAI API, and let the user review and edit the result.

The project cannot treat technical access as permission. A live integration would retrieve and process copyright-protected news information, may process personal information, and would send permitted source data to a third-party AI service. The project therefore requires both an authorised data-access route and technical controls that enforce the exact licence.

The preceding Jira tasks established that:

- No public, self-service CNN article API suitable for this project was identified.
- Legacy CNN RSS feeds are not an approved or technically suitable production source.
- CNN International Commercial, CNN Newsource, or a suitably licensed third-party provider may offer a compliant route, but a specific agreement is required.
- NewsFlow AI has not received written permission, a signed content licence, an approved provider entitlement, or live access credentials.
- No live CNN fields are currently approved for retrieval, storage, OpenAI processing, or derivative LinkedIn output.
- A fixture-first source contract exists and supports safe development with original synthetic data.
- Copyright, privacy, hallucination, prompt-injection, and generated-image risks require the safeguards recorded in NFA-7.

This ADR converts those findings into the architecture decision that the codebase and project workflow must enforce.

This is a project architecture and compliance decision, not legal advice. Appropriate specialist review may still be required before a live or commercial release.

## 4. Decision drivers

The decision is based on the following requirements:

- Use only an explicitly authorised method to access CNN information.
- Do not scrape CNN pages or bypass access restrictions.
- Do not assume that a public URL, RSS feed, or aggregator grants reuse rights.
- Obtain written permission for the exact fields and intended operations.
- Confirm permission to send licensed information to the OpenAI API.
- Confirm permission to generate and externally use original LinkedIn drafts.
- Enforce attribution, retention, correction, deletion, territory, and licence-expiry requirements.
- Generate only from a sufficient, bounded, permitted fact pack.
- Keep the application testable while commercial authorisation is unresolved.
- Fail closed when permission or rights metadata is missing.

## 5. Evidence reviewed

| Evidence ID | Evidence | Finding used in this decision |
|---|---|---|
| ADR1-E001 | [NFA-3 requirements baseline](NFA-3.md) | Requires authorised retrieval, source grounding, attribution, safety controls, and measurable acceptance criteria |
| ADR1-E002 | [NFA-4 access research](NFA-4.md) | Identifies direct licensing and licensed-provider routes, rejects scraping and legacy RSS, and finds no suitable public CNN API |
| ADR1-E003 | [NFA-4 pull request](https://github.com/mashoodogunbiyi/newsflow-ai/pull/3) | Preserves the reviewed access research in the repository history |
| ADR1-E004 | [NFA-5 authorisation record](NFA-5.md) | Records that live authorisation, permitted fields, AI-processing rights, credentials, and a provider agreement are absent |
| ADR1-E005 | [NFA-5 pull request](https://github.com/mashoodogunbiyi/newsflow-ai/pull/4) | Preserves the approved no-authorisation decision |
| ADR1-E006 | [NFA-6 source data contract](NFA-6.md) | Defines the approved `fixture-v1` contract and fail-closed controls while leaving live provider fields blocked |
| ADR1-E007 | [NFA-6 pull request](https://github.com/mashoodogunbiyi/newsflow-ai/pull/5) | Preserves the approved fixture-first data contract |
| ADR1-E008 | [NFA-7 risk and safeguards review](NFA-7.md) | Records the copyright, privacy, hallucination, and image-safety risks and the safeguards required before live use |
| ADR1-E009 | [NFA-7 pull request](https://github.com/mashoodogunbiyi/newsflow-ai/pull/6) | Preserves the approved risk and safeguards baseline |
| ADR1-E010 | [CNN International Commercial terms](https://commercial.cnn.com/terms-of-use/) | Supports the requirement to obtain appropriate permission before restricted reuse of protected CNN material |
| ADR1-E011 | NFA-5 secure evidence review | Confirms that no project-specific confidential authorisation or provider agreement has been supplied |

The absence of authorisation evidence is material evidence for a No-Go decision. It is not evidence that CNN will never grant permission.

## 6. Options considered

### Option A - Go with live CNN integration now

Build and enable a live adapter using a public CNN page, legacy RSS feed, aggregator, or assumed provider access.

**Advantages:**

- Could provide live data earlier.
- Could reveal provider-specific technical issues sooner.

**Disadvantages:**

- No written authorisation exists.
- No exact permitted field list or AI-processing right exists.
- No approved credentials, retention rules, attribution terms, or deletion duties exist.
- Public availability would be incorrectly treated as reuse permission.
- It would expose the project to unacceptable copyright, privacy, contractual, and reputational risk.
- It would violate the controls approved in NFA-5, NFA-6, and NFA-7.

**Result:** Rejected.

### Option B - No-Go for live CNN and Go for fixture-based development

Keep every live CNN adapter disabled and continue the application with original synthetic fixtures, provider interfaces, fake responses, and the approved safeguards.

**Advantages:**

- Complies with the current authorisation record.
- Allows repository setup, UI, authentication, database, OpenAI integration, grounding, image generation, and tests to progress.
- Preserves a clean provider boundary for a later authorised integration.
- Avoids building production behaviour around an unknown provider contract.
- Makes the live decision reversible when suitable evidence arrives.

**Disadvantages:**

- Does not prove compatibility with a real provider.
- Does not deliver live CNN information.
- Provider-specific implementation and testing remain delayed.
- Some schema, rate-limit, correction, and operational details remain unknown.

**Result:** Accepted.

### Option C - Stop the entire project

Pause all engineering until a CNN agreement is obtained.

**Advantages:**

- Avoids spending effort on assumptions about a future live provider.

**Disadvantages:**

- Blocks substantial work that does not require live CNN data.
- Prevents the project from demonstrating secure architecture, AI grounding, workflow design, and project-management practice.
- Is unnecessary because original synthetic fixtures provide an approved development path.

**Result:** Rejected.

### Option D - Record the live decision as Pending

Leave the architecture decision undecided until a provider responds.

**Advantages:**

- Reflects that authorisation could be obtained later.

**Disadvantages:**

- Gives implementation teams an ambiguous current instruction.
- Does not clearly prevent live integration while permission is absent.
- A reversible No-Go decision provides a safer and clearer rule.

**Result:** Rejected. The current decision is No-Go, not Pending.

## 7. Decision

### 7.1 Live CNN integration

The architecture decision is **No-Go** for live CNN integration.

NewsFlow AI must not connect to, retrieve from, scrape, store content from, or otherwise integrate with a live CNN source. It must not send live CNN information to the OpenAI API or generate LinkedIn posts or images from live CNN information.

This decision applies to development, test, demonstration, staging, and production environments. A hidden feature flag, local-only configuration, manual workaround, or experimental branch does not bypass the decision.

### 7.2 Fixture-based development

The architecture decision is **Go** for development using the approved `fixture-v1` source contract and original synthetic content.

The project may build:

- A source-provider interface and disabled live-provider boundary.
- A synthetic fixture provider and provider fakes.
- The web application and FastAPI backend.
- Authentication, authorisation, database, storage, and audit controls.
- OpenAI text and image generation using original synthetic facts.
- Grounding, moderation, validation, review, export, and automated tests.

Synthetic fixtures must not copy or closely imitate CNN articles and must be clearly identified as synthetic.

## 8. Technical feasibility assessment

| Area | Assessment | Current decision |
|---|---|---|
| Provider integration pattern | Feasible through a source-provider interface and normalised contract | Build the interface against fixtures |
| Approved live endpoint | None | Block live network requests |
| Provider credentials | None | Do not create or store live CNN credentials |
| Live provider schema | Unknown until a provider agreement and current specification exist | Do not hard-code assumed CNN fields |
| Data normalisation | Feasible under NFA-6 | Implement and test with `fixture-v1` |
| OpenAI text generation | Feasible with bounded synthetic fact packs | Continue under NFA-7 safeguards |
| OpenAI image generation | Feasible for original conceptual illustrations | Continue under NFA-7 safeguards |
| Attribution and rights enforcement | Architecturally feasible, but live values depend on the licence | Keep live profile disabled |
| Corrections, withdrawal, and expiry | Feasible in principle, but provider rules are unknown | Design extension points and defer live behaviour |
| Rate limits and service reliability | Unknown | Reassess with provider documentation and credentials |

The technical architecture is feasible in principle. Technical feasibility does not remove the authorisation blocker and is therefore insufficient for a live Go decision.

## 9. Technical and legal risk assessment

| Risk | Type | Rating | Decision response |
|---|---|---|---|
| Unauthorised retrieval or reuse of CNN information | Legal and contractual | Critical | No live adapter or live request |
| Sending content to OpenAI without permission | Legal, privacy, and contractual | Critical | Synthetic fixture data only |
| Building against an assumed or obsolete feed schema | Technical | High | Provider interface plus fixture contract; wait for current specification |
| Missing attribution, retention, correction, or deletion rules | Legal and technical | High | No live storage or output until exact rules are configured and tested |
| Hallucinated or distorted claims | Product and reputational | Critical | Bounded fact packs, claim mapping, refusal, moderation, and human review |
| Deceptive or rights-infringing generated images | Safety, copyright, and reputational | Critical | Original conceptual images, no CNN assets or branding, disclosure, and review |
| Licence expiry or provider change | Operational and contractual | High | Rights metadata, expiry controls, monitoring, and fail-closed shutdown before live use |
| Fixture behaviour differs from the selected provider | Technical | Medium | Provider contract tests and controlled live sandbox testing after authorisation |

The risks are acceptable for fixture-based development when the NFA-6 and NFA-7 controls are enforced. They are not acceptable for live CNN integration under the current evidence.

## 10. Architecture consequences and controls

The accepted decision has the following consequences:

- The default source mode is `disabled`.
- `fixture-v1` is the only approved active source profile.
- No application code may make a live CNN content request.
- The source-provider interface must separate fixture and future live implementations.
- A live implementation must not be selected through an environment variable unless an approved provider profile exists.
- A live request without approval must fail with `SOURCE_NOT_AUTHORISED` before any external network request.
- Tests, demos, screenshots, and portfolio examples must use original synthetic records.
- The OpenAI API may receive approved synthetic facts, but not live CNN content.
- The application must keep manual review and must not automatically publish to LinkedIn.
- Confidential provider correspondence, contracts, commercial terms, and credentials must remain outside the public repository.

This ADR deliberately delays the live adapter. It does not delay fixture-backed product and engineering work.

## 11. Conditions required to replace the No-Go decision

A later ADR may replace this decision with Go only when all of the following are complete:

1. CNN or an authorised provider supplies suitable written permission or a signed agreement.
2. The agreement identifies the exact product, content coverage, permitted fields, users, territories, and environments.
3. Automated retrieval, storage, caching, OpenAI processing, transformation, external LinkedIn use, and attribution rights are expressly confirmed.
4. Retention, correction, withdrawal, deletion, expiry, rate-limit, security, and audit obligations are documented.
5. Confidential evidence is stored securely and a non-secret evidence reference is added to NFA-5.
6. NFA-5 is revised and approved with the new authorisation decision.
7. NFA-6 is revised with a provider-specific live data contract.
8. NFA-7 is reassessed for the actual provider, fields, licence, and data flow.
9. DPIA screening and any required privacy assessment are complete.
10. Current provider documentation, credentials, sandbox access, and technical feasibility are verified.
11. Contract, security, grounding, attribution, deletion, failure, and licence-expiry tests pass.
12. A new ADR records the replacement Go decision and its evidence.

No single condition is sufficient on its own.

## 12. Next steps

### Immediate project actions

1. Commit and merge this ADR and the README update through the normal GitHub workflow.
2. Add the final document, pull-request, implementation-commit, and merge-commit URLs to NFA-8 in Jira.
3. Move NFA-8 to Done after the evidence is recorded.
4. Start NFA-9 - Create the initial risk register.

### Approved engineering actions

1. Initialise the repository structure.
2. Define the source-provider interface.
3. Create original test fixtures and provider fakes that implement NFA-6.
4. Build the product workflow against the fixture provider.
5. Implement the NFA-7 safeguards and automated tests.
6. Keep live CNN integration disabled.

### External authorisation actions

1. Contact CNN International Commercial or CNN Newsource using the enquiry prepared in NFA-4.
2. Optionally investigate a suitable licensed third-party provider.
3. Store any confidential response securely outside the public repository.
4. Reopen NFA-5 and this ADR only when material new evidence exists.

External provider contact has not been performed as part of this ADR.

## 13. Reassessment and change control

Review this decision when:

- Written permission, a provider proposal, or a signed agreement is received.
- The intended source, fields, use case, AI provider, output channel, territory, or user group changes.
- CNN or provider terms materially change.
- A technical proof shows that the selected provider cannot satisfy the approved contract.
- A safety, privacy, copyright, or security incident changes the risk assessment.

Do not edit the historical decision out of the repository. Record the reason, new evidence, approver, effective date, and superseding ADR when the decision changes.

## 14. Acceptance-criteria traceability

| Acceptance criterion | Evidence in this document | Result |
|---|---|---|
| CNN access decision documented | Sections 2 and 7 | Complete - No-Go for live integration |
| Supporting evidence recorded | Section 5 | Complete |
| Technical and legal risks assessed | Sections 8 and 9 | Complete |
| Decision recorded as Go, No-Go, or Pending | Sections 2 and 7 | Complete - No-Go for live CNN and Go for fixtures |
| Next steps documented | Sections 11 and 12 | Complete |

## 15. Review and Jira decision

NFA-8 is complete and approved by Mashood Ogunbiyi. All five Jira acceptance criteria are satisfied by this ADR.

The final recorded decision is:

- **No-Go** for live CNN integration.
- **Go** for continued development with original synthetic fixtures.
- **No-Go** for public release using live CNN information until this ADR is formally superseded.

After the GitHub evidence is recorded in Jira, NFA-8 can be moved to Done and work can continue with NFA-9.
