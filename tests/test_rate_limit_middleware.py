"""Tests for the rate limiting middleware."""

import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
import redis
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from redis import Redis, ConnectionError
from sqlalchemy.orm import Session
from starlette.datastructures import State, MutableHeaders
from starlette.types import Scope

from parallama.middleware.rate_limit import RateLimitMiddleware
from parallama.models.rate_limit import GatewayRateLimit, GatewayUsageLog
from parallama.models.user import User

class MockRequest(Request):
    def __init__(self, path: str, method: str = "GET"):
        scope: Scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": MutableHeaders(),
        }
        super().__init__(scope)
        self.state = State()

@pytest.fixture(autouse=True)
def mock_redis():
    """Create a mock Redis client."""
    redis_client = MagicMock(spec=Redis)
    pipeline = MagicMock()
    pipeline.execute.return_value = ["0", "0", "0", "0"]  # Default values for get operations
    redis_client.pipeline.return_value = pipeline
    redis_client.ping.return_value = True  # Mock successful ping
    
    def mock_get(key):
        return "0"
    redis_client.get.side_effect = mock_get
    
    with patch('parallama.services.rate_limit.get_redis', return_value=iter([redis_client])):
        yield redis_client

@pytest.fixture
def mock_request():
    """Create a mock request with state."""
    request = MockRequest("/ollama/v1/chat/completions")
    request.state = State()
    return request

@pytest.fixture
def app(db_session: Session) -> FastAPI:
    """Create a test FastAPI application."""
    app = FastAPI()

    def get_user_id(request: Request) -> uuid.UUID:
        """Mock user ID extraction."""
        return getattr(request.state, "user_id", None)

    @app.get("/ollama/v1/chat/completions")
    async def test_endpoint():
        """Test endpoint."""
        return {"status": "ok"}

    @app.get("/ollama/v1/test")
    async def test_endpoint2():
        """Test endpoint."""
        return {"status": "ok"}

    @app.get("/openai/v1/test")
    async def test_endpoint3():
        """Test endpoint."""
        return {"status": "ok"}

    @app.get("/ollama/v1/error")
    async def error_endpoint():
        """Test error endpoint."""
        raise HTTPException(status_code=500, detail="Test error")

    app.add_middleware(
        RateLimitMiddleware,
        get_user_id=get_user_id,
        get_gateway_type=RateLimitMiddleware.get_gateway_type_from_path
    )

    return app

@pytest.fixture
def client(app: FastAPI) -> Generator:
    """Create a test client."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        username="test_user",
        password_hash="test_hash",
        role="basic"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def rate_limits(db_session: Session, user: User) -> GatewayRateLimit:
    """Create test rate limits."""
    limits = GatewayRateLimit(
        id=uuid.uuid4(),
        user_id=user.id,
        gateway_type="ollama",
        token_limit_hourly=1000,
        token_limit_daily=10000,
        request_limit_hourly=100,
        request_limit_daily=1000
    )
    db_session.add(limits)
    db_session.commit()
    return limits

async def test_rate_limit_middleware_success(
    client: TestClient,
    user: User,
    rate_limits: GatewayRateLimit,
    db_session: Session
):
    """Test successful request with rate limiting."""
    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/ollama/v1/chat/completions")
        request.state.user_id = user.id
        request.state.start_time = datetime.utcnow().timestamp()
        request.state.end_time = datetime.utcnow().timestamp() + 0.5
        request.state.tokens_used = 50
        request.state.model_name = "llama2"
        return request

    with patch("fastapi.Request", mock_request_factory):
        response = client.get("/ollama/v1/chat/completions")
        assert response.status_code == 200

async def test_rate_limit_middleware_exceeded(
    client: TestClient,
    user: User,
    db_session: Session
):
    """Test request when rate limit is exceeded."""
    # Create strict rate limits
    limits = GatewayRateLimit(
        id=uuid.uuid4(),
        user_id=user.id,
        gateway_type="ollama",
        token_limit_hourly=10,  # Very low limit
        token_limit_daily=100,
        request_limit_hourly=5,
        request_limit_daily=50
    )
    db_session.add(limits)
    db_session.commit()

    # Mock Redis to simulate exceeded limits
    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = ["100", "0", "0", "0"]  # Exceeded hourly token limit
    mock_redis = MagicMock(spec=Redis)
    mock_redis.pipeline.return_value = mock_pipeline
    mock_redis.ping.return_value = True

    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/ollama/v1/chat/completions")
        request.state.user_id = user.id
        request.state.start_time = datetime.utcnow().timestamp()
        request.state.end_time = datetime.utcnow().timestamp() + 0.5
        request.state.tokens_used = 50
        request.state.model_name = "llama2"
        return request

    with patch("fastapi.Request", mock_request_factory), \
         patch('parallama.services.rate_limit.get_redis', return_value=iter([mock_redis])):
        response = client.get("/ollama/v1/chat/completions")
        assert response.status_code == 429
        assert "token limit" in response.json()["detail"].lower()

async def test_rate_limit_middleware_no_limits(
    client: TestClient,
    user: User
):
    """Test request when no rate limits are configured."""
    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/ollama/v1/chat/completions")
        request.state.user_id = user.id
        request.state.start_time = datetime.utcnow().timestamp()
        request.state.end_time = datetime.utcnow().timestamp() + 0.5
        request.state.tokens_used = 1000
        request.state.model_name = "llama2"
        return request

    with patch("fastapi.Request", mock_request_factory):
        response = client.get("/ollama/v1/chat/completions")
        assert response.status_code == 200

async def test_rate_limit_middleware_non_api_route(
    client: TestClient,
    user: User
):
    """Test that non-API routes bypass rate limiting."""
    @client.app.get("/health")
    async def health():
        return {"status": "ok"}

    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/health")
        request.state.user_id = user.id
        return request

    with patch("fastapi.Request", mock_request_factory):
        response = client.get("/health")
        assert response.status_code == 200

async def test_rate_limit_middleware_error_logging(
    client: TestClient,
    user: User,
    db_session: Session
):
    """Test that errors are properly logged."""
    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/ollama/v1/error")
        request.state.user_id = user.id
        request.state.start_time = datetime.utcnow().timestamp()
        request.state.end_time = datetime.utcnow().timestamp() + 0.5
        request.state.error_message = "Test error"
        return request

    with patch("fastapi.Request", mock_request_factory):
        response = client.get("/ollama/v1/error")
        assert response.status_code == 500

        # Check error was logged
        logs = db_session.query(GatewayUsageLog).filter_by(
            user_id=user.id,
            error_message="Test error"
        ).all()
        assert len(logs) == 1
        assert logs[0].status_code == 500

async def test_rate_limit_middleware_redis_error(
    client: TestClient,
    user: User,
    db_session: Session
):
    """Test handling of Redis connection errors."""
    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/ollama/v1/chat/completions")
        request.state.user_id = user.id
        request.state.start_time = datetime.utcnow().timestamp()
        return request

    # Make Redis pipeline raise ConnectionError
    mock_redis_error = MagicMock(spec=Redis)
    mock_redis_error.ping.side_effect = redis.ConnectionError("Connection refused")

    with patch("fastapi.Request", mock_request_factory), \
         patch('parallama.services.rate_limit.get_redis', return_value=iter([mock_redis_error])):
        response = client.get("/ollama/v1/chat/completions")
        assert response.status_code == 503
        assert "service" in response.json()["detail"].lower()

async def test_rate_limit_middleware_missing_user(client: TestClient):
    """Test request handling when user ID is missing."""
    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/ollama/v1/chat/completions")
        request.state = State()  # Empty state
        return request

    with patch("fastapi.Request", mock_request_factory):
        response = client.get("/ollama/v1/chat/completions")
        assert response.status_code == 200  # Should bypass rate limiting

async def test_rate_limit_middleware_invalid_gateway(
    client: TestClient,
    user: User
):
    """Test handling of invalid gateway types."""
    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/invalid/v1/chat/completions")
        request.state.user_id = user.id
        return request

    @client.app.get("/invalid/v1/chat/completions")
    async def invalid_endpoint():
        return {"status": "ok"}

    with patch("fastapi.Request", mock_request_factory):
        response = client.get("/invalid/v1/chat/completions")
        assert response.status_code == 200  # Should bypass rate limiting

async def test_rate_limit_middleware_concurrent_requests(
    client: TestClient,
    user: User,
    rate_limits: GatewayRateLimit
):
    """Test handling of concurrent requests."""
    import asyncio

    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/ollama/v1/chat/completions")
        request.state.user_id = user.id
        request.state.start_time = datetime.utcnow().timestamp()
        request.state.end_time = datetime.utcnow().timestamp() + 0.1
        request.state.tokens_used = 10
        return request

    async def make_request():
        with patch("fastapi.Request", mock_request_factory):
            return client.get("/ollama/v1/chat/completions")

    # Make concurrent requests
    tasks = [make_request() for _ in range(5)]
    responses = await asyncio.gather(*tasks)

    # All requests should succeed since they're within limits
    assert all(r.status_code == 200 for r in responses)

async def test_rate_limit_middleware_request_timing(
    client: TestClient,
    user: User,
    db_session: Session
):
    """Test accurate request timing recording."""
    start_time = datetime.utcnow().timestamp()
    
    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/ollama/v1/chat/completions")
        request.state.user_id = user.id
        request.state.start_time = start_time
        request.state.end_time = start_time + 1.5  # 1.5 seconds
        return request

    with patch("fastapi.Request", mock_request_factory):
        response = client.get("/ollama/v1/chat/completions")
        assert response.status_code == 200

        # Check timing was recorded
        log = db_session.query(GatewayUsageLog).first()
        assert log is not None
        assert log.request_duration == 1500  # Should be in milliseconds

async def test_state_cleanup(client: TestClient, user: User):
    """Test request state cleanup after processing."""
    def mock_request_factory(*args, **kwargs):
        request = MockRequest("/ollama/v1/chat/completions")
        request.state.user_id = user.id
        request.state.start_time = datetime.utcnow().timestamp()
        request.state.tokens_used = 50
        request.state.model_name = "llama2"
        request.state.custom_data = "should be cleaned"
        return request

    with patch("fastapi.Request", mock_request_factory):
        response = client.get("/ollama/v1/chat/completions")
        assert response.status_code == 200

        # State should be cleaned after request
        request = mock_request_factory()
        assert not hasattr(request.state, "custom_data")
        assert not hasattr(request.state, "tokens_used")

async def test_custom_gateway_handlers(client: TestClient, user: User):
    """Test custom gateway type extraction."""
    app = FastAPI()

    def custom_gateway_type(request: Request) -> str:
        """Custom gateway type extractor."""
        if "custom" in request.url.path:
            return "custom"
        return "unknown"

    app.add_middleware(
        RateLimitMiddleware,
        get_user_id=lambda r: user.id,
        get_gateway_type=custom_gateway_type
    )

    @app.get("/custom/v1/test")
    async def custom_endpoint():
        return {"status": "ok"}

    test_client = TestClient(app)

    # Test custom gateway type
    response = test_client.get("/custom/v1/test")
    assert response.status_code == 200

async def test_gateway_type_switching(client: TestClient, user: User, rate_limits: GatewayRateLimit):
    """Test handling of gateway type switching within a session."""
    def mock_request_factory(path: str):
        request = MockRequest(path)
        request.state.user_id = user.id
        request.state.start_time = datetime.utcnow().timestamp()
        request.state.tokens_used = 10
        return request

    # Test ollama gateway
    with patch("fastapi.Request", lambda *args, **kwargs: mock_request_factory("/ollama/v1/test")):
        response = client.get("/ollama/v1/test")
        assert response.status_code == 200

    # Test openai gateway
    with patch("fastapi.Request", lambda *args, **kwargs: mock_request_factory("/openai/v1/test")):
        response = client.get("/openai/v1/test")
        assert response.status_code == 200

async def test_middleware_cleanup_on_shutdown(client: TestClient, user: User):
    """Test middleware cleanup on application shutdown."""
    app = FastAPI()
    
    cleanup_called = False
    
    class CleanupMiddleware(RateLimitMiddleware):
        async def cleanup(self):
            nonlocal cleanup_called
            cleanup_called = True
    
    app.add_middleware(
        CleanupMiddleware,
        get_user_id=lambda r: user.id,
        get_gateway_type=RateLimitMiddleware.get_gateway_type_from_path
    )
    
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    test_client = TestClient(app)
    response = test_client.get("/test")
    assert response.status_code == 200
    
    # Simulate application shutdown
    await app.shutdown()
    assert cleanup_called

async def test_model_specific_rate_limits(
    client: TestClient,
    user: User,
    db_session: Session,
    mock_redis: MagicMock
):
    """Test rate limits for specific models within a gateway."""
    # Create rate limits for the gateway
    limits = GatewayRateLimit(
        id=uuid.uuid4(),
        user_id=user.id,
        gateway_type="ollama",
        token_limit_hourly=100,  # Set low limit to test accumulation
        token_limit_daily=1000,
        request_limit_hourly=10,
        request_limit_daily=100
    )
    db_session.add(limits)
    db_session.commit()

    def mock_request_factory(model_name: str, tokens: int):
        request = MockRequest("/ollama/v1/chat/completions")
        request.state.user_id = user.id
        request.state.start_time = datetime.utcnow().timestamp()
        request.state.end_time = datetime.utcnow().timestamp() + 0.5
        request.state.tokens_used = tokens
        request.state.model_name = model_name
        return request

    # First request with 60 tokens (should succeed)
    with patch("fastapi.Request", lambda *args, **kwargs: mock_request_factory("llama2", 60)):
        response = client.get("/ollama/v1/chat/completions")
        assert response.status_code == 200

    # Second request with 50 tokens (should exceed hourly limit of 100)
    with patch("fastapi.Request", lambda *args, **kwargs: mock_request_factory("llama2-70b", 50)):
        response = client.get("/ollama/v1/chat/completions")
        assert response.status_code == 429
        assert "token limit" in response.json()["detail"].lower()

async def test_shared_rate_limits(
    client: TestClient,
    user: User,
    db_session: Session,
    mock_redis: MagicMock
):
    """Test rate limits shared across multiple gateways."""
    # Create shared rate limits
    limits = GatewayRateLimit(
        id=uuid.uuid4(),
        user_id=user.id,
        gateway_type="*",  # Wildcard for all gateways
        token_limit_hourly=100,  # Set low limit to test accumulation
        token_limit_daily=1000,
        request_limit_hourly=10,
        request_limit_daily=100
    )
    db_session.add(limits)
    db_session.commit()

    def mock_request_factory(path: str, tokens: int):
        request = MockRequest(path)
        request.state.user_id = user.id
        request.state.start_time = datetime.utcnow().timestamp()
        request.state.tokens_used = tokens
        return request

    # First request to ollama gateway with 60 tokens
    with patch("fastapi.Request", lambda *args, **kwargs: mock_request_factory("/ollama/v1/test", 60)):
        response = client.get("/ollama/v1/test")
        assert response.status_code == 200

    # Second request to openai gateway with 50 tokens (should exceed shared limit of 100)
    with patch("fastapi.Request", lambda *args, **kwargs: mock_request_factory("/openai/v1/test", 50)):
        response = client.get("/openai/v1/test")
        assert response.status_code == 429
        assert "token limit" in response.json()["detail"].lower()
