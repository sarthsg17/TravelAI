from models import Base  # Ensure you are importing Base correctly
from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

# Import database URL
from config import DATABASE_URL

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Ensure metadata is provided
target_metadata = Base.metadata  # This should exist in models.py

def run_migrations_online():
    """Run migrations in async mode."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
        future=True
    )

    async def run_async_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda sync_conn: context.configure(
                    connection=sync_conn,
                    target_metadata=target_metadata,
                    compare_type=True,
                    include_schemas=True
                )
            )
            await connection.run_sync(lambda sync_conn: context.run_migrations())

    asyncio.run(run_async_migrations())

run_migrations_online()
