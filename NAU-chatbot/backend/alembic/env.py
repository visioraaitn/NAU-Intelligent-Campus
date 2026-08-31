"""Async Alembic environment for the academic PostgreSQL schema."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.models.sqlalchemy import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    direct_url = os.getenv("DATABASE_URL")
    if direct_url:
        if direct_url.startswith("postgresql://"):
            return direct_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return direct_url

    keys = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_DB")
    values = {key: os.getenv(key) for key in keys}
    if all(values.values()):
        url = URL.create(
            "postgresql+asyncpg",
            username=values["POSTGRES_USER"],
            password=values["POSTGRES_PASSWORD"],
            host=values["POSTGRES_HOST"],
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=values["POSTGRES_DB"],
        )
        return url.render_as_string(hide_password=False)

    configured_url = config.get_main_option("sqlalchemy.url").strip()
    if configured_url:
        return configured_url
    raise RuntimeError(
        "Set DATABASE_URL or POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, and POSTGRES_DB"
    )


def _set_url() -> str:
    url = _database_url()
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_set_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_sync_migrations(connection: object) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    _set_url()
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_run_sync_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

