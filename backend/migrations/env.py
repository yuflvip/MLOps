import os
from pathlib import Path

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.infrastructure.config import (
    CONFIG_PATH_ENV_VAR,
    default_config_path,
    load_settings,
    resolve_config_path,
)
from app.infrastructure.db import Base
from app.infrastructure.db import normalize_database_url


config = context.config
resolved_config_path = resolve_config_path(
    os.getenv(CONFIG_PATH_ENV_VAR)
    or config.get_main_option("mlops.config_path")
    or default_config_path()
)
settings = load_settings(resolved_config_path)
database_url = normalize_database_url(
    settings.database.url,
    Path(resolved_config_path).resolve().parent.parent,
)
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None and config.attributes.get("configure_logging", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        context.configure(connection=supplied_connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
