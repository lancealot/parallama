"""Test configuration and shared fixtures."""

from datetime import datetime, timedelta, timezone
from typing import Generator
from unittest.mock import MagicMock, create_autospec
import pytest
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from parallama.models.base import Base
from parallama.core.config import AuthConfig, DatabaseConfig, RedisConfig
from parallama.core.permissions import Permission, DefaultRoles
from parallama.models.role import Role
from parallama.models.user import User
from parallama.services.auth import AuthService
from parallama.services.api_key import APIKeyService
from parallama.services.role import RoleService


@pytest.fixture
def engine():
    """Create a SQLite in-memory database engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:
    """Create a new database session for a test."""
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing."""
    redis = create_autospec(Redis)
    redis.get.return_value = None
    redis.incr.return_value = 1
    redis.expire.return_value = True
    redis.setex.return_value = True
    return redis


@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    return MagicMock(
        auth=AuthConfig(
            jwt_secret_key="test_secret",
            access_token_expire_minutes=30,
            refresh_token_expire_days=30,
            refresh_token_rate_limit=5,
            refresh_token_reuse_window=60
        ),
        database=DatabaseConfig(
            url="sqlite:///:memory:",
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo_sql=False
        ),
        redis=RedisConfig(
            host="localhost",
            port=6379,
            db=0,
            password=None,
            max_connections=10,
            socket_timeout=5,
            connect_timeout=5
        )
    )


@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user."""
    user = User(username="testuser")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_roles(db_session) -> dict[str, Role]:
    """Create test roles."""
    roles = {}
    for role_name, role_data in DefaultRoles.get_all_roles().items():
        role = Role(
            name=role_name,
            permissions=role_data["permissions"],
            description=f"Test {role_name} role"
        )
        db_session.add(role)
        roles[role_name] = role
    
    db_session.commit()
    yield roles
    
    # Clean up roles
    for role in roles.values():
        db_session.delete(role)
    db_session.commit()


@pytest.fixture
def auth_service(db_session, mock_redis, mock_config) -> AuthService:
    """Create an AuthService instance for testing."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("parallama.services.auth.config", mock_config)
        return AuthService(db_session, mock_redis)


@pytest.fixture
def api_key_service(db_session, mock_redis) -> APIKeyService:
    """Create an APIKeyService instance for testing."""
    return APIKeyService(db_session, mock_redis)


@pytest.fixture
def role_service(db_session) -> RoleService:
    """Create a RoleService instance for testing."""
    return RoleService(db_session)
