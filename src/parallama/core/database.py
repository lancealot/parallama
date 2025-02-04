"""Database configuration and session management."""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from .config import settings
from .redis import get_redis

__all__ = ['get_db', 'get_redis', 'db_transaction', 'init_db', 'drop_db', 'reset_db', 'get_engine', 'get_base', 'get_session_class']

# Create database engine
engine = create_engine(
    settings.database.url,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    pool_recycle=settings.database.pool_recycle,
    echo=settings.database.echo_sql
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Get database session.
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def db_transaction() -> Generator[Session, None, None]:
    """Context manager for database transactions.
    
    Yields:
        Session: Database session
        
    Example:
        with db_transaction() as db:
            db.add(some_model)
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()

def init_db() -> None:
    """Initialize database schema."""
    Base.metadata.create_all(bind=engine)

def drop_db() -> None:
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)

def reset_db() -> None:
    """Reset database by dropping and recreating all tables."""
    drop_db()
    init_db()

def get_engine():
    """Get SQLAlchemy engine.
    
    Returns:
        Engine: SQLAlchemy engine
    """
    return engine

def get_base():
    """Get SQLAlchemy base class.
    
    Returns:
        DeclarativeMeta: SQLAlchemy base class
    """
    return Base

def get_session_class():
    """Get SQLAlchemy session class.
    
    Returns:
        sessionmaker: SQLAlchemy session class
    """
    return SessionLocal
