from asyncio import current_task

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_scoped_session, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from fastapi import HTTPException, status, Depends
from sqlalchemy.exc import SQLAlchemyError
from typing import Generator

from src.config.config import Settings
from src.config.logger import logger

# Create sync engine
sync_engine = create_engine(
    Settings().SQLALCHEMY_DATABASE_URL,  # Use the original PostgreSQL URL
    pool_pre_ping=True,
    poolclass=NullPool,
    echo_pool=True,
    echo=False
)

# Create sync session factory
SessionLocal = sessionmaker(
    sync_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


def get_sync_db() -> Generator[Session, None, None]:
    """
    Synchronous database session dependency for FastAPI.

    Yields a synchronous database session and handles
    session management and error handling.
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    finally:
        db.close()

def convert_db_url_sync_to_async(sync_url: str) -> str:
    return sync_url.replace("postgresql://", "postgresql+asyncpg://")

async_engine = create_async_engine(
    convert_db_url_sync_to_async(Settings().SQLALCHEMY_DATABASE_URL),
    pool_pre_ping=True,
    poolclass=NullPool,
    echo_pool=True,
    echo=False
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Async DB dependency
async def get_async_db() -> Generator[AsyncSession, None, None]:
    """
    Asynchronous database session dependency for FastAPI.

    Yields an async database session and handles
    session management and error handling.
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except SQLAlchemyError as e:
            await db.rollback()  # Async rollback
            logger.error(f"Database session error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection error"
            )
        finally:
            await db.close()
