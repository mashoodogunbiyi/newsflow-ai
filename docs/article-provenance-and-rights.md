# NFA-32 - Article Provenance and Rights Metadata

## Purpose

NFA-32 makes every stored article traceable and prevents NewsFlow AI from treating an article as authorised merely because a provider returned it.

The implementation uses only synthetic fixture data. It does not enable live CNN access, and it does not represent any confirmed CNN permission.

## Plain-language explanation

Provenance answers: "Where did this article information come from?"

Rights metadata answers: "What is NewsFlow AI allowed to do with it?"

Each retrieval creates a provenance event. Each permission change creates a new rights version. Before displaying, retaining, exporting, or using article information for AI generation, the reusable rights service checks the current version. Missing, unverified, revoked, expired, or disabled-source rights are denied by default.

## Data model

### `article_provenance_events`

This immutable table records one event for every accepted ingestion attempt, including repeated articles that are skipped by deduplication.

| Field | Meaning |
|---|---|
| `article_id` | Stable article identity linked by a foreign key |
| `source_profile_id` | Approved provider profile linked by a foreign key |
| `source_item_id` | Permitted provider article identifier |
| `canonical_url` | Original HTTPS article URL |
| `publication_date` | Source publication timestamp |
| `retrieved_at` | Time the provider supplied the record |
| `source_integration_ref` | Approved integration or profile reference |
| `source_contract_version` | Data contract used for the retrieval |
| `authorisation_reference` | Non-secret authorisation decision reference |
| `ingestion_action` | `created`, `updated`, or `skipped` |

Deduplication therefore avoids duplicate article rows without deleting retrieval history.

### `article_rights_versions`

This table stores immutable, structured permission decisions. `articles.current_rights_version_id` selects the version used for new checks while earlier versions remain available as audit evidence.

The fields cover verification status, storage, display, AI processing, derivative output, redistribution, attribution, retention, expiry, authorisation reference, contract version, verification time, and effective time.

Only one non-superseded rights version can exist for an article. An update marks the old version as superseded, inserts the new version, and moves the article pointer in one transaction.

## Database protections

Migration `20261029_0003` adds both tables and their relationships. PostgreSQL constraints enforce:

- Valid article and source-profile references.
- HTTPS canonical URLs and non-empty source identifiers.
- Documented ingestion actions and rights statuses.
- Retrieval timestamps that do not precede publication.
- Positive, unique rights version numbers per article.
- A maximum of one current rights version per article.
- No allowed operation when rights are unverified or revoked.
- Derivative output only when AI processing is also allowed.
- Approved attribution text when attribution is required.
- Retention expiry after the rights effective time.
- A current rights pointer that belongs to the same article.

The migration backfills one rights version for existing current article snapshots. New retrieval events are recorded by the ingestion repository; historical retrieval events cannot be invented during migration.

## Rights checks

`ArticleRightsService.can_use_article(article_id, operation)` supports:

- `display_metadata`
- `store_metadata`
- `use_for_ai_generation`
- `export_source_information`
- `retain_article`

AI generation requires both `ai_processing_allowed` and `derivative_output_allowed`. Export requires explicit redistribution permission. The synthetic policy deliberately sets redistribution to false because it has not been granted.

A check is denied when:

- No current rights record exists.
- The source profile is disabled.
- The record is unverified or revoked.
- The rights are not yet effective.
- The retention or permission period has expired.
- Required attribution is incomplete.
- The requested operation is not explicitly allowed.

Callers that require permission can use `require_article_use`, which raises a content-free denial rather than continuing.

## Rights changes and retention

`update_rights` appends a new version instead of rewriting history. Subsequent checks immediately use the new current version. Revoked and unverified versions must set all operation flags to false.

An expiry causes the rights service to deny further restricted use. This task records the deletion or retention requirement and prevents newly prohibited operations. A later retention worker must perform physical deletion or archival actions required by an authorised agreement while preserving only permitted audit evidence.

## Logging and confidentiality

Rights decisions log only the article ID, operation, allow or deny result, safe reason, and rights-version ID. Logs do not include provider credentials, article text, attribution text, confidential agreement text, or personal information.

Public APIs must expose only information required by their contract. This task does not create a public rights-administration endpoint.

## Automated evidence

Run the fast tests from `apps/api`:

```bash
pytest tests/test_article_rights.py tests/test_article_deduplication.py
```

These tests cover permitted use, missing and unverified rights, source disablement, AI restrictions, attribution, expiration, rights updates, provenance retrieval, safe denials, confidential logging, and invalid policy combinations.

The safety-gated PostgreSQL integration test also proves provenance is retained across created, skipped, and updated ingestion events and that current rights are linked correctly:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_article_deduplication_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_article_deduplication_integration.py
```

Never point the destructive integration test at the normal development database or a shared database.

## Acceptance status

- Provenance and rights models - complete.
- PostgreSQL migration, constraints, and relationships - complete.
- Article-to-provider, provenance, and current-rights links - complete.
- Fail-closed reusable rights service - complete.
- Versioned rights updates, attribution, retention, and expiry - complete.
- Deduplication preservation of provenance and rights - complete.
- Synthetic seed data and automated tests - complete.
- Live CNN access - intentionally not enabled under ADR-001.

## Limitations and next integration step

The ingestion repository and rights service are backend building blocks. Future catalogue and AI-generation tasks must call `require_article_use` immediately before each rights-sensitive action. A retention worker is still required before an agreement with deletion duties can be activated. Any live provider needs a reviewed agreement, an updated source profile and rights mapping, and a new Go decision before use.
