# Article Normalisation, Validation, and Sanitisation

## Purpose

NFA-30 adds the backend boundary that converts provider-specific article records into NewsFlow AI's approved `NewsArticle` structure. The boundary runs before article information can be stored in PostgreSQL or passed to the rest of the application.

The current implementation processes original synthetic fixtures only. It does not connect to CNN, scrape a website, fetch an article URL, or assume any CNN response format or permission.

## Beginner explanation

Different providers can use different labels for the same information. One provider might call an article title `headline`, while another calls it `title`. The normalisation service works like a careful translator:

```text
Provider-specific record
          |
          v
Approved field mapping and rights check
          |
          v
Text, date, category, and URL rules
          |
          v
Strict Pydantic NewsArticle validation
          |
          v
Safe provider-neutral article or documented error
```

It maps only approved fields, cleans formatting without changing facts, rejects unsafe or invalid records, and adds trusted attribution and rights information from configuration rather than from untrusted provider data.

## Implementation

| File | Responsibility |
|---|---|
| `apps/api/app/providers/normalisation.py` | Defines the approved mapping, rights policy, text, date, category, and URL rules, plus safe normalisation errors. |
| `apps/api/app/providers/models.py` | Applies a second strict Pydantic validation layer to the final provider-neutral article. |
| `apps/api/app/providers/fixture_provider.py` | Sends every synthetic provider record through the normalisation service. |
| `apps/api/tests/test_article_normalisation.py` | Verifies valid, invalid, unsafe, rights-restricted, and differently shaped records. |

The two validation layers have different jobs:

1. `ArticleNormalisationService` translates one authorised provider shape into the standard shape and enforces the provider policy.
2. `NewsArticle` performs final contract validation, including text lengths, identifiers, timestamps, rights relationships, and attribution URL consistency.

## Rights-aware field allowlist

The synthetic fixture policy reads only these provider fields:

| Provider field | Standard use | Required |
|---|---|---:|
| `record_key` | Source item identifier | Yes |
| `headline` | Article title | Yes |
| `link` | Canonical article URL | Yes |
| `published_at` | Publication timestamp | Yes |
| `topic` | Article category | Yes |
| `summary` | Optional permitted description | No |
| `body` | Permitted synthetic content | Yes |
| `collected_at` | Retrieval timestamp | Yes |
| `changed_at` | Optional modification timestamp | No |

Other keys are not copied into the `NewsArticle` model. For example, a provider image, internal note, or unlicensed full-text field is ignored and cannot appear in the normalised result.

The policy checks storage and display permission before reading article fields. The source name, decision identifier, access method, attribution wording, retention rule, content type, and AI permissions come from the trusted policy. A provider record cannot replace those values.

This fixture allowlist is not permission to use equivalent CNN fields. A future live provider requires a revised NFA-5 authorisation record, an updated NFA-6 source data contract, an approved ADR, and its own reviewed policy and tests.

## Text rules

- Treat every provider-supplied string as untrusted.
- Convert Unicode text to NFC so equivalent characters use one consistent representation.
- Decode HTML entities before checking for markup, so encoded tags are not mistaken for safe text.
- Trim leading and trailing whitespace.
- Collapse repeated whitespace in identifiers, titles, URLs, categories, and descriptions.
- Preserve permitted-content line boundaries while normalising whitespace within each line.
- Convert a blank optional description to `null` rather than inventing a description.
- Reject HTML-like markup, including incomplete tags, instead of storing or rendering it.
- Reject unsupported control characters while allowing normal line breaks and tabs.
- Apply Pydantic maximum lengths from the approved source contract.
- Never create, rewrite, or infer a missing article fact.

The frontend must continue rendering article fields as plain text. It must not insert provider text with React's `dangerouslySetInnerHTML`. If approved HTML is introduced later, it needs a separate documented allowlist and an established sanitisation library.

## Date and category rules

- Accept a timezone-aware Python `datetime` or an ISO 8601/RFC 3339 string.
- Reject an unparseable or timezone-free timestamp because its exact instant is ambiguous.
- Convert accepted timestamps to UTC.
- Validate the final relationships, such as retrieval not preceding publication.
- Map approved category labels to the NFA-6 category values.
- Map an unknown but non-empty category to `Other` without inventing a more specific category.
- Reject a missing or blank category.

## URL rules

- Require HTTPS.
- Require a hostname approved by the active source policy.
- Reject embedded usernames or passwords.
- Reject malformed URLs and invalid ports.
- Lowercase the scheme and hostname.
- Remove URL fragments because fragments do not identify server-side article content.
- Preserve the path and query string.
- Do not fetch the URL during normalisation.

The current fixture policy accepts only `example.invalid`. If backend URL fetching is added in a later task, it must include separate server-side request forgery protections, redirect controls, timeouts, response-size limits, and network tests. URL validation by itself is not an SSRF defence.

## Safe error handling

Invalid input raises `ArticleNormalisationError` with a stable code and a general safe message. The message does not repeat the raw title, URL, restricted content, credentials, or provider response.

| Code | Meaning |
|---|---|
| `INVALID_ARTICLE_RECORD` | The record or one of its fields has the wrong structure or type. |
| `MISSING_REQUIRED_ARTICLE_FIELD` | A required approved field is absent or blank. |
| `INVALID_ARTICLE_DATE` | A timestamp cannot be parsed or has no timezone. |
| `INVALID_ARTICLE_URL` | A URL is malformed or outside the approved URL policy. |
| `UNSAFE_ARTICLE_TEXT` | Text contains markup or unsupported control characters. |
| `ARTICLE_RIGHTS_NOT_PERMITTED` | The active rights policy does not allow retention and display. |
| `ARTICLE_CONTRACT_VALIDATION_FAILED` | The translated result fails the final NFA-6 contract. |

The fixture provider converts these failures to the existing safe `PROVIDER_DATA_INVALID` provider error. This prevents one malformed record from exposing raw provider content to callers or logs.

## Supporting another authorised field shape

`ArticleFieldMapping` separates provider key names from NewsFlow AI's standard field names. Tests demonstrate a second synthetic shape using fields such as `provider_id`, `title`, `article_link`, and `publication_date`.

A different mapping is not enough to enable a live provider. The provider also needs confirmed rights, a specific allowed-host policy, correct attribution, documented category rules, fixture-based contract tests, and written approval before any network access is implemented.

## Automated evidence

The focused tests cover:

- A valid record with whitespace, Unicode, URL, and UTC normalisation.
- A differently shaped provider record with an explicit mapping.
- Invalid and timezone-free publication dates.
- Missing required titles, URLs, and categories.
- Raw, encoded, and incomplete HTML-like content.
- Unsupported control characters.
- HTTP, credential-bearing, malformed, and unapproved-host URLs.
- Prohibited fields that must not enter the final model.
- Trusted attribution and provenance that untrusted input cannot replace.
- Optional descriptions and unknown categories.
- Rights denial before article fields are processed.
- Malformed top-level structures and safe errors that do not repeat restricted text.

Run the focused checks from `apps/api`:

```bash
pytest tests/test_article_normalisation.py
pytest tests/test_source_provider.py tests/test_cnn_adapter.py
```

Run the complete backend quality checks:

```bash
ruff check .
ruff format --check .
pytest
```

All automated records are synthetic and require no live news provider, network request, API key, or PostgreSQL database.

## Current limitations and next steps

- The active implementation is fixture-only.
- Live CNN access remains blocked by NFA-5 and ADR-001.
- No provider URL is fetched by the normalisation service.
- Normalised articles are not yet persisted through an ingestion repository or exposed through an article API endpoint.
- A future authorised source must receive a separate reviewed policy instead of changing the fixture policy into a guessed live contract.
