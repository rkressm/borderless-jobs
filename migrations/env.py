"""Alembic environment; the connection URL is supplied by the caller."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


def require_database_url() -> str:
    database_url = os.environ.get("BORDERLESS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("BORDERLESS_DATABASE_URL is required for migrations")
    return database_url


def run_migrations_offline() -> None:
    context.configure(
        url=require_database_url(),
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(require_database_url(), poolclass=NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=None)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
