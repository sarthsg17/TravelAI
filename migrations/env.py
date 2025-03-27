from models import Base  # Ensure you are importing Base correctly
from alembic import context
from sqlalchemy import engine_from_config, pool

# Import database URL
from config import DATABASE_URL

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Ensure metadata is provided
target_metadata = Base.metadata  # This should exist in models.py

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,  # Ensure metadata is passed
        )

        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
