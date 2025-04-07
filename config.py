# config.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # Removed sslmode

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# For dependency injection
async def get_db():
    async with SessionLocal() as session:
        yield session

# Add your Google API key

GOOGLE_API_KEY = "AIzaSyCGr2Pv8_aV9uxAODgutLdYGfqRdZWaYk8"
