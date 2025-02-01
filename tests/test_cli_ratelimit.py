"""Tests for rate limit CLI commands."""
import pytest
from click.testing import CliRunner
from datetime import datetime
from unittest.mock import patch

from parallama.cli.commands.ratelimit import ratelimit_cli
from parallama.models.user import User
from parallama.models.rate_limit import GatewayRateLimit
from parallama.core.database import get_db

@pytest.fixture
def cli_runner(db_session):
    """Create a CLI runner with database session."""
    runner = CliRunner()
    def mock_get_db():
        return db_session
    with patch('parallama.cli.commands.ratelimit.get_db', side_effect=mock_get_db):
        yield runner

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(username="testuser", role="basic")
    user.set_password("password123")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_rate_limit(db_session, test_user):
    """Create a test rate limit."""
    rate_limit = GatewayRateLimit(
        user_id=test_user.id,
        gateway_type="ollama",
        token_limit_hourly=1000,
        token_limit_daily=10000,
        request_limit_hourly=100,
        request_limit_daily=1000
    )
    db_session.add(rate_limit)
    db_session.commit()
    return rate_limit

def test_set_rate_limit(cli_runner, test_user, db_session):
    """Test setting rate limits."""
    result = cli_runner.invoke(
        ratelimit_cli,
        ['set', 'testuser', 'ollama', '--token-hourly', '1000', '--token-daily', '10000'],
        input='y\n'  # Confirm the action
    )
    assert result.exit_code == 0
    assert "Rate limits updated" in result.output
    
    # Verify database changes
    rate_limit = db_session.query(GatewayRateLimit).filter(
        GatewayRateLimit.user_id == test_user.id,
        GatewayRateLimit.gateway_type == 'ollama'
    ).first()
    assert rate_limit is not None
    assert rate_limit.token_limit_hourly == 1000
    assert rate_limit.token_limit_daily == 10000

def test_set_rate_limit_nonexistent_user(cli_runner):
    """Test setting rate limits for nonexistent user."""
    result = cli_runner.invoke(
        ratelimit_cli,
        ['set', 'nonexistent', 'ollama', '--token-hourly', '1000']
    )
    assert result.exit_code != 0
    assert "User 'nonexistent' not found" in result.output

def test_set_rate_limit_no_limits(cli_runner, test_user):
    """Test setting rate limits with no limits specified."""
    result = cli_runner.invoke(
        ratelimit_cli,
        ['set', 'testuser', 'ollama']
    )
    assert result.exit_code != 0
    assert "No rate limits specified" in result.output

def test_get_rate_limits(cli_runner, test_rate_limit):
    """Test getting rate limits."""
    result = cli_runner.invoke(
        ratelimit_cli,
        ['get', 'testuser']
    )
    assert result.exit_code == 0
    assert "ollama" in result.output
    assert "1000" in result.output
    assert "10000" in result.output

def test_get_rate_limits_with_gateway(cli_runner, test_rate_limit):
    """Test getting rate limits for specific gateway."""
    result = cli_runner.invoke(
        ratelimit_cli,
        ['get', 'testuser', 'ollama']
    )
    assert result.exit_code == 0
    assert "ollama" in result.output
    assert "1000" in result.output
    assert "10000" in result.output

def test_get_rate_limits_nonexistent_user(cli_runner):
    """Test getting rate limits for nonexistent user."""
    result = cli_runner.invoke(
        ratelimit_cli,
        ['get', 'nonexistent']
    )
    assert result.exit_code != 0
    assert "User 'nonexistent' not found" in result.output

def test_get_rate_limits_no_limits(cli_runner, test_user):
    """Test getting rate limits when none exist."""
    result = cli_runner.invoke(
        ratelimit_cli,
        ['get', 'testuser']
    )
    assert result.exit_code != 0
    assert "No rate limits found" in result.output

def test_reset_rate_limits(cli_runner, test_rate_limit):
    """Test resetting rate limits."""
    result = cli_runner.invoke(
        ratelimit_cli,
        ['reset', 'testuser', 'ollama'],
        input='y\n'  # Confirm the action
    )
    assert result.exit_code == 0
    assert "Rate limits reset" in result.output

def test_reset_rate_limits_nonexistent_user(cli_runner):
    """Test resetting rate limits for nonexistent user."""
    result = cli_runner.invoke(
        ratelimit_cli,
        ['reset', 'nonexistent', 'ollama']
    )
    assert result.exit_code != 0
    assert "User 'nonexistent' not found" in result.output

def test_reset_rate_limits_no_limits(cli_runner, test_user):
    """Test resetting rate limits when none exist."""
    result = cli_runner.invoke(
        ratelimit_cli,
        ['reset', 'testuser', 'ollama']
    )
    assert result.exit_code != 0
    assert "No rate limits found" in result.output
