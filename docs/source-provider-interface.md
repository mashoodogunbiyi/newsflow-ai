# News Source Provider Interface

## Purpose

NFA-28 defines the provider-neutral boundary used to discover and retrieve authorised news information. The boundary lets NewsFlow AI use one consistent article structure even when external providers use different field names, pagination formats, or error responses.

The current implementation uses only original synthetic fixtures. It does not connect to CNN, scrape a website, bypass access controls, or make a live news request.

## Beginner explanation

Think of the interface as a standard electrical socket. News providers may be built differently, but each adapter must supply information through the same socket. The rest of NewsFlow AI connects to the socket rather than directly to a particular provider.

```text
Synthetic fixture or future authorised provider
                    |
                    v
           Provider-specific adapter
                    |
                    v
          NewsProvider interface
                    |
                    v
        Standard NewsArticle model
                    |
                    v
          NewsFlow AI application
```

This separation prevents CNN-specific field names or response formats from spreading through the application.

## Implementation structure

| File | Responsibility |
|---|---|
| `apps/api/app/providers/base.py` | Defines the typed `NewsProvider` protocol. |
| `apps/api/app/providers/models.py` | Defines strict provider-neutral requests, pages, article fields, attribution, and rights data. |
| `apps/api/app/providers/exceptions.py` | Defines stable and safe errors for callers. |
| `apps/api/app/providers/fixture_provider.py` | Maps original synthetic records into the approved NFA-6 contract. |
| `apps/api/app/providers/cnn_adapter.py` | Provides the NFA-29 disabled CNN boundary required by the active No-Go decision. |
| `apps/api/app/providers/factory.py` | Enables only the provider selected through validated configuration. |
| `apps/api/app/providers/service.py` | Demonstrates a consumer that depends only on the interface. |
| `apps/api/tests/test_source_provider.py` | Verifies mapping, validation, errors, pagination, replacement, and authorisation controls. |

## Provider agreement

Every provider supplies:

- A stable, non-secret provider identifier.
- A capabilities description.
- `fetch_articles(query)` for article discovery.
- `fetch_article(source_item_id)` for one article.
- A `ProviderPage` containing only validated `NewsArticle` records.
- Documented `ProviderError` failures instead of raw provider exceptions.

Python's `Protocol` provides structural typing. A provider does not inherit from a framework base class, but it must provide the required properties and asynchronous methods with the correct types.

## Standard article model

The `NewsArticle` model implements the approved NFA-6 fixture-first contract. It includes:

- Contract version and source profile.
- Stable source item identifier and source name.
- Title, publication date, category, optional description, and canonical HTTPS URL.
- Explicit permitted content and AI-processing flags.
- Required attribution wording and canonical URL.
- Rights decision, access method, storage permission, display permission, expiry, and retention rule.
- Retrieval and modification timestamps.

Pydantic rejects missing required values, unknown fields, unsafe URLs, invalid timestamps, HTML-like markup, inconsistent permission states, and mismatched attribution URLs. Provider-specific data never passes directly into the database, frontend, or future OpenAI integration.

## Pagination and incremental retrieval

`ArticleQuery` accepts:

- `limit` from 1 to 100.
- An optional opaque `cursor` returned by the previous page.
- An optional timezone-aware `published_after` timestamp.

A cursor is a bookmark, not a value the frontend should interpret or modify. The fixture provider verifies that a cursor belongs to itself before using it. Its capabilities declare support for pagination and incremental date filtering.

## Safe provider errors

| Code | Meaning | Retryable |
|---|---|---:|
| `SOURCE_NOT_AUTHORISED` | No approved source mode is enabled. | No |
| `PROVIDER_UNAVAILABLE` | The provider is temporarily unavailable. | Yes |
| `PROVIDER_DATA_INVALID` | Provider data failed the approved contract. | No |
| `INVALID_PROVIDER_CURSOR` | A pagination cursor is invalid or belongs to another provider. | No |
| `ARTICLE_NOT_FOUND` | The provider has no matching article. | No |

Errors expose a safe message and never include credentials, raw responses, or restricted source text. The original exception remains available only as an internal exception cause for controlled server logging.

## Fixture provider

The fixture provider deliberately uses internal names such as `headline`, `published_at`, and `record_key`. It maps those names to `title`, `publication_date`, and `source_item_id`. This proves that application consumers do not need to know a provider's private format.

All bundled records:

- Are fictional and original to NewsFlow AI.
- Use the reserved `example.invalid` domain.
- Identify themselves as synthetic fixtures.
- Carry the approved fixture rights decision.
- Make no network request.
- Contain no copied CNN material or real personal information.

`NEWS_SOURCE_MODE` is `disabled` when no value is supplied directly to the settings class. Local development explicitly selects `fixture` through the ignored `.env` file or safe `.env.example`. No live mode exists.

## Adding a future authorised provider

A developer must not add a live provider until NFA-5, NFA-6, and ADR-001 are formally revised with written authorisation. After approval:

1. Add the provider-specific response parser in `apps/api/app/providers`.
2. Map only approved fields into the standard models.
3. Implement every `NewsProvider` property and method.
4. Convert provider failures into the safe provider error types.
5. Keep credentials in validated server-side environment configuration.
6. Add an approved source mode to the settings and provider factory.
7. Add contract, mapping, pagination, error, rate-limit, and rights tests.
8. Confirm that no raw provider response reaches application services or logs.

The `ArticleDiscoveryService` will continue to work without provider-specific changes because it depends only on `NewsProvider`.

NFA-29 adds a disabled `CnnSourceAdapter` while the No-Go decision remains active. It implements the interface but raises `SOURCE_NOT_AUTHORISED` before networking. It does not contain an endpoint, credential mechanism, guessed CNN response, or live mode. See the [disabled CNN adapter record](cnn-adapter.md).

## Running the tests

From `apps/api` with the virtual environment active:

```bash
pytest tests/test_source_provider.py
ruff check .
ruff format --check .
pytest
```

These tests use synthetic in-memory data. They require no live provider, network access, API key, or PostgreSQL database.

## Current decision

- Jira issue: NFA-28
- Parent: NFA-27
- Project-plan task: T3.1 - Define a source-provider interface
- Active implementation: synthetic fixture provider
- Live CNN integration: not authorised and not implemented
- NFA-29 status: disabled safety skeleton implemented; live adapter remains blocked
