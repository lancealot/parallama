"""Database configuration and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .config import config

# Create database engine with connection pooling
engine = create_engine(
    config.database.url,
    pool_size=config.database.pool_size,
    max_overflow=config.database.max_overflow,
    pool_timeout=config.database.pool_timeout,
    pool_recycle=config.database.pool_recycle,
    pool_pre_ping=True,  # Enable connection health checks
    echo=config.database.echo_sql  # SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db() -> Generator[Session, None, None]:
    """
    Get a database session from the connection pool.
    
    Yields:
        Session: Database session
        
    Example:
        ```python
        db = next(get_db())
        try:
            # Use the session
            users = db.query(User).all()
        finally:
            db.close()
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Yields:
        Session: Database session
        
    Example:
        ```python
        with get_db_context() as db:
            # Use the session
            users = db.query(User).all()
        # Session is automatically closed
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    Initialize the database.
    Creates all tables and sets up initial data.
    """
    from ..models.base import Base
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize default roles
    with get_db_context() as db:
        from ..services.role import RoleService
        role_service = RoleService(db)
        role_service.initialize_default_roles()
