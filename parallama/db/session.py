"""Database session management and configuration."""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

class DatabaseSettings:
    """Database configuration settings."""
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout

    @property
    def database_url(self) -> str:
        """Generate database URL from settings."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

def create_engine_from_settings(settings: DatabaseSettings) -> Engine:
    """Create SQLAlchemy engine from settings."""
    return create_engine(
        settings.database_url,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        pool_pre_ping=True  # Enable connection health checks
    )

class DatabaseSessionManager:
    """Manages database sessions and connections."""
    def __init__(self, settings: DatabaseSettings):
        self.engine = create_engine_from_settings(settings)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def dispose_engine(self) -> None:
        """Dispose of the engine and connection pool."""
        self.engine.dispose()
