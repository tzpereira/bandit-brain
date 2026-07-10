import os

from alembic import context
from sqlalchemy import create_engine

config = context.config

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable must be set to run migrations.")

# No SQLAlchemy models yet — migrations are hand-written, so no autogenerate metadata.
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(url=DATABASE_URL, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
