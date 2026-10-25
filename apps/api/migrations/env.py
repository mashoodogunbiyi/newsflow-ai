"""Alembic environment configured from NewsFlow AI's validated settings."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import Settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_migration_url() -> str:
    """Load the database URL without placing credentials in Alembic files."""

    database_url = Settings().require_database_url().get_secret_value()
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if not database_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Alembic requires a PostgreSQL psycopg DATABASE_URL.")
    return database_url


def run_migrations_offline() -> None:
    """Generate SQL without opening a database connection."""

    context.configure(
        url=get_migration_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations through a short-lived SQLAlchemy connection."""

    config.set_main_option(
        "sqlalchemy.url",
        get_migration_url().replace("%", "%%"),
    )
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
