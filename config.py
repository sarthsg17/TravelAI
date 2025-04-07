from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# Your NeonDB connection string
DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_o67wFIalfbsc@ep-withered-union-a1fizbkz-pooler.ap-southeast-1.aws.neon.tech/neondb?ssl=require"
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False  # Remove in production
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

GOOGLE_API_KEY = "AIzaSyCGr2Pv8_aV9uxAODgutLdYGfqRdZWaYk8"
