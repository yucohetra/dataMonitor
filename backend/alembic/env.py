import os
import sys

# NOTE:
# - Ensures the project root (/app) is discoverable for imports such as "from app.*".
# - Keeps Alembic execution consistent across Docker and local environments.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.config import settings
from app.db.base import Base
from app.models import role, user, record, system_log  # noqa: F401

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    # NOTE:
    # - Alembic uses a synchronous driver for migrations.
    return settings.alembic_sync_database_url


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
