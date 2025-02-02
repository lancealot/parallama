"""Tests for the API key service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from redis import Redis
from sqlalchemy.orm import Session

from parallama.models.api_key import APIKey
from parallama.services.api_key import APIKeyService, APIKeyError
from parallama.core.exceptions import ResourceNotFoundError

class TestAPIKeyService:
    """Test cases for API key service."""

    def test_create_key(self, db_session: Session, mock_redis: Redis):
        """Test creating a new API key."""
        service = APIKeyService(db_session, mock_redis)
        user_id = uuid.uuid4()
        description = "Test key"

        key = service.create_key(user_id, name=description)
        assert key.key.startswith("pk_")

        # Check database record
        key_model = db_session.query(APIKey).first()
        assert key_model is not None
        assert key_model.user_id == str(user_id)
        assert key_model.name == description
        assert key_model.revoked_at is None

    def test_create_key_error(self, db_session: Session, mock_redis: Redis):
        """Test error handling when creating a key."""
        service = APIKeyService(db_session, mock_redis)
        user_id = uuid.uuid4()

        # Mock database error
        db_session.add = MagicMock(side_effect=Exception("Database error"))

        with pytest.raises(APIKeyError) as exc:
            service.create_key(user_id)
        assert "Database error" in str(exc.value)

    def test_verify_key_cached(self, db_session: Session, mock_redis: Redis):
        """Test verifying a key that is cached."""
        service = APIKeyService(db_session, mock_redis)
        user_id = uuid.uuid4()
        key = "pk_live_test_key"
        api_key = APIKey()
        api_key.set_key(key)
        key_hash = api_key.key_hash

        # Mock cached key
        mock_redis.get.return_value = str(user_id).encode()

        result = service.verify_key(key)
        assert result == str(user_id)

        # Check Redis was queried
        mock_redis.get.assert_called_once_with(f"api_key:{key}")

    def test_verify_key_from_db(self, db_session: Session, mock_redis: Redis):
        """Test verifying a key from database."""
        service = APIKeyService(db_session, mock_redis)
        user_id = uuid.uuid4()
        key = "pk_live_test_key"

        # Create key in database
        key_model = APIKey(
            id=uuid.uuid4(),
            user_id=str(user_id),
            created_at=datetime.now(timezone.utc)
        )
        key_model.set_key(key)
        db_session.add(key_model)
        db_session.commit()

        # Mock Redis miss
        mock_redis.get.return_value = None

        result = service.verify_key(key)
        assert result == str(user_id)

        # Check key was cached
        mock_redis.setex.assert_called_once_with(
            f"api_key:{key_model.key}",
            300,
            str(user_id)
        )

    def test_verify_key_invalid(self, db_session: Session, mock_redis: Redis):
        """Test verifying an invalid key."""
        service = APIKeyService(db_session, mock_redis)
        key = "pk_live_invalid_key"

        # Mock Redis miss
        mock_redis.get.return_value = None

        result = service.verify_key(key)
        assert result is None

    def test_verify_key_error(self, db_session: Session, mock_redis: Redis):
        """Test error handling when verifying a key."""
        service = APIKeyService(db_session, mock_redis)
        key = "pk_live_test_key"

        # Mock Redis error
        mock_redis.get.side_effect = Exception("Redis error")

        with pytest.raises(APIKeyError) as exc:
            service.verify_key(key)
        assert "Redis error" in str(exc.value)

    def test_revoke_key(self, db_session: Session, mock_redis: Redis):
        """Test revoking an API key."""
        service = APIKeyService(db_session, mock_redis)
        user_id = uuid.uuid4()
        key_id = uuid.uuid4()
        key = "pk_live_test_key"

        # Create key in database
        key_model = APIKey(
            id=key_id,
            user_id=str(user_id),
            created_at=datetime.now(timezone.utc)
        )
        key_model.set_key(key)
        db_session.add(key_model)
        db_session.commit()

        service.revoke_key(key_id)

        # Check key was revoked
        key_model = db_session.get(APIKey, str(key_id))
        assert key_model.revoked_at is not None

        # Check cache was invalidated
        mock_redis.delete.assert_called_once_with(f"api_key:{key_model.key}")

    def test_revoke_key_not_found(self, db_session: Session, mock_redis: Redis):
        """Test revoking a non-existent key."""
        service = APIKeyService(db_session, mock_redis)
        key_id = uuid.uuid4()

        with pytest.raises(ResourceNotFoundError) as exc:
            service.revoke_key(key_id)
        assert str(key_id) in str(exc.value)

    def test_revoke_key_error(self, db_session: Session, mock_redis: Redis):
        """Test error handling when revoking a key."""
        service = APIKeyService(db_session, mock_redis)
        user_id = uuid.uuid4()
        key_id = uuid.uuid4()
        key = "pk_live_test_key"

        # Create key in database
        key_model = APIKey(
            id=key_id,
            user_id=str(user_id),
            created_at=datetime.now(timezone.utc)
        )
        key_model.set_key(key)
        db_session.add(key_model)
        db_session.commit()

        # Mock database error
        db_session.commit = MagicMock(side_effect=Exception("Database error"))

        with pytest.raises(APIKeyError) as exc:
            service.revoke_key(key_id)
        assert "Database error" in str(exc.value)

    def test_list_keys(self, db_session: Session, mock_redis: Redis):
        """Test listing API keys for a user."""
        service = APIKeyService(db_session, mock_redis)
        user_id = uuid.uuid4()

        # Create some keys
        keys = []
        for i in range(3):
            key_model = APIKey(
                id=uuid.uuid4(),
                user_id=str(user_id),
                created_at=datetime.now(timezone.utc)
            )
            key_model.set_key(f"key_{i}")
            keys.append(key_model)
            db_session.add(key_model)
        db_session.commit()

        result = service.list_keys(user_id)
        assert len(result) == 3
        for key in result:
            assert key.id in [str(k.id) for k in keys]

    def test_list_keys_empty(self, db_session: Session, mock_redis: Redis):
        """Test listing keys when user has none."""
        service = APIKeyService(db_session, mock_redis)
        user_id = uuid.uuid4()

        result = service.list_keys(user_id)
        assert result == []

    def test_list_keys_error(self, db_session: Session, mock_redis: Redis):
        """Test error handling when listing keys."""
        service = APIKeyService(db_session, mock_redis)
        user_id = uuid.uuid4()

        # Mock database error
        db_session.query = MagicMock(side_effect=Exception("Database error"))

        with pytest.raises(APIKeyError) as exc:
            service.list_keys(user_id)
        assert "Database error" in str(exc.value)
