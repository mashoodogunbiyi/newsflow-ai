# NFA-3 — Baseline Requirements and Acceptance Criteria

## 1. Document control

| Field | Value |
|---|---|
| Project | NewsFlow AI |
| Jira issue | NFA-3 |
| Project-plan task | T0.1 - Baseline requirements and acceptance criteria |
| Version | 1.0 candidate baseline |
| Status | Ready for product-owner review |
| Created | 11 October 2026 |
| Primary source | Approved project brief: *AI-Powered CNN News-to-LinkedIn Content Generator* |
| Repository path | `docs/jira/NFA-3.md` |

### Revision history

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 candidate | 11 October 2026 | Initial functional, non-functional, scope, acceptance, and traceability baseline | Mashood Ogunbiyi |

### Approval

This document becomes the approved version 1.0 baseline when the product owner confirms that it reflects the intended MVP. Jira remains the source of truth for the issue's workflow status.

| Role | Name | Decision | Date |
|---|---|---|---|
| Product owner | To be completed | Pending review | — |
| Technical reviewer | To be completed | Pending review | — |

## 2. Purpose

This document establishes the initial requirements baseline for NewsFlow AI. It defines what the first release must do, the quality and control standards it must meet, how each major feature will be accepted, and what is deliberately excluded.

It is the deliverable for Jira issue NFA-3. Later Jira issues may produce separate research, architecture, design, implementation, and test documents. This file should change only when an approved requirement changes; ordinary task progress remains in Jira.

## 3. Product objective

NewsFlow AI will allow an authenticated user to discover recent CNN International news through an authorised access method, select an article, and use AI to create an original professional LinkedIn draft and a supporting original illustration. The user will be able to review, edit, regenerate, save, copy, and download the generated content for manual publication.

CNN is the only news source for the MVP and the factual source of truth. The application must not invent facts or use an unauthorised content-retrieval method.

## 4. Stakeholders and user roles

| Role | Interest and responsibility |
|---|---|
| Product owner | Approves scope, requirements, CNN access decision, and release acceptance |
| Application user | Discovers articles and creates, reviews, manages, and exports content |
| Developer/operator | Builds, configures, monitors, tests, and supports the application |
| Content-rights owner/provider | Defines what CNN information may be accessed, stored, processed, and attributed |
| AI provider | Supplies text and image generation through the OpenAI API |

The MVP has one application-user permission level. Administrative UI features are not required, but operational access must remain separate from normal user access.

## 5. Terms

| Term | Definition |
|---|---|
| Authorised source | A CNN feed, API, licence, or other access route whose use is documented and permitted for this project |
| Article metadata | Permitted fields such as headline, publication date, description, category, and canonical CNN URL |
| Fact pack | A bounded, numbered set of permitted source facts supplied to the text-generation service |
| Grounded claim | A factual statement supported by one or more facts in the selected article's fact pack |
| Source snapshot | The immutable version of the permitted source information used for a particular generation |
| Generation run | One text- or image-generation request and its outcome, configuration, and trace information |
| MVP | The first release covered by this baseline |

## 6. Project scope

### 6.1 In scope

- Authorised discovery and processing of recent CNN International news information.
- Article metadata, category, publication date, description when available, and original CNN URL.
- Article-body processing only where the selected access agreement explicitly permits it.
- Duplicate prevention and source provenance.
- Registration, login, logout, secure sessions, and user-specific data access.
- News dashboard, category filtering, article selection, and original-source access.
- AI-generated LinkedIn drafts with tone, length, and target-audience controls.
- Factual grounding, source-sufficiency checks, attribution, and refusal when evidence is insufficient.
- AI-generated original supporting illustrations, additional user instructions, regeneration, disclosure, and download.
- Manual editing, LinkedIn-style preview, copying, saving, retrieval, regeneration, and deletion.
- PostgreSQL persistence, generated-image storage, REST API, Docker-based local execution, testing, and technical documentation.
- Manual publication by the user after review.

### 6.2 Out of scope

- Direct publishing or scheduling through LinkedIn.
- News providers other than CNN.
- Other social-media platforms.
- Video generation.
- Subscription, billing, and payment processing.
- Social-media performance analytics.
- Reproduction of CNN photographs, branding, or substantial copyrighted article text.
- Unauthorised scraping, access-control bypass, paywall bypass, or bulk copying.
- A multi-role administration portal for the MVP.

## 7. Assumptions, dependencies, and constraints

### 7.1 Assumptions

- Users manually review generated drafts and images before publishing them.
- The OpenAI project used by the backend has access to suitable text- and image-generation capabilities.
- Local S3-compatible storage may be used during development; the delivery environment will determine the final storage service.
- Synthetic fixtures may be used for development and testing without representing them as live CNN content.

### 7.2 External dependencies

- Written confirmation of the permitted CNN access route, fields, storage, processing, retention, and attribution rules.
- CNN source availability and credentials where required.
- OpenAI API credentials, account limits, model availability, and budget.
- Database, object-storage, and deployment services.

### 7.3 Constraints

- CNN is the sole news source for this release.
- Live CNN ingestion must remain disabled until the authorisation decision is documented.
- Only permitted CNN fields may be retrieved, retained, or supplied to an AI provider.
- OpenAI and source credentials must remain on the server.
- Factual content must come from the selected source snapshot, not model memory.
- Generated content is a draft for human review, not an automatically published post.
- The complete scope is subject to delivery capacity and availability of the authorised source.

## 8. Requirement conventions

- **Must:** required for MVP acceptance.
- **Should:** expected for the MVP unless an approved scope decision defers it.
- **Could:** optional enhancement and not a release blocker.
- **Given/When/Then** statements define observable acceptance conditions.
- Requirement IDs are stable. Changed or removed requirements retain their IDs in the revision history rather than being silently renumbered.

## 9. Functional requirements

### 9.1 Authorised CNN news discovery and processing

| ID | Priority | Requirement | Measurable acceptance criteria |
|---|---|---|---|
| FR-SRC-001 | Must | The system shall obtain CNN information only through the access method approved by the product owner and rights review. | **Given** no approved live-source configuration, **when** a sync is requested, **then** no live content request is made and the operation returns `SOURCE_NOT_AUTHORISED`. **Given** an approved test configuration, the adapter requests only the documented endpoint and fields. |
| FR-SRC-002 | Must | The system shall discover recent CNN articles. | A successful sync stores all eligible items returned by the authorised source for the configured window, defaulting to the preceding seven days where the source supports date filtering. Retrieval time is recorded for every item. |
| FR-SRC-003 | Must | The system shall store permitted article metadata. | For every accepted record, headline, publication date, canonical CNN URL, provider/source identifier, category, and retrieval time are present; description is stored when supplied and permitted. Invalid required fields cause the record to be rejected and logged safely. |
| FR-SRC-004 | Must | The system shall process article-body text only when explicitly permitted. | When the rights configuration disallows body text, the stored article and AI fact pack contain no body field. When allowed, only the permitted portion is stored and its rights/retention metadata is recorded. |
| FR-SRC-005 | Must | The system shall normalise article categories. | Technology, Business, World News, and Science records map to their corresponding application categories. Unknown permitted categories map to `Other` rather than being silently discarded. |
| FR-SRC-006 | Must | The system shall sanitise permitted source content. | Stored/displayed text contains no executable scripts, event handlers, unsafe markup, or unintended navigation. Automated tests cover script, malformed HTML, and encoded-markup inputs. |
| FR-SRC-007 | Must | The system shall prevent duplicate articles. | Reprocessing the same provider ID or canonical URL creates no second active article. The database uniqueness rule and an integration test demonstrate a duplicate rate of zero for identical inputs. |
| FR-SRC-008 | Should | The system shall support controlled scheduled and manual synchronisation. | An authorised operator can start a sync; concurrent syncs do not process the same batch twice; the last start, completion, outcome, and item counts are recorded. |

### 9.2 User registration, authentication, and authorisation

| ID | Priority | Requirement | Measurable acceptance criteria |
|---|---|---|---|
| FR-AUTH-001 | Must | A visitor shall be able to register with a valid unique email address and password. | Valid details create one account and permit subsequent login. Invalid email, weak/invalid password under the configured policy, and duplicate email return validation errors without exposing stored credentials. |
| FR-AUTH-002 | Must | A registered user shall be able to log in and log out. | Correct credentials create an authenticated session; incorrect credentials do not. Logout invalidates the current session and the next protected request returns `401`. |
| FR-AUTH-003 | Must | The system shall maintain secure user sessions. | Session cookies are `HttpOnly`, use `Secure` outside local development, apply an appropriate `SameSite` setting, expire according to configuration, and are not readable by browser JavaScript. |
| FR-AUTH-004 | Must | Protected pages and API operations shall require authentication. | An unauthenticated request to every protected endpoint returns `401` or redirects to login without revealing protected data. |
| FR-AUTH-005 | Must | A user shall access only their own generated content and images. | Automated tests using two users show that cross-user read, edit, regenerate, download, and delete attempts return `403` or `404` and do not alter data. |

### 9.3 News article dashboard

| ID | Priority | Requirement | Measurable acceptance criteria |
|---|---|---|---|
| FR-DASH-001 | Must | Authenticated users shall be able to browse available articles. | Each displayed item shows headline, category, publication date, original CNN URL, and description when available, plus a Generate action. At least one fixture-backed end-to-end test verifies the display. |
| FR-DASH-002 | Must | Users shall be able to filter articles by category. | Selecting Technology, Business, World News, Science, Other, or All returns only matching active articles and preserves a clear empty state when no result exists. |
| FR-DASH-003 | Must | Users shall be able to select an article for generation. | Selecting an eligible article opens its permitted details and generation controls. An unavailable or ineligible article cannot start generation and displays the reason. |
| FR-DASH-004 | Must | Users shall be able to open the original source. | Every article detail and generated post contains a link whose destination exactly matches the stored canonical CNN URL and opens without replacing unsaved editor content. |
| FR-DASH-005 | Must | The dashboard shall communicate loading, empty, and failure states. | Tests demonstrate distinct visible states for initial loading, no articles, source unavailable, and API failure; no failure state is represented by a permanently spinning indicator. |

### 9.4 LinkedIn post generation

| ID | Priority | Requirement | Measurable acceptance criteria |
|---|---|---|---|
| FR-TEXT-001 | Must | A user shall choose a tone from Professional, Educational, Conversational, Inspirational, and Analytical. | All five values are accepted by the API and represented in the user interface; any other value is rejected with a validation error. |
| FR-TEXT-002 | Must | A user shall choose Short, Medium, or Long post length. | Generated drafts target 75–150 words for Short, 151–300 for Medium, and 301–500 for Long. Output outside the chosen band is flagged or rejected before display. These ranges may change only through an approved baseline revision. |
| FR-TEXT-003 | Must | A user shall choose General professionals, Business leaders, Technology professionals, or Entrepreneurs as the target audience. | All four values are accepted and supplied to the versioned prompt; any other value is rejected. Evaluation fixtures confirm that each audience option changes the framing without changing source facts. |
| FR-TEXT-004 | Must | The system shall generate the required post structure. | A valid draft contains an opening hook, concise news explanation, professional insight or discussion point, call to action where appropriate, three to five relevant hashtags, and source attribution with the canonical CNN URL. |
| FR-TEXT-005 | Must | Every factual claim shall be grounded in the selected source snapshot. | The structured result maps every factual claim to one or more valid fact IDs. A response containing an unknown fact ID or an unmapped factual claim fails validation and is not presented as a successful draft. |
| FR-TEXT-006 | Must | The system shall not generate unsupported content from insufficient source information. | A fact pack below the configured sufficiency threshold returns `INSUFFICIENT_SOURCE`, creates no successful post version, and explains that more source information is required. |
| FR-TEXT-007 | Must | Generated content shall distinguish reported facts from added opinion or analysis. | Evaluation samples contain no opinion presented as a CNN-reported fact; analytical language is introduced as interpretation or discussion. Any direct quotation must exist in the permitted source facts. |
| FR-TEXT-008 | Must | Generated content shall be original rather than a reproduction of the source. | Release evaluation finds no substantial copied passage from supplied source text beyond unavoidable names, titles, facts, and short attributed quotations. Flagged samples are rejected or revised before release. |
| FR-TEXT-009 | Must | Users shall be able to regenerate post text independently. | Regeneration creates a new version linked to the same source snapshot, preserves the previous version, and does not regenerate or delete the selected image unless separately requested. |
| FR-TEXT-010 | Must | Every successful generation shall retain traceable lineage. | The stored generation includes user, article, source-snapshot ID, tone, length, audience, prompt-template version, model identifier, timestamp, outcome, and provider/internal trace identifiers. |

### 9.5 AI image generation

| ID | Priority | Requirement | Measurable acceptance criteria |
|---|---|---|---|
| FR-IMG-001 | Must | The system shall compose an image prompt from the validated source facts and post context. | The saved generation record contains the composed prompt and source/post-version links. Unsupported details absent from the source or user instruction are not added as factual depictions. |
| FR-IMG-002 | Must | Users shall be able to generate a professional image suitable for the post. | A successful request returns one decodable image in an allowed format and configured size, stores it outside the relational database, and displays it with the draft. |
| FR-IMG-003 | Must | Generated images shall be original and shall not reproduce CNN photography or branding. | The application does not submit CNN images as references, and the prompt prohibits CNN logos, watermarks, trade dress, and recreation of source photographs. Release review rejects any output that violates this rule. |
| FR-IMG-004 | Must | Users shall be able to add image instructions. | The UI accepts additional instructions up to 1,000 characters, validates them server-side, and includes the accepted instruction in the stored prompt metadata. |
| FR-IMG-005 | Must | Users shall be able to regenerate images independently. | Each regeneration creates a new image record and leaves the current post text and previous image record unchanged until the user selects or deletes an asset. |
| FR-IMG-006 | Must | Users shall be able to download an authorised image. | The owner receives the image with the correct MIME type and a safe filename. An unauthenticated or different user cannot download it. |
| FR-IMG-007 | Must | Sensitive-news images shall avoid misleading documentary presentation. | Conflict, disaster, crime, health, election, and identifiable-person fixtures produce a conceptual/editorial-illustration prompt, not a claim of an actual photograph. The preview visibly identifies generated imagery as AI-generated where appropriate. |

### 9.6 Editor and LinkedIn-style preview

| ID | Priority | Requirement | Measurable acceptance criteria |
|---|---|---|---|
| FR-EDIT-001 | Must | Users shall be able to review and manually edit generated post text. | Text changes remain visible during the editing session and can be saved as a new current version without changing the immutable AI generation record. |
| FR-EDIT-002 | Must | Users shall be able to change tone and length and request regeneration. | Changing a supported control and regenerating produces a new text version with the updated configuration while retaining previous versions. |
| FR-EDIT-003 | Must | Users shall see a LinkedIn-style preview of the post and selected image. | The preview shows the complete current text, hashtags, attribution/source link, and selected image together and is clearly labelled as a preview rather than a live LinkedIn post. |
| FR-EDIT-004 | Must | Users shall be able to copy the final post. | A successful copy places the exact current editor text on the clipboard and shows confirmation; denied/unavailable clipboard access displays recovery guidance. |
| FR-EDIT-005 | Must | The editor shall warn about unsaved changes. | Navigating away with changed unsaved text triggers a warning; confirming departure discards the changes and cancelling retains them. |

### 9.7 Content management

| ID | Priority | Requirement | Measurable acceptance criteria |
|---|---|---|---|
| FR-CONT-001 | Must | Users shall be able to save generated posts and associated images. | Saving creates or updates a user-owned content item linked to its article, source snapshot, current post version, and selected image. Refreshing and reopening returns the saved state. |
| FR-CONT-002 | Must | Users shall be able to view their generated-content history. | The personal dashboard lists only the authenticated user's items with a title/summary, source, image when present, and created/updated timestamps. Pagination or an equivalent bounded result is used. |
| FR-CONT-003 | Must | Users shall be able to reopen and edit a saved post. | Opening an item loads its current text, image, source link, and generation controls; saving an edit updates the current version without changing another user's data. |
| FR-CONT-004 | Must | Users shall be able to delete saved content. | After explicit confirmation, the item disappears from the user's active history, subsequent access returns `404`, and associated assets follow the documented retention/deletion policy. |
| FR-CONT-005 | Must | Text and image regeneration shall remain separately available for saved content. | A user can regenerate only text or only image; the untouched content type remains unchanged and both operations retain version lineage. |

### 9.8 API behaviour and external-service failures

| ID | Priority | Requirement | Measurable acceptance criteria |
|---|---|---|---|
| FR-API-001 | Must | The backend shall expose documented REST endpoints for the required workflows. | The generated OpenAPI document includes authentication, articles, generation, content, and image operations with request/response schemas and error responses matching integration tests. |
| FR-API-002 | Must | The system shall handle CNN, OpenAI, database, and storage failures safely. | Timeout, rate-limit, unavailable, invalid-response, and storage-failure tests return a stable error code and useful user message, record a redacted trace, and do not expose credentials or stack traces. |
| FR-API-003 | Must | The system shall avoid accidental duplicate AI requests. | Repeating an in-flight request with the same user and idempotency key creates at most one chargeable generation record and returns the original outcome or current status. |
| FR-API-004 | Must | External retries shall be bounded. | Only retryable failures are retried, no operation makes more than the configured maximum of three attempts, and exponential backoff or the provider retry interval is used. |

## 10. Data requirements

| ID | Priority | Requirement | Measurable acceptance criteria |
|---|---|---|---|
| DR-001 | Must | Article records shall retain source identity and provenance. | Every article has a provider/source ID or canonical identity, canonical URL, retrieval timestamp, and rights/access-method reference. |
| DR-002 | Must | Each generation shall use an immutable source snapshot. | Editing or refreshing the catalogue does not alter the fact pack stored against an existing generation. |
| DR-003 | Must | Generated text and images shall retain version lineage. | A reviewer can navigate from every post/image version to its generation run, source snapshot, article, and owning user. |
| DR-004 | Must | User ownership shall be enforced at the database/service boundary. | All user-content queries include the authenticated owner scope, supported by cross-user integration tests. |
| DR-005 | Must | Image binary data shall be stored in controlled file/object storage. | The database stores metadata and a storage key rather than the binary; stored objects are private by default and delivered only after authorisation. |
| DR-006 | Must | Data retention shall follow the approved rights and privacy policy. | Source and generated records expose retention/deletion rules in configuration or documentation, and a test demonstrates deletion/expiry behaviour for at least one record type. |

## 11. Non-functional requirements

| ID | Category | Priority | Requirement and measurable acceptance criteria |
|---|---|---|---|
| NFR-SEC-001 | Security | Must | All credentials are loaded from server-side environment variables or a secret manager. Repository, client bundle, normal logs, fixtures, and screenshots contain no live secret; automated secret scanning passes. |
| NFR-SEC-002 | Security | Must | Passwords are stored only as hashes using an approved adaptive password-hashing algorithm. No API response or log contains a plaintext password or password hash. |
| NFR-SEC-003 | Security | Must | Input schemas enforce type, enum, length, and format limits; output is safely encoded; CORS, CSRF, cookie, and security-header settings are documented and tested for the deployment pattern. |
| NFR-SEC-004 | Security | Must | The release has no open critical/high security finding and automated tests cover authentication bypass, cross-user access, XSS input, unsafe URLs, and prompt-injection fixtures. |
| NFR-COMP-001 | Rights/compliance | Must | Every active live-source record carries the selected access-method and permitted-use metadata. The application cannot enable live ingestion without the documented NFA-5 decision/configuration. |
| NFR-COMP-002 | AI safety | Must | Release evaluation covers factual grounding, thin sources, sensitive news, copied-content risk, and unsafe/misleading image prompts; every critical failure is fixed or blocks release. |
| NFR-PERF-001 | Performance | Should | With external providers replaced by deterministic fakes and 10 concurrent test users, 95% of article-list, article-detail, save, and history API requests complete within 500 ms in the reference local environment. |
| NFR-PERF-002 | Performance | Should | Under normal provider availability, the UI gives immediate progress feedback and applies a configured maximum wait of 60 seconds for text and 120 seconds for image generation before presenting timeout/retry guidance. |
| NFR-REL-001 | Reliability | Must | A failed external call does not create a successful content version or corrupt prior saved content. Retrying after a recoverable failure produces at most one successful version per idempotency key. |
| NFR-REL-002 | Data integrity | Must | Database constraints protect required relationships and uniqueness; migrations apply successfully to an empty database and the supported prior schema in CI. |
| NFR-ACC-001 | Accessibility | Must | The core workflow is operable by keyboard with visible focus, associated labels and errors, and appropriate status announcements. Automated accessibility checks report no critical or serious violation on core pages. |
| NFR-UX-001 | Responsive design | Must | Registration, dashboard, generation, editor/preview, and history remain usable without horizontal page scrolling at 360 px, 768 px, and 1280 px viewport widths. |
| NFR-COMPAT-001 | Compatibility | Should | The core workflow passes smoke tests in the latest two stable versions of Chrome, Edge, Firefox, and Safari available at release testing. |
| NFR-MAINT-001 | Maintainability | Must | CNN access, OpenAI text, OpenAI image, storage, authentication, and content management are separate modules with interfaces that can be replaced by test fakes. |
| NFR-TEST-001 | Testability | Must | CI runs formatting/lint, type checks, unit tests, integration/contract tests, migration checks, build checks, and critical-path end-to-end tests. All release-gate checks pass before delivery. |
| NFR-OBS-001 | Observability | Must | Every source sync and AI generation has an internal trace ID, outcome, duration, and safe error class. Provider request IDs are stored when available; source text, generated content, credentials, and personal data are excluded from normal logs. |
| NFR-DEP-001 | Deployability | Must | From a clean clone, documented Docker Compose commands start the required local services, apply migrations, load synthetic fixtures, pass health checks, and run the documented demo flow. |
| NFR-COST-001 | Cost control | Must | OpenAI usage and outcome metadata are captured per generation; duplicate-call protection, per-user generation limits, bounded retries, and project spend alerts/limits are configured before release. |
| NFR-PRIV-001 | Privacy | Must | The application stores only data needed for the documented workflow, enforces user ownership, documents retention/deletion, and does not place personal data in provider prompts unless explicitly required and approved. |

## 12. Business rules

| ID | Rule |
|---|---|
| BR-001 | CNN is the only approved news source for the MVP. |
| BR-002 | The documented CNN access decision takes precedence over assumptions in this baseline; a restriction may reduce available fields but may not be bypassed. |
| BR-003 | The selected source snapshot is the sole factual basis for a generation. |
| BR-004 | A missing or insufficient source produces a refusal, not model-supplied facts. |
| BR-005 | Generated content must include attribution and the original CNN link. |
| BR-006 | Generated images must not reproduce CNN photography or branding. |
| BR-007 | The user is responsible for reviewing and manually publishing the final content. |
| BR-008 | Direct LinkedIn publishing is prohibited in the MVP even if technically possible. |

## 13. Major-feature acceptance matrix

The release must pass every **Must** row below. Detailed criteria remain authoritative in the referenced requirements.

| Major feature | Release acceptance test | Requirement coverage |
|---|---|---|
| Authorised CNN discovery | Approved adapter imports a valid test batch, records permitted fields/provenance, rejects malformed items, and creates no duplicates; without approval it makes no live request. | FR-SRC-001–008, DR-001, NFR-COMP-001 |
| Authentication | A new user registers, logs in, refreshes the session, logs out, and is denied afterward; a second user cannot access the first user's content. | FR-AUTH-001–005, NFR-SEC-001–004 |
| Article dashboard | User views required metadata, filters all categories, selects an eligible article, opens the canonical CNN link, and sees explicit empty/error states. | FR-DASH-001–005 |
| LinkedIn generation | User exercises every tone, length, and audience option; valid sources create structured, attributed drafts with claim mappings; thin sources refuse generation. | FR-TEXT-001–010, NFR-COMP-002 |
| Image generation | User generates and independently regenerates an original image, supplies additional instructions, sees appropriate disclosure, and downloads it; sensitive fixtures use conceptual treatment. | FR-IMG-001–007 |
| Editor and preview | User edits text, changes controls, previews current text/image, receives an unsaved-change warning, and copies the exact final text. | FR-EDIT-001–005 |
| Content management | User saves, reopens, edits, versions, lists, and deletes their own content; another user is denied every operation. | FR-CONT-001–005, DR-002–006 |
| Failure handling | Simulated timeouts, rate limits, invalid provider responses, database errors, and storage errors produce safe recoverable states without duplicate or corrupted content. | FR-API-001–004, NFR-REL-001–002, NFR-OBS-001 |
| Local delivery | A reviewer follows the README from a clean clone, starts the application, loads safe fixtures, and completes the critical workflow with all release checks passing. | NFR-TEST-001, NFR-DEP-001 |

## 14. Project-brief traceability

| Project brief section | Baseline coverage |
|---|---|
| 2.1 CNN News Discovery and Extraction | FR-SRC-001–008, DR-001, NFR-COMP-001 |
| 2.2 News Article Dashboard | FR-DASH-001–005 |
| 2.3 AI-Powered LinkedIn Post Generation | FR-TEXT-001–010, BR-003–005 |
| 2.4 AI Image Generation | FR-IMG-001–007, BR-006 |
| 2.5 LinkedIn Content Editor and Preview | FR-EDIT-001–005 |
| 2.6 Content Management | FR-CONT-001–005, DR-002–006 |
| 2.7 User Authentication | FR-AUTH-001–005, NFR-SEC-001–004 |
| 3 Expected Application Workflow | Major-feature acceptance matrix in Section 13 |
| 4 Proposed System Architecture | NFR-MAINT-001 and the architecture in `PROJECT_PLAN.md` |
| 5 Suggested Technology Stack | NFR-DEP-001 and the planned architecture in `README.md` |
| 6 Technical Requirements | FR-API-001–004 and all non-functional requirements |
| 7 Development Milestones | `PROJECT_PLAN.md` and `PROJECT_MANAGEMENT.md` |
| 8 Project Deliverables | NFR-TEST-001, NFR-DEP-001, and Epic E9 in `PROJECT_PLAN.md` |
| 9 Acceptance Criteria | Sections 9–13 of this baseline |
| 10 Scope and Limitations | Section 6 and BR-001–008 |
| 11 Final Expected Outcome | Product objective in Section 3 and acceptance matrix in Section 13 |

No approved project-brief requirement is intentionally omitted. Clarifications added here make broad brief statements measurable without expanding the product into an excluded feature.

## 15. NFA-3 acceptance evidence

| Jira acceptance criterion | Evidence in this document | Result |
|---|---|---|
| Functional requirements are documented | Section 9 and Section 10 | Met |
| Non-functional requirements are documented | Section 11 | Met |
| In-scope and out-of-scope features are identified | Section 6 | Met |
| Each major feature has measurable acceptance criteria | Detailed tables in Sections 9–11 and summary matrix in Section 13 | Met |
| Requirements are consistent with the approved project brief | Section 14 traceability matrix | Met, pending product-owner review |
| Requirements baseline is saved in project documentation | `docs/jira/NFA-3.md` | Met |

## 16. Baseline review checklist

- [ ] Product owner confirms the product objective and primary user workflow.
- [ ] Product owner confirms in-scope and out-of-scope boundaries.
- [ ] Product owner confirms the measurable post-length ranges and other clarified business rules.
- [ ] Technical reviewer confirms requirements are feasible and testable.
- [ ] Reviewer confirms traceability to the approved brief.
- [ ] Approval table in Section 1 is completed.
- [ ] NFA-3 is moved through the agreed Jira review/verification status and then marked Done.

## 17. Change control

After approval, changes to a requirement must:

1. Be proposed in a linked Jira issue.
2. Describe the reason and impact on scope, schedule, rights, security, testing, and documentation.
3. Receive product-owner approval before implementation when the change affects scope or acceptance.
4. Update this document's version and revision history without reusing or silently deleting requirement IDs.
5. Update affected Jira Tasks, tests, plans, and architecture decisions.

Research or implementation notes that do not change a requirement belong in the relevant Jira deliverable file, not in this baseline.
