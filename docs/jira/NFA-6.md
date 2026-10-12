# NFA-6 - Source Data Contract

## 1. Document control

| Field | Value |
|---|---|
| Project | NewsFlow AI |
| Jira issue | NFA-6 |
| Project-plan task | T0.4 - Define the source data contract |
| Version | 1.0 |
| Status | Approved fixture-first source data contract |
| Created | 12 October 2026 |
| Approved | 12 October 2026 |
| Owner | Mashood Ogunbiyi |
| Requirements baseline | [NFA-3 - Baseline Requirements and Acceptance Criteria](NFA-3.md) |
| Access research | [NFA-4 - CNN Data Access Research](NFA-4.md) |
| Authorisation decision | [NFA-5 - CNN Authorisation Record](NFA-5.md) |
| Repository path | `docs/jira/NFA-6.md` |

### Revision history

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 12 October 2026 | Defined and approved the fixture-first news source contract, validation rules, missing-data handling, provenance, attribution, and live-source restrictions | Mashood Ogunbiyi |

### Approval

Mashood Ogunbiyi has reviewed and approved this document as the project and document owner. The approval applies to the fixture-first contract and the common structure that future source adapters must implement.

This approval does not authorise live CNN retrieval. NFA-5 records that live CNN authorisation has not been obtained. A live-source profile must remain disabled until written permission is obtained, NFA-5 is revised, and the provider-specific fields and restrictions are approved in a new version of this contract.

| Role | Name | Decision | Date |
|---|---|---|---|
| Project and document owner | Mashood Ogunbiyi | Approved | 12 October 2026 |
| Technical reviewer | Mashood Ogunbiyi | Self-reviewed and accepted for the current solo phase | 12 October 2026 |

## 2. Purpose

This document defines the structure and format of news information that NewsFlow AI can retrieve, validate, store, display, and process. It provides one normalised contract for source adapters, the application database, the news dashboard, and later AI generation work.

The contract has two purposes:

- Allow development and testing to continue safely with original synthetic fixtures.
- Define the controls that a future authorised live provider must satisfy before its data can enter the application.

The required product fields are title, publication date, category, description, URL, and permitted content. The contract also includes identity, provenance, rights, retrieval, and attribution fields because the application cannot process source information safely without them.

## 3. Current contract decision

| Decision area | Approved position |
|---|---|
| Active source profile | `fixture-v1` |
| Allowed data source | Original synthetic NewsFlow AI fixtures only |
| Live CNN profile | Not approved and disabled |
| Live network requests | Prohibited |
| Fixture processing by OpenAI | Allowed when the fixture is original, synthetic, and contains no copied CNN material |
| Live CNN processing by OpenAI | Not authorised |
| Fixture retention | Retain in the development repository or test environment until replaced or deleted |
| Live-source retention | Not defined until a written licence supplies the rule |
| Contract failure behaviour | Reject or quarantine invalid input and fail closed |

The source adapter must default to `disabled`. Development may explicitly select `fixture`. No configuration value may enable a live adapter until an approved provider profile exists.

## 4. Normalised news record

### 4.1 Field definitions

| Field | Type | Required | Nullable | Rule and purpose |
|---|---|---:|---:|---|
| `contract_version` | String | Yes | No | Exact value `1.0` for this contract. Unknown major versions are rejected. |
| `source_profile` | String enum | Yes | No | `fixture-v1` is the only currently approved value. |
| `source_item_id` | String | Yes | No | Stable identifier within the source profile. It must be unique and 1 to 200 characters. Fixture values use the prefix `fixture-`. |
| `source_name` | String | Yes | No | Human-readable origin. Current value is `NewsFlow AI synthetic fixture`. A future live value must match the approved provider profile. |
| `title` | String | Yes | No | News title used for discovery and display. After trimming, it must contain 1 to 300 characters. |
| `publication_date` | RFC 3339 date-time string | Yes | No | Original publication time including a timezone. It is normalised to UTC for storage. |
| `category` | String enum | Yes | No | One of `Technology`, `Business`, `World News`, `Science`, or `Other`. |
| `description` | String or null | Yes | Yes | Short source description. The property must exist. A permitted value contains 1 to 1,000 characters after sanitisation; otherwise it is `null`. |
| `url` | HTTPS URL string | Yes | No | Canonical source URL used for identity and attribution. It must contain no credentials and must satisfy Section 7. |
| `permitted_content` | Object | Yes | No | Content that may be processed, together with explicit rights state. Defined in Section 4.2. |
| `attribution` | Object | Yes | No | Display and output attribution instructions. Defined in Section 4.3. |
| `rights` | Object | Yes | No | Records the decision that permits or blocks storage, AI processing, and derivative output. Defined in Section 4.4. |
| `retrieved_at` | RFC 3339 date-time string | Yes | No | Time the adapter supplied the record to NewsFlow AI. It is normalised to UTC. |
| `modified_at` | RFC 3339 date-time string or null | Yes | Yes | Source modification time when supplied and permitted; otherwise `null`. |

Requiring a property does not always require a text value. For example, `description` must always be present so consumers can distinguish a deliberately recorded missing value from a malformed record, but its value may be `null`.

### 4.2 Permitted content object

| Field | Type | Required | Rule |
|---|---|---:|---|
| `status` | String enum | Yes | One of `available`, `missing`, or `not_permitted`. |
| `content_type` | String enum | Yes | One of `synthetic`, `provider_description`, `licensed_article_text`, or `none`. |
| `text` | String or null | Yes | Contains only the text covered by the recorded permission. Maximum 20,000 characters for this contract. It must be `null` when status is `missing` or `not_permitted`. |
| `ai_processing_allowed` | Boolean | Yes | Must be `true` before the text can be sent to the OpenAI API. |
| `derivative_output_allowed` | Boolean | Yes | Must be `true` before the text can support a LinkedIn draft intended for external use. |

Rules for `permitted_content`:

- `fixture-v1` uses `status: available`, `content_type: synthetic`, and original synthetic text.
- A missing source description or body uses `status: missing`, `content_type: none`, and `text: null`.
- Content excluded by a licence uses `status: not_permitted`, `content_type: none`, and `text: null`.
- `licensed_article_text` cannot be used until an approved provider profile explicitly allows retrieval, storage, OpenAI processing, transformation, retention, and attribution.
- `ai_processing_allowed` and `derivative_output_allowed` default to `false` when a value is absent or unclear.
- A record is not eligible for generation unless both permission flags are `true` and the permitted facts are sufficient for grounded output.

### 4.3 Attribution object

| Field | Type | Required | Rule |
|---|---|---:|---|
| `display_name` | String | Yes | Name shown beside the source link. Fixture value is `NewsFlow AI synthetic fixture`. |
| `canonical_url` | HTTPS URL string | Yes | Must exactly match the normalised top-level `url`. |
| `attribution_text` | String | Yes | Required wording for display and generated output. Maximum 500 characters. |
| `byline` | String or null | Yes | Provider byline when supplied, permitted, and required; otherwise `null`. |
| `copyright_notice` | String or null | Yes | Provider wording when required by an approved licence; otherwise `null`. |

Fixture attribution must clearly state that the record is synthetic and is not live news. It must not use CNN branding, a CNN byline, or a URL that could be mistaken for a live CNN article.

A future CNN record must display the source name, the exact canonical URL, and every byline, copyright notice, or provider phrase required by the approved agreement. Attribution does not replace permission.

### 4.4 Rights object

| Field | Type | Required | Rule |
|---|---|---:|---|
| `decision_id` | String | Yes | Current fixture decision references `NFA-SRC-AUTH-001` and its fixture-only outcome. |
| `access_method` | String enum | Yes | Current value is `fixture`. Future values require an approved provider profile. |
| `storage_allowed` | Boolean | Yes | Must be `true` before the record is persisted. |
| `display_allowed` | Boolean | Yes | Must be `true` before source fields are shown to a user. |
| `expires_at` | RFC 3339 date-time string or null | Yes | Licence expiry or content expiry when applicable; otherwise `null`. |
| `retention_rule` | String | Yes | Machine-readable policy name. Current value is `fixture-until-replaced-or-deleted`. |

If any required right is false or uncertain, the application must block the affected operation. It must not infer permission from a public webpage, working endpoint, API subscription, or missing restriction.

## 5. Approved fixture example

```json
{
  "contract_version": "1.0",
  "source_profile": "fixture-v1",
  "source_item_id": "fixture-technology-001",
  "source_name": "NewsFlow AI synthetic fixture",
  "title": "Synthetic company announces an energy-efficient data platform",
  "publication_date": "2026-10-12T09:00:00Z",
  "category": "Technology",
  "description": "A fictional technology company has announced a test data platform designed to reduce energy use.",
  "url": "https://example.invalid/newsflow-ai/fixture-technology-001",
  "permitted_content": {
    "status": "available",
    "content_type": "synthetic",
    "text": "This is original synthetic test content created for NewsFlow AI. It does not describe a real CNN report.",
    "ai_processing_allowed": true,
    "derivative_output_allowed": true
  },
  "attribution": {
    "display_name": "NewsFlow AI synthetic fixture",
    "canonical_url": "https://example.invalid/newsflow-ai/fixture-technology-001",
    "attribution_text": "Source: NewsFlow AI synthetic fixture - not live news",
    "byline": null,
    "copyright_notice": null
  },
  "rights": {
    "decision_id": "NFA-SRC-AUTH-001",
    "access_method": "fixture",
    "storage_allowed": true,
    "display_allowed": true,
    "expires_at": null,
    "retention_rule": "fixture-until-replaced-or-deleted"
  },
  "retrieved_at": "2026-10-12T09:05:00Z",
  "modified_at": null
}
```

The example is illustrative contract data. It must not be presented to a user as a real news report.

## 6. Validation and normalisation rules

### 6.1 General rules

- Reject unknown required-field types, missing required properties, and unknown major contract versions.
- Trim surrounding whitespace and normalise text to Unicode NFC.
- Remove executable markup, scripts, event handlers, control characters, and unsafe links.
- Treat source text as untrusted data, never as system instructions or application configuration.
- Preserve the factual meaning of permitted text during sanitisation. Do not silently rewrite source facts.
- Record a safe validation code and source item ID when rejecting a record. Do not log full source text, credentials, or confidential rights information.
- Ignore unknown optional fields for forward compatibility, but do not persist or process them until added to an approved contract version.

### 6.2 Field-specific rules

| Field | Validation | Invalid result |
|---|---|---|
| `source_item_id` | Trimmed, 1 to 200 characters, unique within `source_profile`, and limited to letters, numbers, period, underscore, colon, and hyphen | Reject |
| `title` | Plain text, 1 to 300 characters after sanitisation | Reject |
| `publication_date` | Valid RFC 3339 date-time with timezone; not more than five minutes in the future | Reject and quarantine for review |
| `category` | Exact supported value after approved mapping | Map an unknown non-empty source category to `Other`; reject a missing value |
| `description` | `null` or plain text of 1 to 1,000 characters | Convert empty or whitespace-only text to `null`; reject an over-limit or unsafe value that cannot be sanitised safely |
| `url` | Absolute HTTPS URL with no username, password, or fragment | Reject |
| `permitted_content.text` | Consistent with permission status, sanitised plain text, maximum 20,000 characters | Reject and block generation |
| Permission flags | Explicit Boolean values consistent with the rights decision | Default to false and block the affected operation |
| `retrieved_at` | Valid RFC 3339 date-time with timezone; not earlier than `publication_date` without an explicit test-clock exception | Reject |
| `modified_at` | `null` or valid RFC 3339 date-time not earlier than `publication_date` | Reject |

### 6.3 Duplicate handling

- The pair `source_profile` and `source_item_id` is the primary source identity.
- The normalised canonical `url` is a second uniqueness key.
- Reprocessing the same ID or canonical URL must not create a second active article.
- A later valid record may update mutable catalogue fields and `modified_at`, but it must not alter an immutable source snapshot already linked to a generation.
- Conflicting IDs and URLs are quarantined for review instead of being merged automatically.

## 7. URL and attribution rules

### 7.1 Canonical URL normalisation

- Accept HTTPS only.
- Convert the host name to lowercase.
- Remove the URL fragment.
- Remove known tracking parameters only when the provider contract permits normalisation.
- Do not follow a redirect to a different unapproved host during ingestion.
- Store one canonical URL and use the exact stored value in the dashboard, preview, saved content, and exported post.
- Fixture URLs must use the reserved `.invalid` domain.
- A future live profile must define its approved hosts, redirects, query handling, and canonicalisation rules.

### 7.2 Output attribution

Every article view and generated LinkedIn draft must include:

- The approved source display name.
- The exact canonical source URL.
- Required provider attribution wording.
- A byline or copyright notice when the approved provider profile requires it.

The application must not remove attribution during editing or export. If required attribution cannot be produced, generation or export must be blocked with `ATTRIBUTION_INCOMPLETE`.

## 8. Missing and restricted information handling

| Condition | Required behaviour | Generation eligibility |
|---|---|---|
| Missing `title` | Reject the record with `MISSING_TITLE` | Not eligible |
| Missing or invalid `publication_date` | Reject the record with `INVALID_PUBLICATION_DATE` | Not eligible |
| Missing `category` | Reject with `MISSING_CATEGORY` | Not eligible |
| Unknown non-empty category | Store as `Other` and retain the original value only if permitted | Depends on all other checks |
| Missing or blank `description` | Store `description: null` and show `No description available` in the interface | Eligible only if sufficient permitted content exists |
| Missing or invalid `url` | Reject with `INVALID_CANONICAL_URL` | Not eligible |
| Missing `permitted_content` object | Reject with `MISSING_PERMISSION_STATE` | Not eligible |
| Content is unavailable | Use `status: missing`, `content_type: none`, and `text: null` | Eligible only if another permitted fact source is sufficient |
| Content is not licensed | Use `status: not_permitted`, do not retrieve or store the text, and record no excerpt | Not eligible unless separately permitted information is sufficient |
| AI processing not allowed | Keep permitted display data only where storage and display are allowed | Not eligible |
| Derivative output not allowed | Do not generate or export a LinkedIn draft | Not eligible |
| Attribution incomplete | Allow no generation or export | Not eligible |
| Unsupported contract version | Reject with `UNSUPPORTED_CONTRACT_VERSION` | Not eligible |

Missing information must never be invented by the application or supplied from model memory. The user must receive a clear, non-technical explanation when an article cannot be used for generation.

## 9. Provenance, refresh, and retention

### 9.1 Provenance

Every accepted record must be traceable to:

- Its `source_profile` and `source_item_id`.
- Its `source_name` and access method.
- Its rights decision ID.
- Its canonical URL.
- Its publication, retrieval, and modification times.
- The contract version used for validation.

Every generation must use an immutable source snapshot so that a later catalogue update cannot change the evidence behind an existing draft.

### 9.2 Refresh

- `fixture-v1` performs no network refresh.
- Fixtures are loaded during an explicit development or test setup action.
- Manual fixture reloads must remain idempotent and produce no duplicates.
- Live scheduling and manual live synchronisation remain disabled.
- A future live profile must state the permitted refresh interval, date window, rate limits, concurrency rules, and correction or withdrawal behaviour.

### 9.3 Retention

- Approved synthetic fixtures may remain in the repository and development database until replaced or deliberately deleted.
- Fixture-generated test data may be cleared when the local environment is reset.
- Immutable snapshots linked to retained generated content follow the generated-content retention policy.
- No live-source retention period is approved.
- A future live profile must define maximum storage duration, cache duration, expiry, correction, withdrawal, and deletion requirements before ingestion is enabled.

## 10. Adapter behaviour and processing boundary

All source adapters must return the normalised record defined in Section 4. Provider-specific responses must not pass directly into the database, user interface, prompt builder, or OpenAI client.

The processing sequence is:

1. Confirm that the requested source profile is approved and enabled.
2. Retrieve data only when the profile permits retrieval.
3. Map provider fields into the normalised record.
4. Apply permission, type, format, sanitisation, URL, and duplicate checks.
5. Reject or quarantine invalid records with safe error codes.
6. Persist only approved fields and their provenance.
7. Build an immutable source snapshot from eligible permitted content.
8. Send content to OpenAI only when both processing permission and source sufficiency checks pass.

When the profile is missing, disabled, or unapproved, the adapter must return `SOURCE_NOT_AUTHORISED` and make no external content request.

## 11. Error codes

| Code | Meaning |
|---|---|
| `SOURCE_NOT_AUTHORISED` | The requested live source has no approved profile or permission |
| `UNSUPPORTED_CONTRACT_VERSION` | The record uses an unsupported major contract version |
| `MISSING_SOURCE_ID` | The source identity is absent |
| `MISSING_TITLE` | The required title is absent or empty |
| `INVALID_PUBLICATION_DATE` | The publication date is missing, malformed, or unreasonably in the future |
| `MISSING_CATEGORY` | No category value was supplied |
| `INVALID_CANONICAL_URL` | The URL is missing, unsafe, malformed, or outside the approved rules |
| `MISSING_PERMISSION_STATE` | The record does not state what content and processing are permitted |
| `CONTENT_NOT_PERMITTED` | Source text is outside the recorded permission |
| `AI_PROCESSING_NOT_PERMITTED` | The record cannot be supplied to the OpenAI API |
| `DERIVATIVE_OUTPUT_NOT_PERMITTED` | A LinkedIn draft cannot be generated or exported |
| `ATTRIBUTION_INCOMPLETE` | Required attribution data is absent |
| `DUPLICATE_SOURCE_CONFLICT` | Source ID and canonical URL conflict with existing records |
| `SOURCE_CONTENT_INVALID` | Source text fails type, length, or sanitisation validation |

## 12. Test and acceptance approach

The implementation of this contract must include automated tests for:

- A complete valid synthetic record.
- Each missing required property.
- A `null` and a valid description.
- Every supported category and unknown-category mapping to `Other`.
- Invalid dates, future dates, unsafe URLs, URL credentials, and URL fragments.
- Script, event-handler, malformed HTML, encoded markup, and prompt-injection-style source text.
- Missing, unavailable, and not-permitted content states.
- False or absent AI-processing and derivative-output permissions.
- Complete and incomplete attribution.
- Duplicate provider IDs, duplicate canonical URLs, and conflicting identities.
- Idempotent fixture reloads.
- An attempted live sync returning `SOURCE_NOT_AUTHORISED` without making a network request.
- An immutable source snapshot remaining unchanged after a catalogue update.

## 13. Future live-provider profile

A future live profile is a controlled extension of this contract, not an informal configuration change. Before it can be approved, it must record:

- The provider and exact product or service.
- Written authorisation evidence and the NFA-5 decision revision.
- Approved endpoints, credentials process, environments, and rate limits.
- Provider-to-normalised-field mappings.
- Permitted titles, dates, categories, descriptions, article text, quotations, bylines, and media.
- Storage, caching, retention, correction, withdrawal, and deletion rules.
- Permission to send each field to OpenAI.
- Permission to create and externally use derivative LinkedIn content.
- Required attribution, canonical URL, branding, and copyright wording.
- Territory, user, volume, expiry, and termination restrictions.
- New validation, contract, integration, and compliance tests.

The new profile requires a version update and project-owner approval. Until then, `fixture-v1` remains the only enabled profile.

## 14. Acceptance-criteria traceability

| Acceptance criterion | Evidence in this document | Result |
|---|---|---|
| Required fields identified: title, publication date, category, description, URL, and permitted content | Sections 4.1 and 4.2 | Complete |
| Data types and validation rules documented | Sections 4 and 6 | Complete |
| Missing information handling defined | Section 8 | Complete |
| Source attribution requirements documented | Sections 4.3 and 7 | Complete |

Additional project-plan requirements are covered as follows:

| Project-plan requirement | Evidence |
|---|---|
| Provenance | Section 9.1 |
| Refresh interval and behaviour | Section 9.2 |
| Retention rule | Section 9.3 |
| Canonical URL rule | Section 7.1 |
| Behaviour when full text is not permitted | Sections 4.2 and 8 |

## 15. Review and Jira decision

NFA-6 is complete and approved by Mashood Ogunbiyi for the current fixture-first project state. The four Jira acceptance criteria are satisfied by this document.

The next workflow actions are:

1. Review the Markdown preview and request any required changes.
2. Commit and merge this document through the normal GitHub workflow.
3. Add the final document, pull-request, and commit links to NFA-6 in Jira.
4. Move NFA-6 to Done after the evidence links are recorded.
5. Continue to NFA-7 - Complete privacy, copyright, and AI safety review.
6. Keep live CNN retrieval disabled unless NFA-5 and this contract are formally revised.

The practical project state is:

- The normalised news data structure is approved.
- Synthetic fixture development is approved.
- Required validation, missing-data, attribution, provenance, refresh, and retention behaviour is defined.
- Live CNN ingestion remains blocked.
