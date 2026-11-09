from logging.config import fileConfig

from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  # Import all models and register them in Base.metadata
from alembic import context
from app.config import settings
from app.models.base import Base

# Alembic Config object
config = context.config

# Configure Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy metadata used by Alembic autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""

    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live database connection."""

    connectable = create_engine(
        settings.database_url,
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

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
