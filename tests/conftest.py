"""Test configuration and fixtures."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from parallama.core.database import Base
import uuid
from parallama.models.user import User
from parallama.models.api_key import APIKey
from parallama.models.rate_limit import GatewayRateLimit, GatewayUsageLog
from parallama.models.user_role import UserRole

@pytest.fixture
def basic_role(db_session):
    """Create a basic user role."""
    # First check if role exists
    role = db_session.query(UserRole).filter_by(name="basic").first()
    if not role:
        role = UserRole(
            id=str(uuid.uuid4()),  # Convert UUID to string
            name="basic",
            permissions=["use_api"]
        )
        db_session.add(role)
        db_session.commit()
    return role

@pytest.fixture(scope="session")
def engine():
    """Create database engine for testing."""
    # Create a new engine for testing
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create all tables
    Base.metadata.create_all(test_engine)
    
    return test_engine

@pytest.fixture
def db_session(engine):
    """Create database session for testing."""
    # Create a new session factory bound to the test engine
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    
    # Start a nested transaction
    session.begin_nested()
    
    try:
        yield session
    finally:
        session.rollback()  # Rollback the nested transaction
        session.close()

@pytest.fixture(autouse=True)
def cleanup_db(engine):
    """Clean up database after each test."""
    yield
    # Drop and recreate all tables
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    # Create pipeline mock first
    pipeline = MagicMock()
    pipeline.execute.return_value = [0] * 8  # Default values for rate limit checks
    
    # Create Redis mock
    redis = MagicMock(spec=Redis)
    redis.get.return_value = None
    redis.setex.return_value = True
    redis.delete.return_value = True
    redis.pipeline.return_value = pipeline
    redis.ping.return_value = True
    return redis

@pytest.fixture
def test_user(db_session):
    """Create test user."""
    user = User(
        username="test_user",
        password_hash="test_hash",
        role="basic"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_api_key(db_session, test_user):
    """Create test API key."""
    # First check if key exists
    key_model = db_session.query(APIKey).filter_by(user_id=test_user.id).first()
    if not key_model:
        key = APIKey.generate_key()
        key_model = APIKey(
            user_id=test_user.id,  # BaseModel will handle UUID conversion
            description="Test key"
        )
        key_model.set_key(key)
        db_session.add(key_model)
        db_session.commit()
    return key_model

@pytest.fixture
def test_rate_limits(db_session, test_user):
    """Create test rate limits."""
    # First check if limits exist
    limits = db_session.query(GatewayRateLimit).filter_by(user_id=test_user.id).first()
    if not limits:
        limits = GatewayRateLimit(
            user_id=test_user.id,  # BaseModel will handle UUID conversion
            gateway_type="ollama",
            token_limit_hourly=1000,
            token_limit_daily=10000,
            request_limit_hourly=100,
            request_limit_daily=1000
        )
        db_session.add(limits)
        db_session.commit()
    return limits

@pytest.fixture
def test_usage_log(db_session, test_user):
    """Create test usage log."""
    # First check if log exists
    log = db_session.query(GatewayUsageLog).filter_by(user_id=test_user.id).first()
    if not log:
        log = GatewayUsageLog(
            user_id=test_user.id,  # BaseModel will handle UUID conversion
            gateway_type="ollama",
            endpoint="/test",
            tokens_used=100,
            model_name="test-model",
            request_duration=500,
            status_code=200
        )
        db_session.add(log)
        db_session.commit()
    return log

@pytest.fixture
def mock_request():
    """Create mock request with state."""
    request = MagicMock()
    request.state = MagicMock()
    request.state.user_id = None
    request.state.tokens_used = None
    request.state.model_name = None
    request.state.error_message = None
    request.state.status_code = None
    request.url.path = "/test"
    return request
