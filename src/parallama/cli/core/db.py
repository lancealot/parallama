"""Database utilities for CLI."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session
import redis

from parallama.core.database import init_db as init_core_db
from parallama.core.database import get_db as get_core_db
from parallama.core.database import get_redis as get_core_redis


def init_db() -> None:
    """Initialize database connection."""
    init_core_db()


def cleanup_db() -> None:
    """Clean up database resources."""
    pass


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = get_core_db()
    try:
        yield db
    finally:
        db.close()


def get_redis() -> redis.Redis:
    """Get Redis client."""
    return get_core_redis()
