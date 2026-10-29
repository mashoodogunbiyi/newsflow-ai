# Article Identity and Deduplication

## Purpose

NFA-31 gives every normalised article a stable provider-scoped identity and prevents repeated ingestion from creating duplicate PostgreSQL records. It also creates immutable snapshots when permitted metadata changes while preserving earlier snapshots used by generated content.

The implementation uses only original synthetic fixtures. It does not enable CNN access, inspect restricted fields, or retrieve extra content for deduplication.

## Beginner explanation

Think of an article record as a folder in a filing cabinet:

- The article row is the folder and keeps the same internal database ID.
- Each accepted metadata change creates a new snapshot inside that folder.
- Repeating exactly the same information does not create another folder or snapshot.
- Existing generated posts can remain attached to the older snapshot they actually used.

```text
Normalised NewsArticle
          |
          v
Provider ID available?
   | yes            | no
   v                v
Use provider ID   Hash the canonical URL
          \        /
           v      v
Provider-scoped identity plus canonical URL
                    |
                    v
PostgreSQL transaction and uniqueness constraints
                    |
          +---------+---------+
          |         |         |
       created    updated   skipped
```

Article titles are never identity keys. Two different stories can have similar titles, and one story's title can change after publication.

## Implementation

| File | Responsibility |
|---|---|
| `apps/api/app/services/article_identity.py` | Selects a stable provider ID or creates a deterministic canonical-URL fallback. |
| `apps/api/app/providers/normalisation.py` | Applies the fallback before the final NFA-6 article contract is validated. |
| `apps/api/app/repositories/articles.py` | Performs atomic lookup, insert, update, and skip operations. |
| `apps/api/app/services/article_deduplication.py` | Checks storage permission and coordinates idempotent persistence. |
| `apps/api/tests/test_article_deduplication.py` | Verifies the identity and deduplication rules with synthetic data. |
| `apps/api/tests/test_article_deduplication_integration.py` | Verifies the real constraints and concurrent behaviour in disposable PostgreSQL. |

## Identity strategy

### Preferred identity

When an authorised provider supplies a stable permitted article identifier, the primary identity is:

```text
(source_profile, source_item_id)
```

The source profile is part of the identity. Therefore, `shared-123` from `provider-one` and `shared-123` from `provider-two` are different identities.

### Canonical URL fallback

When a provider does not supply a stable identifier, the system uses:

```text
fixture-url- + SHA-256(normalised canonical URL)
```

This produces the same fallback for repeated ingestion of the same canonical URL without storing or inspecting extra source content. The fixture prefix also satisfies the approved NFA-6 identifier rules.

The fallback is created only after NFA-30 has validated and normalised the URL. It does not use the title, description, publication date, or article body. A future authorised provider must define its own approved fallback prefix and URL rules.

### Canonical URL rules

NFA-31 uses the exact canonical URL returned by NFA-30:

- HTTPS is required.
- The hostname is lowercase.
- Credentials and fragments are rejected or removed by normalisation.
- The path and query string are preserved.
- A missing path becomes `/`.
- Trailing slashes are not removed because a provider might treat two paths differently.
- Tracking parameters are not guessed or removed. A future provider contract must explicitly approve any query-parameter removal.

## Database safeguards

The original NFA-20 migration already created the correct constraints:

| Constraint | Columns | Purpose |
|---|---|---|
| `uq_articles_source_identity` | `source_profile_id, source_item_id` | Prevents the same provider identity from creating another article. |
| `uq_articles_canonical_url` | `canonical_url` | Prevents a second article from using the same canonical URL. |

NFA-31 uses these existing constraints and does not add a duplicate migration.

An application lookup alone cannot protect concurrent workers. The repository therefore:

1. Locks any matching article rows inside one transaction.
2. Attempts an atomic PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` when no row is visible.
3. Repeats the locked lookup if another transaction won the insert race.
4. Relies on the database constraints as the final duplicate guarantee.
5. Locks the stable article row before calculating the next snapshot number.
6. Inserts the snapshot and updates the current snapshot pointer in the same transaction.

This means two workers can ingest the same article at the same time, but only one stable article row is created.

## Created, updated, and skipped results

Every ingestion returns a structured result containing the stable `article_id`, selected `snapshot_id`, and one action:

| Action | Meaning |
|---|---|
| `created` | A new stable article and its first snapshot were inserted. |
| `updated` | The existing stable article received a new immutable snapshot. |
| `skipped` | The permitted normalised content already matches the current snapshot. |

The result contains no article text and can be safely counted by a future synchronisation job. NFA-31 does not yet add a persistent ingestion-audit table.

## Safe update rules

- The stable `articles.id` never changes during a metadata update.
- Existing snapshots are immutable and are not overwritten.
- A changed title, category, description, canonical URL, permitted content, attribution, rights value, or source modification time creates a new snapshot.
- A later retrieval timestamp by itself is skipped, preventing unnecessary snapshot growth.
- The new snapshot becomes `articles.current_snapshot_id`.
- Generated posts linked to an earlier snapshot remain linked to that exact snapshot.

The repository calculates a SHA-256 fingerprint from the permitted normalised fields and excludes `retrieved_at`. The fingerprint is stored only for the synthetic profile, where this use is permitted. A future provider policy must expressly permit fingerprinting before this behaviour is reused.

## Identity conflicts

The system does not silently merge uncertain records. It raises a safe conflict when:

- A canonical URL is already attached to a different source identity.
- The source identity and canonical URL point to two different existing rows.

The error message contains no title, article text, provider response, or credential. A future synchronisation workflow can quarantine the source reference for review.

## Automated evidence

The fast tests verify:

- Provider IDs are preferred and scoped by provider.
- Missing provider IDs produce a repeatable URL-hash fallback.
- Normalisation applies the fallback before Pydantic contract validation.
- First ingestion creates an article.
- Repeated ingestion skips without adding a row or snapshot.
- Retrieval time alone does not cause an update.
- Permitted metadata changes create a new snapshot while retaining the stable article ID and old snapshot.
- Similar titles with different source identities remain separate.
- Contradictory source identities and URLs fail safely.
- Concurrent ingestion creates one article.
- Storage permission is checked before repository use.

Run them from `apps/api`:

```bash
pytest tests/test_article_deduplication.py
```

The PostgreSQL test is destructive by design and requires a separate disposable database whose name contains `newsflow_article_deduplication_test`:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_article_deduplication_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_article_deduplication_integration.py
```

Never point this integration test at the normal development database, a shared database, staging, or production. It rebuilds the named test database schema before the test and removes it afterwards.

The PostgreSQL proof verifies the existing uniqueness constraints, repeated ingestion, metadata updates, retained snapshot relationships, similar titles, and simultaneous insert attempts.

Run the complete normal quality checks with:

```bash
ruff check .
ruff format --check .
pytest
```

The normal suite skips the destructive integration test unless both safety variables are explicitly supplied.

## Current limitations

- The active source profile remains `fixture-v1`.
- Live CNN access remains blocked by NFA-5 and ADR-001.
- The repository is not yet connected to a scheduled synchronisation job or public article endpoint.
- The action result is returned to the caller but is not stored in a separate ingestion-audit table.
- Cross-provider canonical URL policy must be reviewed before a second authorised provider is enabled because the approved NFA-20 schema currently treats canonical URL as globally unique.
