"""Database session management for CLI commands."""
from sqlalchemy.orm import Session
from redis import Redis

from parallama.core.database import get_db as get_core_db
from parallama.core.redis import get_redis as get_core_redis

# Global session objects
_db_session: Session = None
_redis_client: Redis = None

def init_db():
    """Initialize database and Redis connections."""
    global _db_session, _redis_client
    
    # Create database session
    _db_session = next(get_core_db())
    
    # Create Redis client
    _redis_client = next(get_core_redis())

def get_db() -> Session:
    """Get the current database session."""
    global _db_session
    if _db_session is None:
        init_db()
    return _db_session

def get_redis() -> Redis:
    """Get the current Redis client."""
    global _redis_client
    if _redis_client is None:
        init_db()
    return _redis_client

def cleanup_db():
    """Cleanup database and Redis connections."""
    global _db_session, _redis_client
    
    if _db_session is not None:
        _db_session.close()
        _db_session = None
    
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
