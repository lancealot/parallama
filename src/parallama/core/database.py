"""Database configuration."""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import redis

from .config import get_settings

# Create base class for models
Base = declarative_base()

# Initialize these after settings are loaded
engine = None
SessionLocal = None
redis_client = None


def init_db():
    """Initialize database connection."""
    global engine, SessionLocal, redis_client
    
    if engine is None:
        engine = create_engine(get_settings().database.url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        redis_client = redis.from_url(get_settings().redis.url)


def get_db() -> Session:
    """Get database session."""
    if SessionLocal is None:
        init_db()
    return SessionLocal()


@contextmanager
def db_session():
    """Context manager for database sessions."""
    db = get_db()
    try:
        yield db
    finally:
        db.close()


def get_redis() -> redis.Redis:
    """Get Redis client."""
    if redis_client is None:
        init_db()
    return redis_client
