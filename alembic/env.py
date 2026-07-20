from __future__ import annotations

from logging.config import fileConfig
import os
from alembic import context
from sqlalchemy import engine_from_config, pool

from app.models.base import Base
from app.core.config import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# Ce fichier est aussi exécuté à chaud, en process, par app.models.base.init_db()
# (démarrage d'uvicorn, scripts/seed_fixtures.py) — pas seulement via la CLI
# `alembic`. fileConfig() reconfigure le logger root d'après [logger_root] dans
# alembic.ini (niveau WARN, handler stderr dédié) quoi qu'il arrive, y compris
# avec disable_existing_loggers=False : ça écrasait silencieusement le logging
# déjà configuré par l'application hôte (niveau, RotatingFileHandler) pour le
# reste du process. On saute cette étape quand l'appelant programmatique le
# demande via config.attributes["configure_logger"] = False (pattern documenté
# par Alembic pour l'usage "programmatic").
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Load metadata for autogenerate support
settings = get_settings()

target_metadata = Base.metadata


def _get_database_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url

    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    env_user = os.getenv("POSTGRES_USER")
    env_password = os.getenv("POSTGRES_PASSWORD")
    env_host = os.getenv("POSTGRES_HOST")
    env_port = os.getenv("POSTGRES_PORT")
    env_db = os.getenv("POSTGRES_DB")

    if all([env_user, env_password, env_host, env_port, env_db]):
        return f"postgresql://{env_user}:{env_password}@{env_host}:{env_port}/{env_db}"

    return (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _get_database_url()
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
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = engine_from_config(
        configuration,
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
