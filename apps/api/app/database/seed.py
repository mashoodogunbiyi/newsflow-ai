"""Load deterministic, synthetic development data into PostgreSQL."""

from collections.abc import Mapping
from typing import Any

from psycopg import Connection, connect

from app.core.config import Settings


class SeedSafetyError(RuntimeError):
    """Raised when seed data is requested outside an explicitly safe environment."""


SEED_IDS = {
    "user": "10000000-0000-4000-8000-000000000001",
    "source_profile": "10000000-0000-4000-8000-000000000002",
    "article": "10000000-0000-4000-8000-000000000003",
    "article_snapshot": "10000000-0000-4000-8000-000000000004",
    "generated_post": "10000000-0000-4000-8000-000000000005",
    "generation_run": "10000000-0000-4000-8000-000000000006",
    "generation_fact_1": "10000000-0000-4000-8000-000000000007",
    "generation_fact_2": "10000000-0000-4000-8000-000000000008",
    "post_version": "10000000-0000-4000-8000-000000000009",
    "post_claim_1": "10000000-0000-4000-8000-000000000010",
    "post_claim_2": "10000000-0000-4000-8000-000000000011",
    "saved_content": "10000000-0000-4000-8000-000000000012",
}

SEED_USER_EMAIL = "developer@example.invalid"
SEED_PASSWORD_HASH = "!disabled-synthetic-account-with-no-usable-password-000000000000"
SEED_ARTICLE_URL = "https://example.invalid/newsflow/synthetic-clean-energy"
SEED_ARTICLE_TEXT = (
    "Synthetic development fixture: A fictional research team reports that a "
    "prototype energy dashboard reduced wasted power by 18 percent during a "
    "controlled demonstration. The information is invented for local testing."
)


def validate_seed_settings(settings: Settings) -> None:
    """Require a non-production environment and a deliberate opt-in flag."""

    if settings.app_env not in {"development", "test"}:
        raise SeedSafetyError(
            "Seed data is allowed only when APP_ENV is development or test."
        )
    if not settings.seed_data_enabled:
        raise SeedSafetyError(
            "SEED_DATA_ENABLED must be true before development seed data is loaded."
        )


def _psycopg_url(settings: Settings) -> str:
    database_url = settings.require_database_url().get_secret_value()
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _execute_seed(connection: Connection[Any]) -> None:
    values: Mapping[str, str] = {
        **SEED_IDS,
        "user_email": SEED_USER_EMAIL,
        "password_hash": SEED_PASSWORD_HASH,
        "article_url": SEED_ARTICLE_URL,
        "article_text": SEED_ARTICLE_TEXT,
    }

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (id, email, password_hash, display_name, status)
            VALUES (
                %(user)s,
                %(user_email)s,
                %(password_hash)s,
                'Synthetic Developer',
                'disabled'
            )
            ON CONFLICT (id) DO NOTHING
            """,
            values,
        )
        cursor.execute(
            """
            INSERT INTO source_profiles (
                id,
                profile_key,
                source_name,
                contract_version,
                profile_type,
                status,
                authorisation_decision_ref,
                access_method,
                approved_at
            )
            VALUES (
                %(source_profile)s,
                'fixture-v1',
                'NewsFlow AI fixture source',
                '1.0',
                'fixture',
                'enabled',
                'NFA-SRC-AUTH-001',
                'fixture',
                '2026-10-25T00:00:00Z'
            )
            ON CONFLICT (id) DO NOTHING
            """,
            values,
        )
        cursor.execute(
            """
            INSERT INTO articles (
                id,
                source_profile_id,
                source_item_id,
                canonical_url,
                status
            )
            VALUES (
                %(article)s,
                %(source_profile)s,
                'synthetic-clean-energy-001',
                %(article_url)s,
                'active'
            )
            ON CONFLICT (id) DO NOTHING
            """,
            values,
        )
        cursor.execute(
            """
            INSERT INTO article_snapshots (
                id,
                article_id,
                snapshot_number,
                contract_version,
                source_name,
                title,
                publication_date,
                category,
                description,
                canonical_url,
                permitted_content_status,
                permitted_content_type,
                permitted_content_text,
                storage_allowed,
                display_allowed,
                ai_processing_allowed,
                derivative_output_allowed,
                rights_decision_ref,
                access_method,
                retention_rule,
                attribution_display_name,
                attribution_text,
                retrieved_at,
                content_fingerprint
            )
            VALUES (
                %(article_snapshot)s,
                %(article)s,
                1,
                '1.0',
                'NewsFlow AI synthetic fixture',
                'Fictional energy dashboard reduces waste in a test',
                '2026-10-20T09:00:00Z',
                'technology',
                'Invented metadata for database and interface development.',
                %(article_url)s,
                'available',
                'synthetic',
                %(article_text)s,
                true,
                true,
                true,
                true,
                'NFA-SRC-AUTH-001',
                'fixture',
                'development-only',
                'NewsFlow AI synthetic fixture',
                'Synthetic content created for NewsFlow AI development.',
                '2026-10-20T10:00:00Z',
                '67fc1ef8eea7413c8db1f483f0dbc5567e185f0f1c3761622a82be42ac31ea9f'
            )
            ON CONFLICT (id) DO NOTHING
            """,
            values,
        )
        cursor.execute(
            """
            UPDATE articles
            SET current_snapshot_id = %(article_snapshot)s
            WHERE id = %(article)s AND current_snapshot_id IS NULL
            """,
            values,
        )
        cursor.execute(
            """
            INSERT INTO generated_posts (
                id,
                user_id,
                article_snapshot_id,
                status
            )
            VALUES (
                %(generated_post)s,
                %(user)s,
                %(article_snapshot)s,
                'draft'
            )
            ON CONFLICT (id) DO NOTHING
            """,
            values,
        )
        cursor.execute(
            """
            INSERT INTO generation_runs (
                id,
                generated_post_id,
                generation_type,
                status,
                idempotency_key,
                provider,
                model,
                prompt_template_version,
                prompt_text,
                completed_at
            )
            VALUES (
                %(generation_run)s,
                %(generated_post)s,
                'post',
                'succeeded',
                'synthetic-seed-post-v1',
                'fixture-provider',
                'fixture-model',
                'seed-v1',
                'Create a synthetic professional post using only supplied fixture facts.',
                now()
            )
            ON CONFLICT (id) DO NOTHING
            """,
            values,
        )
        cursor.executemany(
            """
            INSERT INTO generation_facts (
                id,
                generation_run_id,
                fact_key,
                position,
                fact_text
            )
            VALUES (%(id)s, %(generation_run)s, %(key)s, %(position)s, %(text)s)
            ON CONFLICT (id) DO NOTHING
            """,
            [
                {
                    "id": SEED_IDS["generation_fact_1"],
                    "generation_run": SEED_IDS["generation_run"],
                    "key": "reported_reduction",
                    "position": 1,
                    "text": "The fictional test reported an 18 percent reduction.",
                },
                {
                    "id": SEED_IDS["generation_fact_2"],
                    "generation_run": SEED_IDS["generation_run"],
                    "key": "test_context",
                    "position": 2,
                    "text": "The result came from a controlled demonstration.",
                },
            ],
        )
        cursor.execute(
            """
            INSERT INTO post_versions (
                id,
                generated_post_id,
                generation_run_id,
                version_number,
                origin,
                tone,
                length_option,
                audience,
                hook,
                summary,
                insight,
                call_to_action,
                rendered_text,
                source_attribution,
                word_count,
                is_current,
                created_by_user_id
            )
            VALUES (
                %(post_version)s,
                %(generated_post)s,
                %(generation_run)s,
                1,
                'ai',
                'professional',
                'short',
                'technology_professionals',
                'Small experiments can reveal useful ways to reduce energy waste.',
                'A fictional development fixture reported an 18 percent reduction in a controlled demonstration.',
                'The value is not a real-world claim; it helps developers test evidence-linked content safely.',
                'What would you measure first in an energy-efficiency trial?',
                'Small experiments can reveal useful ways to reduce energy waste. A fictional development fixture reported an 18 percent reduction in a controlled demonstration. The value is not a real-world claim; it helps developers test evidence-linked content safely. What would you measure first in an energy-efficiency trial?',
                'Source: NewsFlow AI synthetic fixture.',
                47,
                true,
                %(user)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            values,
        )
        cursor.executemany(
            """
            INSERT INTO post_version_hashtags (post_version_id, position, hashtag)
            VALUES (%(post_version)s, %(position)s, %(hashtag)s)
            ON CONFLICT (post_version_id, position) DO NOTHING
            """,
            [
                {
                    "post_version": SEED_IDS["post_version"],
                    "position": 1,
                    "hashtag": "#SustainableTech",
                },
                {
                    "post_version": SEED_IDS["post_version"],
                    "position": 2,
                    "hashtag": "#EnergyEfficiency",
                },
                {
                    "post_version": SEED_IDS["post_version"],
                    "position": 3,
                    "hashtag": "#SyntheticDemo",
                },
            ],
        )
        cursor.executemany(
            """
            INSERT INTO post_claims (
                id,
                post_version_id,
                claim_key,
                position,
                claim_text
            )
            VALUES (%(id)s, %(post_version)s, %(key)s, %(position)s, %(text)s)
            ON CONFLICT (id) DO NOTHING
            """,
            [
                {
                    "id": SEED_IDS["post_claim_1"],
                    "post_version": SEED_IDS["post_version"],
                    "key": "reported_reduction",
                    "position": 1,
                    "text": "The fictional fixture reported an 18 percent reduction.",
                },
                {
                    "id": SEED_IDS["post_claim_2"],
                    "post_version": SEED_IDS["post_version"],
                    "key": "test_context",
                    "position": 2,
                    "text": "The result came from a controlled demonstration.",
                },
            ],
        )
        cursor.executemany(
            """
            INSERT INTO post_claim_sources (post_claim_id, generation_fact_id)
            VALUES (%(claim)s, %(fact)s)
            ON CONFLICT (post_claim_id, generation_fact_id) DO NOTHING
            """,
            [
                {
                    "claim": SEED_IDS["post_claim_1"],
                    "fact": SEED_IDS["generation_fact_1"],
                },
                {
                    "claim": SEED_IDS["post_claim_2"],
                    "fact": SEED_IDS["generation_fact_2"],
                },
            ],
        )
        cursor.execute(
            """
            INSERT INTO saved_content_items (
                id,
                user_id,
                generated_post_id,
                selected_post_version_id,
                library_title
            )
            VALUES (
                %(saved_content)s,
                %(user)s,
                %(generated_post)s,
                %(post_version)s,
                'Synthetic energy dashboard example'
            )
            ON CONFLICT (id) DO NOTHING
            """,
            values,
        )
        cursor.execute(
            """
            UPDATE generated_posts
            SET status = 'saved'
            WHERE id = %(generated_post)s AND status = 'draft'
            """,
            values,
        )


def _seed_counts(connection: Connection[Any]) -> dict[str, int]:
    table_ids = {
        "users": [SEED_IDS["user"]],
        "source_profiles": [SEED_IDS["source_profile"]],
        "articles": [SEED_IDS["article"]],
        "article_snapshots": [SEED_IDS["article_snapshot"]],
        "generated_posts": [SEED_IDS["generated_post"]],
        "generation_runs": [SEED_IDS["generation_run"]],
        "generation_facts": [
            SEED_IDS["generation_fact_1"],
            SEED_IDS["generation_fact_2"],
        ],
        "post_versions": [SEED_IDS["post_version"]],
        "post_claims": [SEED_IDS["post_claim_1"], SEED_IDS["post_claim_2"]],
        "saved_content_items": [SEED_IDS["saved_content"]],
    }
    counts: dict[str, int] = {}
    with connection.cursor() as cursor:
        for table, ids in table_ids.items():
            placeholders = ", ".join(["%s"] * len(ids))
            cursor.execute(
                f"SELECT count(*) FROM {table} WHERE id IN ({placeholders})",
                ids,
            )
            row = cursor.fetchone()
            counts[table] = int(row[0]) if row else 0

        cursor.execute(
            """
            SELECT count(*) FROM post_version_hashtags
            WHERE post_version_id = %s
            """,
            (SEED_IDS["post_version"],),
        )
        row = cursor.fetchone()
        counts["post_version_hashtags"] = int(row[0]) if row else 0

        cursor.execute(
            """
            SELECT count(*) FROM post_claim_sources
            WHERE post_claim_id IN (%s, %s)
            """,
            (SEED_IDS["post_claim_1"], SEED_IDS["post_claim_2"]),
        )
        row = cursor.fetchone()
        counts["post_claim_sources"] = int(row[0]) if row else 0
    return counts


def seed_database(settings: Settings | None = None) -> dict[str, int]:
    """Insert the synthetic fixture once and return its resulting row counts."""

    active_settings = settings or Settings()
    validate_seed_settings(active_settings)

    with connect(
        _psycopg_url(active_settings),
        connect_timeout=active_settings.database_connect_timeout_seconds,
    ) as connection:
        _execute_seed(connection)
        return _seed_counts(connection)


def main() -> None:
    """CLI entry point for development seeding."""

    counts = seed_database()
    summary = ", ".join(f"{table}={count}" for table, count in counts.items())
    print(f"Synthetic development seed is ready: {summary}")


if __name__ == "__main__":
    main()
