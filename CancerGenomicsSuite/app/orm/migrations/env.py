import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic executes this file as a script, not as a module inside a package, so a
# relative import such as `from ..models import ...` has no parent package to
# resolve against and cannot work here. The project is imported by its full
# name instead, which needs the repository root on sys.path: four levels up,
# through migrations -> orm -> app -> CancerGenomicsSuite.
_repo_root = Path(__file__).resolve().parents[4]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from CancerGenomicsSuite.app import db  # noqa: E402

# Imported for its side effect: each db.Model subclass registers its table on
# db.metadata when the module loads. The models are Flask-SQLAlchemy models,
# so there is no declarative `Base` here -- db.metadata is the equivalent.
from CancerGenomicsSuite.app.orm import models  # noqa: E402,F401
from CancerGenomicsSuite.config.settings import settings  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
#
# disable_existing_loggers=False matters here. fileConfig's default disables
# every logger that already exists and is not named in alembic.ini -- and by
# this point the imports above have created the application's loggers, so the
# default would silence them for the rest of the process. Any warning the app
# emitted during a migration would vanish, and anything running migrations
# in-process (the test suite does) loses its logging from then on.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """The database the application itself connects to.

    DATABASE_URL in the environment wins, so a one-off target reads plainly:
    `DATABASE_URL=... alembic upgrade head`. Otherwise this is
    settings.get_database_url(), which is exactly what app/__init__.py hands to
    Flask-SQLAlchemy -- so migrations and the running app cannot quietly point
    at different databases. The ini's sqlalchemy.url is left empty on purpose
    and only consulted if both of those are unset.

    This used to import DATABASE_URL from config.settings, a name that module
    has never defined, so the file failed before any of it ran.
    """
    return (
        os.environ.get("DATABASE_URL")
        or settings.get_database_url()
        or config.get_main_option("sqlalchemy.url")
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
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
