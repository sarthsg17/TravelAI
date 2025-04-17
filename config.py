# config.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # Removed sslmode


# Use SQLite for Hugging Face deployment
DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)



# For dependency injection
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Add your Google API key

# GOOGLE_API_KEY = "AIzaSyCGr2Pv8_aV9uxAODgutLdYGfqRdZWaYk8"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyCGr2Pv8_aV9uxAODgutLdYGfqRdZWaYk8")
FOURSQUARE_API_KEY: str = "fsq3Uz0C6s6XLGU4xB+lQOfNa0Q/BPxiV5edWxVY9wpZV/I= "