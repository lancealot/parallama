"""Tests for CLI database session management."""
import pytest
from unittest.mock import patch, MagicMock
from redis import Redis

from parallama.cli.core.db import (
    init_db,
    get_db,
    get_redis,
    cleanup_db
)

@pytest.fixture
def mock_session_local():
    """Mock SQLAlchemy SessionLocal."""
    with patch('parallama.cli.core.db.SessionLocal') as mock:
        mock.return_value = MagicMock()
        yield mock

@pytest.fixture
def mock_redis_pool():
    """Mock Redis connection pool."""
    with patch('parallama.cli.core.db.redis_pool') as mock:
        yield mock

def test_init_db(mock_session_local, mock_redis_pool):
    """Test database initialization."""
    # Setup mock Redis client
    mock_redis = MagicMock(spec=Redis)
    with patch('parallama.cli.core.db.Redis', return_value=mock_redis) as mock_redis_class:
        init_db()
        
        # Verify session was created
        mock_session_local.assert_called_once()
        
        # Verify Redis client was created with pool
        mock_redis_class.assert_called_once_with(connection_pool=mock_redis_pool)

def test_get_db_initializes_if_needed(mock_session_local):
    """Test get_db initializes session if not exists."""
    mock_session = MagicMock()
    mock_session_local.return_value = mock_session
    
    with patch('parallama.cli.core.db._db_session', None):
        # First call should initialize
        session1 = get_db()
        assert session1 is mock_session
        mock_session_local.assert_called_once()
        
        # Second call should return same session
        session2 = get_db()
        assert session2 is session1
        assert mock_session_local.call_count == 1  # No additional initialization

def test_get_redis_initializes_if_needed(mock_redis_pool):
    """Test get_redis initializes client if not exists."""
    mock_redis = MagicMock(spec=Redis)
    with patch('parallama.cli.core.db.Redis', return_value=mock_redis) as mock_redis_class, \
         patch('parallama.cli.core.db._redis_client', None):
        # First call should initialize
        client1 = get_redis()
        assert client1 is mock_redis
        mock_redis_class.assert_called_once_with(connection_pool=mock_redis_pool)
        
        # Second call should return same client
        client2 = get_redis()
        assert client2 is client1
        assert mock_redis_class.call_count == 1  # No additional initialization

def test_cleanup_db():
    """Test database cleanup."""
    # Setup mock session and client
    mock_session = MagicMock()
    mock_client = MagicMock(spec=Redis)
    
    with patch('parallama.cli.core.db._db_session', mock_session), \
         patch('parallama.cli.core.db._redis_client', mock_client):
        cleanup_db()
        
        # Verify session was closed
        mock_session.close.assert_called_once()
        
        # Verify Redis client was closed
        mock_client.close.assert_called_once()

def test_cleanup_db_handles_none():
    """Test cleanup handles None session/client."""
    with patch('parallama.cli.core.db._db_session', None), \
         patch('parallama.cli.core.db._redis_client', None):
        # Should not raise any errors
        cleanup_db()

def test_session_lifecycle():
    """Test complete session lifecycle."""
    # Setup mocks
    mock_session = MagicMock()
    mock_redis = MagicMock(spec=Redis)
    
    with patch('parallama.cli.core.db.SessionLocal', return_value=mock_session), \
         patch('parallama.cli.core.db.Redis', return_value=mock_redis):
        
        # Initialize
        init_db()
        
        # Get session and client
        session = get_db()
        client = get_redis()
        
        assert session is mock_session
        assert client is mock_redis
        
        # Cleanup
        cleanup_db()
        
        # Verify cleanup
        mock_session.close.assert_called_once()
        mock_redis.close.assert_called_once()
