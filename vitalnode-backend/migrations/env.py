"""
Alembic environment configuration.
Uses a SYNCHRONOUS engine (psycopg2) for migrations.
The application itself uses asyncpg at runtime - that is separate.
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.db.database import Base

# Import ALL models so Alembic can detect every table
from app.models import user, patient, encounter, assessment, vital       # noqa
from app.models import recommendation, audit, notification, device, queue_entry  # noqa

settings_obj = get_settings()

config = context.config

# Use the SYNC database URL (postgresql://... not postgresql+asyncpg://...)
config.set_main_option("sqlalchemy.url", settings_obj.database_sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL without connecting to the database."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the live database using a sync connection."""
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
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
