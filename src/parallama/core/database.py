"""Database configuration and session management."""

from contextlib import contextmanager
from typing import Generator
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database configuration
SQLALCHEMY_DATABASE_URL = "postgresql://parallama:development@localhost:5432/parallama"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis configuration
REDIS_URL = "redis://localhost:6379/0"
redis_client = redis.from_url(REDIS_URL)

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

def get_redis() -> Generator[redis.Redis, None, None]:
    """Get Redis client.
    
    Yields:
        redis.Redis: Redis client
    """
    try:
        yield redis_client
    finally:
        redis_client.close()

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

def get_redis_client():
    """Get Redis client.
    
    Returns:
        redis.Redis: Redis client
    """
    return redis_client
