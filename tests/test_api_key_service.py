"""Tests for the API key service."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, create_autospec
from uuid import UUID, uuid4

import pytest
from redis import Redis
from sqlalchemy.orm import Session

from parallama.services.api_key import APIKeyService, APIKeyError
from parallama.models.api_key import APIKey


@pytest.fixture
def test_user_id() -> UUID:
    """Fixture providing a test user ID."""
    return uuid4()


@pytest.fixture
def mock_db():
    """Fixture providing a mock database session."""
    db = create_autospec(Session)
    
    # Setup query mock
    query_mock = MagicMock()
    query_mock.filter.return_value.first.return_value = None
    db.query.return_value = query_mock
    
    return db


@pytest.fixture
def mock_redis():
    """Fixture providing a mock Redis client."""
    redis = MagicMock(spec=Redis)
    redis.get = MagicMock(return_value=None)
    redis.setex = MagicMock()
    redis.delete = MagicMock()
    return redis


@pytest.fixture
def api_key_service(mock_db, mock_redis) -> APIKeyService:
    """Fixture providing an APIKeyService instance."""
    return APIKeyService(mock_db, mock_redis)


class TestAPIKeyService:
    """Test cases for API key functionality."""

    @pytest.fixture
    def mock_api_key_model(self, test_user_id):
        """Fixture providing a mock APIKey model."""
        key_model = MagicMock(spec=APIKey)
        key_model.id = uuid4()
        key_model.user_id = test_user_id
        key_model.key_hash = "test_hash"
        key_model.description = "Test key"
        key_model.created_at = datetime.now(timezone.utc)
        key_model.last_used_at = None
        key_model.revoked_at = None
        return key_model

    def test_create_key(self, api_key_service, test_user_id, mock_db):
        """Test creating an API key."""
        description = "Test key"
        key = api_key_service.create_key(test_user_id, description)
        
        # Verify key format
        assert key.startswith("pk_live_")
        assert len(key) > 20
        
        # Verify model was saved
        assert mock_db.add.called
        assert mock_db.commit.called

    def test_create_key_error(self, api_key_service, test_user_id, mock_db):
        """Test error handling in key creation."""
        mock_db.commit.side_effect = Exception("Database error")
        
        with pytest.raises(APIKeyError, match="Error creating API key"):
            api_key_service.create_key(test_user_id)
        
        assert mock_db.rollback.called

    def test_verify_key_cached(self, api_key_service, test_user_id, mock_redis):
        """Test verifying a key that's in cache."""
        key = "pk_live_test_key"
        mock_redis.get.return_value = str(test_user_id).encode()
        
        user_id = api_key_service.verify_key(key)
        
        assert user_id == test_user_id

    def test_verify_key_from_db(
        self, api_key_service, test_user_id, mock_db, mock_redis, mock_api_key_model
    ):
        """Test verifying a key from database."""
        key = "pk_live_test_key"
        
        # Setup mock DB query
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_api_key_model
        mock_db.query.return_value = mock_query
        
        user_id = api_key_service.verify_key(key)
        
        assert user_id == test_user_id
        assert mock_redis.setex.called  # Verify result was cached
        assert mock_db.commit.called  # Verify last_used_at was updated

    def test_verify_key_invalid(self, api_key_service):
        """Test verifying an invalid key."""
        key = "pk_live_invalid_key"
        
        user_id = api_key_service.verify_key(key)
        
        assert user_id is None

    def test_verify_key_error(self, api_key_service, mock_db, mock_api_key_model):
        """Test error handling in key verification."""
        key = "pk_live_test_key"
        
        # Setup mock DB query to return a key model
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_api_key_model
        mock_db.query.return_value = mock_query
        
        # Setup commit to fail
        mock_db.commit.side_effect = Exception("Database error")
        
        with pytest.raises(APIKeyError, match="Error verifying API key"):
            api_key_service.verify_key(key)
        
        assert mock_db.rollback.called

    def test_revoke_key(
        self, api_key_service, mock_db, mock_redis, mock_api_key_model
    ):
        """Test revoking an API key."""
        key_id = uuid4()
        
        # Setup mock DB query
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_api_key_model
        mock_db.query.return_value = mock_query
        
        api_key_service.revoke_key(key_id)
        
        assert mock_api_key_model.revoked_at is not None
        assert mock_db.commit.called
        assert mock_redis.delete.called  # Verify cache was invalidated

    def test_revoke_key_not_found(self, api_key_service):
        """Test revoking a non-existent key."""
        key_id = uuid4()
        
        # Should not raise an error
        api_key_service.revoke_key(key_id)

    def test_revoke_key_error(self, api_key_service, mock_db, mock_api_key_model):
        """Test error handling in key revocation."""
        key_id = uuid4()
        
        # Setup mock DB query
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_api_key_model
        mock_db.query.return_value = mock_query
        
        mock_db.commit.side_effect = Exception("Database error")
        
        with pytest.raises(APIKeyError, match="Error revoking API key"):
            api_key_service.revoke_key(key_id)
        
        assert mock_db.rollback.called

    def test_list_keys(
        self, api_key_service, test_user_id, mock_db, mock_api_key_model
    ):
        """Test listing a user's API keys."""
        # Setup mock DB query
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [mock_api_key_model]
        mock_db.query.return_value = mock_query
        
        keys = api_key_service.list_keys(test_user_id)
        
        assert len(keys) == 1
        key = keys[0]
        assert key["id"] == mock_api_key_model.id
        assert key["created_at"] == mock_api_key_model.created_at
        assert key["last_used_at"] == mock_api_key_model.last_used_at
        assert key["description"] == mock_api_key_model.description
        assert key["revoked_at"] == mock_api_key_model.revoked_at

    def test_list_keys_empty(self, api_key_service, test_user_id, mock_db):
        """Test listing keys when user has none."""
        # Setup mock DB query to return empty list
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        keys = api_key_service.list_keys(test_user_id)
        
        assert len(keys) == 0

    def test_list_keys_error(self, api_key_service, test_user_id, mock_db):
        """Test error handling in key listing."""
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(APIKeyError, match="Error listing API keys"):
            api_key_service.list_keys(test_user_id)
