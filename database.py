from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL
from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


engine = create_async_engine(DATABASE_URL, echo=True, future=True)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

