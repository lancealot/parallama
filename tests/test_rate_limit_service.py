"""Tests for the rate limiting service."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import redis
from fastapi import HTTPException
from redis import Redis, ConnectionError
from sqlalchemy.orm import Session

from parallama.models.rate_limit import GatewayRateLimit, GatewayUsageLog
from parallama.services.rate_limit import RateLimitService
from parallama.models.user import User

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

@pytest.fixture
def rate_limit_service_with_mock(db_session: Session, mock_redis) -> RateLimitService:
    """Create a rate limit service with mocked Redis."""
    service = RateLimitService(db_session)
    service.redis = mock_redis  # Use the mock from conftest.py
    return service

async def test_get_user_limits(rate_limit_service_with_mock, user, rate_limits):
    """Test retrieving user rate limits."""
    limits = await rate_limit_service_with_mock.get_user_limits(user.id, "ollama")
    assert limits is not None
    assert limits.token_limit_hourly == 1000

async def test_check_rate_limit_no_limits(rate_limit_service_with_mock, user):
    """Test rate limit check when no limits are configured."""
    assert await rate_limit_service_with_mock.check_rate_limit(user.id, "ollama")

async def test_check_rate_limit_within_limits(rate_limit_service_with_mock, user, rate_limits):
    """Test rate limit check when within limits."""
    assert await rate_limit_service_with_mock.check_rate_limit(
        user_id=user.id,
        gateway_type="ollama",
        tokens=50
    )

async def test_check_rate_limit_exceed_hourly_tokens(rate_limit_service_with_mock, user, rate_limits):
    """Test rate limit check when hourly token limit is exceeded."""
    # Mock Redis to return high usage
    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = ["990", "0", "0", "0"]  # Near hourly token limit
    rate_limit_service_with_mock.redis.pipeline.return_value = mock_pipeline

    with pytest.raises(HTTPException) as exc:
        await rate_limit_service_with_mock.check_rate_limit(
            user_id=user.id,
            gateway_type="ollama",
            tokens=50
        )
    assert exc.value.status_code == 429
    assert "Hourly token limit" in str(exc.value.detail)

async def test_check_rate_limit_exceed_daily_tokens(rate_limit_service_with_mock, user, rate_limits):
    """Test rate limit check when daily token limit is exceeded."""
    # Mock Redis to return high usage
    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = ["0", "9900", "0", "0"]  # Near daily token limit
    rate_limit_service_with_mock.redis.pipeline.return_value = mock_pipeline

    with pytest.raises(HTTPException) as exc:
        await rate_limit_service_with_mock.check_rate_limit(
            user_id=user.id,
            gateway_type="ollama",
            tokens=200
        )
    assert exc.value.status_code == 429
    assert "Daily token limit" in str(exc.value.detail)

async def test_record_usage(rate_limit_service_with_mock, user):
    """Test recording API usage."""
    await rate_limit_service_with_mock.record_usage(
        user_id=user.id,
        gateway_type="ollama",
        endpoint="/test",
        tokens=50,
        model_name="llama2",
        duration=100,
        status_code=200
    )

    # Verify Redis counters were incremented
    pipeline = rate_limit_service_with_mock.redis.pipeline()
    assert pipeline.incr.called
    assert pipeline.expire.called

async def test_record_usage_with_error(rate_limit_service_with_mock, user):
    """Test recording API usage with error."""
    await rate_limit_service_with_mock.record_usage(
        user_id=user.id,
        gateway_type="ollama",
        endpoint="/test",
        error_message="Test error",
        status_code=500
    )

    # Verify error was logged
    pipeline = rate_limit_service_with_mock.redis.pipeline()
    assert pipeline.incr.called
    assert pipeline.expire.called

async def test_rate_limit_key_format(rate_limit_service_with_mock, user):
    """Test rate limit key formatting."""
    keys = rate_limit_service_with_mock._get_rate_limit_keys(user.id, "ollama")
    assert len(keys) == 4
    assert all(str(user.id) in key for key in keys)
    assert all("ollama" in key for key in keys)

async def test_redis_connection_error(db_session, user):
    """Test handling of Redis connection errors."""
    mock_redis = MagicMock(spec=Redis)
    mock_redis.ping.side_effect = redis.ConnectionError("Connection refused")

    with patch('parallama.services.rate_limit.get_redis', return_value=iter([mock_redis])):
        with pytest.raises(HTTPException) as exc:
            service = RateLimitService(db_session)
        assert exc.value.status_code == 503
        assert "service" in str(exc.value.detail).lower()

async def test_database_transaction_rollback(rate_limit_service_with_mock, user):
    """Test database transaction rollback on error."""
    # Simulate a database error during usage logging
    with patch.object(rate_limit_service_with_mock.db, "commit", side_effect=Exception("Database error")), \
         patch.object(rate_limit_service_with_mock.db, "rollback") as mock_rollback:
        with pytest.raises(Exception):
            await rate_limit_service_with_mock.record_usage(
                user_id=user.id,
                gateway_type="ollama",
                endpoint="/test",
                tokens=50
            )

        # Verify rollback was called
        mock_rollback.assert_called_once()

        # Verify no usage logs were created
        logs = rate_limit_service_with_mock.db.query(GatewayUsageLog).all()
        assert len(logs) == 0

async def test_concurrent_requests(rate_limit_service_with_mock, user, rate_limits):
    """Test handling of concurrent requests."""
    import asyncio

    # Simulate multiple concurrent requests
    async def make_request():
        return await rate_limit_service_with_mock.check_rate_limit(
            user_id=user.id,
            gateway_type="ollama",
            tokens=10
        )

    # Run 5 concurrent requests
    results = await asyncio.gather(
        *[make_request() for _ in range(5)],
        return_exceptions=True
    )

    # All requests should succeed since they're within limits
    assert all(result is True for result in results)

    # Verify Redis counters
    pipeline = rate_limit_service_with_mock.redis.pipeline()
    pipeline.execute.assert_called()

async def test_zero_limits(rate_limit_service_with_mock, user, db_session):
    """Test handling of zero rate limits."""
    # Create limits with zero values
    limits = GatewayRateLimit(
        id=uuid.uuid4(),
        user_id=user.id,
        gateway_type="ollama",
        token_limit_hourly=0,
        token_limit_daily=0,
        request_limit_hourly=0,
        request_limit_daily=0
    )
    db_session.add(limits)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await rate_limit_service_with_mock.check_rate_limit(
            user_id=user.id,
            gateway_type="ollama"
        )
    assert exc.value.status_code == 429
    assert "zero" in str(exc.value.detail).lower()

async def test_negative_token_count(rate_limit_service_with_mock, user):
    """Test handling of negative token counts."""
    with pytest.raises(ValueError) as exc:
        await rate_limit_service_with_mock.check_rate_limit(
            user_id=user.id,
            gateway_type="ollama",
            tokens=-10
        )
    assert "negative" in str(exc.value).lower()

async def test_usage_log_cleanup(rate_limit_service_with_mock, user, db_session):
    """Test cleanup of old usage logs."""
    # Create some old logs
    old_time = datetime.utcnow() - timedelta(days=31)
    old_log = GatewayUsageLog(
        user_id=user.id,
        gateway_type="ollama",
        endpoint="/test",
        timestamp=old_time
    )
    db_session.add(old_log)
    db_session.commit()

    # Run cleanup
    await rate_limit_service_with_mock.cleanup_old_logs(days=30)

    # Verify old logs were deleted
    logs = db_session.query(GatewayUsageLog).all()
    assert len(logs) == 0

async def test_token_counting_edge_cases(rate_limit_service_with_mock, user, rate_limits):
    """Test edge cases for token counting."""
    # Test zero tokens
    assert await rate_limit_service_with_mock.check_rate_limit(
        user_id=user.id,
        gateway_type="ollama",
        tokens=0
    )

    # Test maximum token value (simulate near limit)
    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = ["990", "9900", "0", "0"]
    rate_limit_service_with_mock.redis.pipeline.return_value = mock_pipeline

    # Should pass with tokens just under limit
    assert await rate_limit_service_with_mock.check_rate_limit(
        user_id=user.id,
        gateway_type="ollama",
        tokens=9
    )

    # Should fail with tokens exceeding limit
    with pytest.raises(HTTPException) as exc:
        await rate_limit_service_with_mock.check_rate_limit(
            user_id=user.id,
            gateway_type="ollama",
            tokens=11
        )
    assert exc.value.status_code == 429

async def test_transaction_isolation(rate_limit_service_with_mock, user, db_session):
    """Test database transaction isolation."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    # Create multiple usage logs concurrently
    async def create_log():
        await rate_limit_service_with_mock.record_usage(
            user_id=user.id,
            gateway_type="ollama",
            endpoint="/test",
            tokens=10
        )

    # Run concurrent operations
    tasks = [create_log() for _ in range(5)]
    await asyncio.gather(*tasks)

    # Verify all logs were created
    logs = db_session.query(GatewayUsageLog).all()
    assert len(logs) == 5

    # Verify no logs were duplicated
    log_ids = [log.id for log in logs]
    assert len(log_ids) == len(set(log_ids))

async def test_redis_pipeline_failures(rate_limit_service_with_mock, user, rate_limits):
    """Test Redis pipeline failure scenarios."""
    # Test partial pipeline failure
    mock_pipeline = MagicMock()
    mock_pipeline.execute.side_effect = redis.RedisError("Pipeline failure")
    rate_limit_service_with_mock.redis.pipeline.return_value = mock_pipeline

    with pytest.raises(HTTPException) as exc:
        await rate_limit_service_with_mock.check_rate_limit(
            user_id=user.id,
            gateway_type="ollama",
            tokens=10
        )
    assert exc.value.status_code == 503
    assert "service" in str(exc.value.detail).lower()

    # Test recovery after failure
    mock_pipeline.execute.side_effect = None
    mock_pipeline.execute.return_value = ["0", "0", "0", "0"]
    assert await rate_limit_service_with_mock.check_rate_limit(
        user_id=user.id,
        gateway_type="ollama",
        tokens=10
    )

async def test_rate_limit_updates(rate_limit_service_with_mock, user, db_session):
    """Test rate limit updates during active session."""
    # Create initial limits
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

    # Verify initial limits work
    assert await rate_limit_service_with_mock.check_rate_limit(
        user_id=user.id,
        gateway_type="ollama",
        tokens=50
    )

    # Update limits to be more restrictive
    limits.token_limit_hourly = 20
    db_session.commit()

    # Verify new limits are enforced
    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = ["15", "0", "0", "0"]
    rate_limit_service_with_mock.redis.pipeline.return_value = mock_pipeline

    with pytest.raises(HTTPException) as exc:
        await rate_limit_service_with_mock.check_rate_limit(
            user_id=user.id,
            gateway_type="ollama",
            tokens=10
        )
    assert exc.value.status_code == 429
