# NFA-5 - CNN Authorisation Record

## 1. Document control

| Field | Value |
|---|---|
| Project | NewsFlow AI |
| Jira issue | NFA-5 |
| Project-plan task | T0.3 - Obtain and record authorisation |
| Version | 1.0 candidate |
| Status | Authorisation absence documented - ready for review |
| Decision date | 11 October 2026 |
| Decision owner | Mashood Ogunbiyi |
| Related research | [NFA-4 - CNN Data Access Research](NFA-4.md) |
| Requirements baseline | [NFA-3 - Baseline Requirements and Acceptance Criteria](NFA-3.md) |
| Repository path | `docs/jira/NFA-5.md` |

### Revision history

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 candidate | 11 October 2026 | Recorded the absence of written live-source authorisation, the resulting restrictions, evidence status, and fixture-only decision | Mashood Ogunbiyi |

## 2. Purpose

This document records whether NewsFlow AI currently has permission to access and use CNN news information. It converts the NFA-4 research into an explicit authorisation decision that the project can enforce.

This is a project compliance record, not legal advice. It does not replace a licence or written permission from CNN or an authorised provider.

## 3. Authorisation decision

| Decision field | Recorded decision |
|---|---|
| Decision ID | `NFA-SRC-AUTH-001` |
| Live CNN authorisation | Not obtained |
| Approved live access method | None |
| Approved live CNN fields | None |
| OpenAI processing of live CNN content | Not authorised |
| Creation of LinkedIn drafts from live CNN content | Not authorised |
| CNN image, video, logo, or branding use | Not authorised and excluded from the MVP |
| Live ingestion decision | No-go |
| Development decision | Go with original synthetic fixtures only |
| Review trigger | Written permission or a suitable signed provider agreement is received |

### Decision statement

As of 11 October 2026, NewsFlow AI does not hold written permission, a signed content licence, licensed-provider entitlement, or access credentials that authorise its intended use of CNN news information.

The application must therefore make no live CNN content request and must not retrieve, store, send to OpenAI, transform, or publish content obtained from a live CNN source. The live source must remain disabled.

This is not a permanent rejection of CNN integration. It is the safe project decision until suitable written authorisation is obtained and reviewed.

## 4. Permission requirements identified

NFA-4 established that public availability is not sufficient permission for NewsFlow AI's intended use. Any future authorisation must identify all of the following in writing:

| Requirement | Required confirmation | Current result |
|---|---|---|
| Rights provider | CNN or a provider authorised to license the specific CNN content | Not confirmed |
| Product and access method | Named API, feed, MRSS, FTP service, or other controlled delivery method | Not confirmed |
| Content coverage | Exact CNN publications, territories, languages, categories, and date ranges | Not confirmed |
| Permitted fields | Exact metadata, summary, article text, byline, quotation, and media fields | No live fields approved |
| Automated retrieval | Permission to retrieve content programmatically at the required frequency and volume | Not confirmed |
| Storage and caching | Which fields may be stored, where, and for how long | Not confirmed |
| Corrections and deletion | Duties when content is corrected, withdrawn, expired, or deleted | Not confirmed |
| OpenAI processing | Permission to transmit licensed content to the OpenAI API as a third-party processor | Not confirmed |
| Transformation | Permission to generate an original summary, commentary, or LinkedIn draft | Not confirmed |
| External publication | Permission for users to publish generated output on LinkedIn | Not confirmed |
| Attribution | Required source link, byline, copyright notice, provider wording, and branding rules | Not confirmed |
| User and environment scope | Permitted users and development, test, portfolio, demonstration, and production environments | Not confirmed |
| Operational controls | Rate limits, concurrency, security, audit, reporting, and service-level conditions | Not confirmed |
| Commercial terms | Fees, renewal, termination, expiry, and post-termination deletion duties | Not confirmed |

The authorisation is incomplete if any required item is missing or ambiguous. Silence, a public webpage, technical accessibility, or a general-purpose API subscription must not be treated as permission.

## 5. Evidence review

### 5.1 Evidence found

| Evidence ID | Evidence | Location | What it establishes |
|---|---|---|---|
| NFA5-E001 | Approved requirements baseline | [NFA-3.md](NFA-3.md) | Live ingestion is blocked until an authorised access route is documented |
| NFA5-E002 | CNN data-access investigation | [NFA-4.md](NFA-4.md) | Direct licensing routes exist, but no public self-service CNN article API or express permission for this use was identified |
| NFA5-E003 | NFA-4 GitHub pull request | [Pull request 3](https://github.com/mashoodogunbiyi/newsflow-ai/pull/3) | Preserves the reviewed research change and repository history |
| NFA5-E004 | CNN International Commercial content sales | [Official content-sales page](https://commercial.cnn.com/our-solutions/content-sales/) | CNN offers content licensing and CNN Newsource syndication through commercial arrangements |
| NFA5-E005 | CNN International Commercial terms | [Official terms page](https://commercial.cnn.com/terms-of-use/) | CNN commercial-site material is protected and reuse is restricted without appropriate permission |
| NFA5-E006 | CNN Newsource licence behaviour | [Official Newsource FAQ](https://newsource-cdn-static.ns.cnn.com/prd/help/content/faq.pdf) | Content and media visibility depend on the licences held by the customer |
| NFA5-E007 | Repository evidence check | This document, Section 5.2 | No project-specific authorisation document or provider agreement exists in the repository |

### 5.2 Evidence not found or not supplied

The following were not found in the project repository and were not supplied for this decision:

- A written response from CNN approving the NewsFlow AI use case.
- A signed CNN content licence or CNN Newsource agreement.
- A signed agreement with a third-party provider covering the required CNN article content.
- Written permission to send CNN content to the OpenAI API.
- Written permission to generate and externally publish LinkedIn content from CNN source material.
- A provider schedule listing permitted fields, retention, attribution, territories, and deletion duties.
- Valid access credentials tied to an approved agreement.

This absence is the basis for the no-go decision. It is not evidence that CNN will never grant permission.

## 6. Permitted use under the current decision

The following work is permitted now:

- Use original synthetic article fixtures for development and automated testing.
- Design interfaces and schemas that could later support a licensed provider.
- Build the application shell, authentication, persistence, OpenAI integration, and user workflow against fakes or synthetic data.
- Store synthetic provider IDs, headlines, summaries, dates, categories, URLs, and rights metadata that do not reproduce or imitate a real CNN article.
- Send original synthetic fixture content to the OpenAI API during controlled development and testing.
- Keep public links to CNN licensing and terms pages in project documentation as research references.

Synthetic fixtures must be clearly labelled and must not be presented as live CNN reporting.

## 7. Prohibited use under the current decision

Until the decision is replaced by an approved written authorisation, NewsFlow AI must not:

- Call a live CNN article API, feed, RSS endpoint, MRSS endpoint, website, or private service.
- Scrape CNN pages or use a custom feed that monitors or extracts CNN pages.
- Bypass a login, subscription, paywall, robot control, rate limit, or other access restriction.
- Retrieve or store live CNN headlines, descriptions, article text, bylines, quotations, images, captions, video, or other article fields for the application.
- Send live CNN content or provider-supplied CNN content to the OpenAI API.
- Generate a LinkedIn draft from live CNN content through the application.
- Copy, embed, regenerate, or use CNN photographs, videos, logos, trade dress, or branding.
- Treat NewsAPI, Google News, a public RSS endpoint, or another aggregator as proof of CNN reuse permission.
- Enable a live source by configuration, feature flag, code change, or manual workaround.

## 8. Enforced project controls

The following controls are required while authorisation is absent:

- The default live-source state is `disabled`.
- The only allowed development source state is `fixture`.
- No live CNN credentials may be added to local files, environment variables, CI settings, or secret storage without an approved agreement.
- Source adapters must fail closed when no approved authorisation decision is configured.
- A live sync request must return `SOURCE_NOT_AUTHORISED` and make no external content request.
- Tests must use original synthetic records and fake provider responses.
- Code review must reject any direct CNN scraping or unapproved live-source integration.
- Logs and test reports must not contain copied CNN article content.
- NFA-6 must define the fixture contract now and leave the live-provider contract blocked until a licence supplies the permitted fields and rules.

## 9. Supporting evidence storage

### Public evidence

Public research, non-confidential decisions, and source links are stored in this repository through NFA-4 and NFA-5. Git history and pull requests provide the audit trail.

### Confidential evidence

No confidential provider evidence currently exists for NewsFlow AI. If CNN or another provider later supplies correspondence, a proposal, contract, credentials, or commercial conditions:

- Store the original material in access-restricted project storage outside the public GitHub repository.
- Limit access to the project owner and approved reviewers.
- Do not commit contracts, personal contact information, confidential prices, signatures, credentials, API keys, or private provider URLs.
- Create a non-secret evidence identifier for each item.
- Record only the provider, document type, document date, reviewer, effective date, expiry date, secure storage location reference, and resulting decision in this file.
- Store credentials in an approved secret manager, separately from legal and commercial evidence.

Suggested evidence identifiers:

- `NFA5-PRIVATE-001` - provider correspondence.
- `NFA5-PRIVATE-002` - proposal or order form.
- `NFA5-PRIVATE-003` - signed agreement or licence schedule.
- `NFA5-PRIVATE-004` - technical access and security instructions.

## 10. Route to future authorisation

If live CNN integration remains a project objective, the following actions are required:

1. Send the enquiry drafted in NFA-4 to CNN International Commercial or CNN Newsource.
2. Optionally request a separate proposal from LexisNexis Nexis Data+.
3. Obtain a written response covering every requirement in Section 4.
4. Store private evidence securely using Section 9.
5. Review the agreement and record the exact permitted fields and operations.
6. Revise this document with a new version rather than deleting the no-authorisation history.
7. Obtain project-owner approval for the new decision.
8. Complete the NFA-6 live-source data contract before enabling an adapter.
9. Record the final go or no-go architecture decision under NFA-8.

Provider contact or form submission is an external communication and has not been performed as part of this document.

## 11. Reassessment and change control

This decision must be reassessed when any of the following occurs:

- CNN or an authorised provider supplies written permission.
- A proposed provider, product, dataset, or use case changes.
- The project adds a new field, media type, territory, environment, user group, or publication channel.
- OpenAI processing, data retention, attribution, or external-output requirements change.
- A licence expires, is terminated, or is replaced.
- Applicable provider terms or legal requirements materially change.

A future revision must record the previous decision, the new evidence, the reviewer, the effective date, and the exact permissions granted. Authorisation must never be inferred from an earlier or different product licence.

## 12. Acceptance-criteria traceability

| Acceptance criterion | Evidence in this document | Result |
|---|---|---|
| CNN's permission requirements identified | Section 4 | Complete |
| Necessary authorisation obtained and documented, or its absence recorded | Sections 3 and 5 | Complete - absence recorded |
| Permitted data usage and restrictions documented | Sections 6, 7, and 8 | Complete |
| Supporting evidence stored securely | Section 5 records public evidence; Section 9 records that no confidential evidence exists and defines secure handling for future evidence | Complete for the current no-authorisation decision |

## 13. Review and Jira decision

NFA-5's authorisation record is complete and ready for project-owner review. The task can be accepted under the acceptance-criteria route that permits the absence of authorisation to be recorded.

After approval:

1. Commit and merge this document through the normal GitHub workflow.
2. Add the final document, pull-request, and commit links to NFA-5 in Jira.
3. Move NFA-5 to Done.
4. Keep live CNN access disabled.
5. Start NFA-6 - Define the source data contract - using a fixture-first contract with all live-provider fields marked as blocked.
6. Reopen or revise NFA-5 if written provider evidence is later obtained.

The practical project state is therefore:

- Research complete.
- Authorisation absent and recorded.
- Live CNN ingestion blocked.
- Synthetic-fixture development permitted.
