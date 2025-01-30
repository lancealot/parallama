"""Tests for the authentication service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, create_autospec
from uuid import UUID, uuid4

import pytest
from jose import jwt
from redis import Redis
from sqlalchemy.orm import Session

from parallama.core.config import AuthConfig
from parallama.core.permissions import Permission, DefaultRoles
from parallama.services.auth import AuthService, TokenError
from parallama.models.refresh_token import RefreshToken
from parallama.models.user import User
from parallama.models.role import Role
from parallama.models.user_role import UserRole
from parallama.models.base import BaseModel


@pytest.fixture
def test_user_id() -> UUID:
    """Fixture providing a test user ID."""
    return uuid4()


@pytest.fixture
def test_secret_key() -> str:
    """Fixture providing a test secret key."""
    return "test_secret_key"


@pytest.fixture
def jwt_secret_file(test_secret_key, tmp_path) -> str:
    """Fixture providing a temporary JWT secret key file."""
    secret_file = tmp_path / "jwt_secret"
    secret_file.write_text(test_secret_key)
    return str(secret_file)


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
    redis.incr = MagicMock()
    redis.expire = MagicMock()
    redis.setex = MagicMock()
    return redis

@pytest.fixture
def auth_service(jwt_secret_file, mock_db, mock_redis) -> AuthService:
    """Fixture providing an AuthService instance with test configuration."""
    with patch('parallama.services.auth.config') as mock_config:
        # Create test auth config
        auth_config = AuthConfig(
            jwt_secret_key_file=jwt_secret_file,
            access_token_expire_minutes=30,
            refresh_token_expire_days=30,
            refresh_token_rate_limit=5,
            refresh_token_reuse_window=60
        )
        mock_config.auth = auth_config
        return AuthService(mock_db, mock_redis)


def test_create_access_token(auth_service: AuthService, test_user_id: UUID):
    """Test creating an access token."""
    token = auth_service.create_access_token(test_user_id)
    
    # Decode and verify the token
    payload = jwt.decode(
        token,
        auth_service.secret_key,
        algorithms=[auth_service.ALGORITHM]
    )
    
    assert payload["sub"] == str(test_user_id)
    assert payload["type"] == "access"
    
    # Verify expiration is set correctly
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    assert exp > now
    assert exp < now + timedelta(minutes=31)  # Allow some buffer


@pytest.fixture
def mock_role_service(mock_db):
    """Fixture providing a mock RoleService with test roles."""
    with patch('parallama.services.role.RoleService') as MockRoleService:
        role_service = MockRoleService.return_value
        
        # Create test roles
        admin_role = Role(
            name="admin",
            permissions=DefaultRoles.ADMIN["permissions"],
            description="Admin role"
        )
        basic_role = Role(
            name="basic",
            permissions=DefaultRoles.BASIC["permissions"],
            description="Basic role"
        )
        
        # Setup get_user_roles mock
        role_service.get_user_roles.return_value = [admin_role]
        
        return role_service

@pytest.fixture
def auth_service_with_roles(jwt_secret_file, mock_db, mock_redis, mock_role_service) -> AuthService:
    """Fixture providing an AuthService instance with mocked role service."""
    with patch('parallama.services.auth.config') as mock_config:
        auth_config = AuthConfig(
            jwt_secret_key_file=jwt_secret_file,
            access_token_expire_minutes=30,
            refresh_token_expire_days=30,
            refresh_token_rate_limit=5,
            refresh_token_reuse_window=60
        )
        mock_config.auth = auth_config
        
        service = AuthService(mock_db, mock_redis)
        service.role_service = mock_role_service
        return service

def test_verify_token(auth_service_with_roles: AuthService, test_user_id: UUID):
    """Test verifying a valid token."""
    token = auth_service_with_roles.create_access_token(test_user_id)
    user_id, permissions = auth_service_with_roles.verify_token(token)
    assert user_id == test_user_id
    assert Permission.MANAGE_USERS in permissions


def test_verify_token_expired(auth_service: AuthService, test_user_id: UUID):
    """Test verifying an expired token."""
    # Create a token that's already expired
    with patch('parallama.services.auth.datetime') as mock_datetime:
        now = datetime.now(timezone.utc)
        mock_datetime.now.return_value = now - timedelta(hours=1)
        token = auth_service.create_access_token(test_user_id)
    
    with pytest.raises(TokenError, match="Invalid token"):
        auth_service.verify_token(token)


def test_verify_token_invalid_signature(auth_service: AuthService, test_user_id: UUID):
    """Test verifying a token with invalid signature."""
    # Create a token with a different secret key
    token = jwt.encode(
        {
            "sub": str(test_user_id),
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        },
        "different_secret_key",  # Use a different secret key
        algorithm=auth_service.ALGORITHM
    )
    
    with pytest.raises(TokenError, match="Invalid token"):
        auth_service.verify_token(token)


def test_verify_token_missing_user_id(auth_service: AuthService):
    """Test verifying a token without a user ID."""
    # Create a token without a user ID
    token = jwt.encode(
        {"type": "access"},
        auth_service.secret_key,
        algorithm=auth_service.ALGORITHM
    )
    
    with pytest.raises(TokenError, match="Token missing user ID"):
        auth_service.verify_token(token)


def test_verify_token_invalid_type(auth_service: AuthService, test_user_id: UUID):
    """Test verifying a token with wrong type."""
    # Create a token with wrong type
    token = jwt.encode(
        {
            "sub": str(test_user_id),
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        },
        auth_service.secret_key,
        algorithm=auth_service.ALGORITHM
    )
    
    with pytest.raises(TokenError, match="Invalid token type"):
        auth_service.verify_token(token)


def test_create_token_response(auth_service_with_roles: AuthService, test_user_id: UUID):
    """Test creating a complete token response with roles and permissions."""
    response = auth_service_with_roles.create_token_response(test_user_id)
    
    assert "access_token" in response
    assert "refresh_token" in response
    assert response["token_type"] == auth_service_with_roles.TOKEN_TYPE
    assert response["expires_in"] == 30 * 60  # 30 minutes in seconds
    
    # Verify roles and permissions are included
    assert "roles" in response
    assert "permissions" in response
    assert "admin" in response["roles"]
    assert Permission.MANAGE_USERS in response["permissions"]
    
    # Verify the access token is valid
    user_id, permissions = auth_service_with_roles.verify_token(response["access_token"])
    assert user_id == test_user_id
    assert Permission.MANAGE_USERS in permissions
    
    # Verify refresh token format
    assert response["refresh_token"].startswith("rt_")

def test_create_token_response_without_permissions(auth_service_with_roles: AuthService, test_user_id: UUID):
    """Test creating a token response without including permissions."""
    response = auth_service_with_roles.create_token_response(test_user_id, include_permissions=False)
    
    assert "access_token" in response
    assert "refresh_token" in response
    assert "roles" not in response
    assert "permissions" not in response
    
    # Verify the access token is valid but doesn't contain permissions
    user_id, permissions = auth_service_with_roles.verify_token(response["access_token"])
    assert user_id == test_user_id
    assert not permissions  # Should be empty list

def test_refresh_tokens_with_roles(auth_service_with_roles: AuthService, test_user_id: UUID):
    """Test refreshing tokens includes roles and permissions."""
    old_token = "rt_old_token"
    
    # Create mock token model
    mock_token_model = MagicMock(spec=RefreshToken)
    mock_token_model.user_id = test_user_id
    mock_token_model.is_valid.return_value = True
    mock_token_model.revoke = MagicMock()
    mock_token_model.set_token = MagicMock()
    
    # Setup mock DB query for verification
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_token_model
    auth_service_with_roles.db.query.return_value = mock_query
    
    # Perform token refresh
    response = auth_service_with_roles.refresh_tokens(old_token)
    
    # Verify roles and permissions are included
    assert "roles" in response
    assert "permissions" in response
    assert "admin" in response["roles"]
    assert Permission.MANAGE_USERS in response["permissions"]
    
    # Verify the new access token contains permissions
    user_id, permissions = auth_service_with_roles.verify_token(response["access_token"])
    assert user_id == test_user_id
    assert Permission.MANAGE_USERS in permissions


class TestRefreshToken:
    """Test cases for refresh token functionality."""

    @pytest.fixture
    def mock_token_model(self, test_user_id):
        """Fixture providing a mock RefreshToken model."""
        token_model = MagicMock(spec=RefreshToken)
        token_model.id = uuid4()
        token_model.user_id = test_user_id
        token_model.is_valid.return_value = True
        token_model.revoke = MagicMock()
        token_model.set_token = MagicMock()
        return token_model

    @pytest.fixture
    def mock_user(self, test_user_id):
        """Fixture providing a mock User model."""
        user = MagicMock(spec=User)
        user.id = test_user_id
        user.username = "testuser"
        return user

    def test_create_refresh_token(self, auth_service, test_user_id, mock_db):
        """Test creating a refresh token."""
        token, token_model = auth_service.create_refresh_token(test_user_id)
        
        # Verify token format
        assert token.startswith("rt_")
        assert len(token) > 10
        
        # Verify model was saved
        assert mock_db.add.called
        assert mock_db.commit.called
        
        # Verify token model properties
        assert token_model.user_id == test_user_id
        # Use timezone-aware datetime for comparison
        now = datetime.now(timezone.utc)
        assert token_model.expires_at > now
        assert token_model.expires_at <= now + timedelta(days=31)  # Allow some buffer

    def test_verify_refresh_token_valid(
        self, auth_service, test_user_id, mock_db, mock_redis, mock_token_model
    ):
        """Test verifying a valid refresh token."""
        token = "rt_valid_token"
        token_hash = RefreshToken.hash_token(token)
        
        # Setup mock DB query
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_token_model
        mock_db.query.return_value = mock_query
        
        # Verify token
        user_id, token_model = auth_service.verify_refresh_token(token)
        
        assert user_id == test_user_id
        assert token_model == mock_token_model
        
        # Verify Redis operations
        mock_redis.incr.assert_called_with(f"refresh_rate:{token_hash}")
        mock_redis.setex.assert_called_with(
            f"refresh_reuse:{token_hash}",
            60,  # reuse window
            "1"
        )

    def test_verify_refresh_token_rate_limited(
        self, auth_service, mock_redis
    ):
        """Test rate limiting for refresh token verification."""
        token = "rt_test_token"
        
        # Simulate rate limit exceeded
        mock_redis.get.return_value = "5"  # 5 attempts already made
        
        with pytest.raises(TokenError, match="Rate limit exceeded"):
            auth_service.verify_refresh_token(token)

    def test_verify_refresh_token_reuse(
        self, auth_service, mock_db, mock_redis, mock_token_model
    ):
        """Test prevention of refresh token reuse."""
        token = "rt_test_token"
        token_hash = RefreshToken.hash_token(token)
        
        # Setup mock DB query for initial token
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_token_model
        mock_db.query.return_value = mock_query
        
        # Setup replacement token chain
        replacement_token = MagicMock(spec=RefreshToken)
        replacement_token.replaced_by_id = None  # End of chain
        
        # First query returns original token, second query returns replacement, third returns None
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_token_model,  # First call returns original token
            replacement_token,  # Second call returns replacement token
            None  # Third call returns None to end the chain
        ]
        
        # Simulate token already used
        mock_redis.get.side_effect = lambda key: (
            "1" if key == f"refresh_reuse:{token_hash}" else None
        )
        
        with pytest.raises(TokenError, match="Refresh token reuse detected"):
            auth_service.verify_refresh_token(token)
            
        # Verify both tokens were revoked
        mock_token_model.revoke.assert_called_once()
        replacement_token.revoke.assert_called_once()
        
        # Verify token was revoked
        assert mock_token_model.revoke.called

    def test_refresh_tokens(
        self, auth_service, test_user_id, mock_db, mock_redis, mock_token_model
    ):
        """Test refreshing access and refresh tokens."""
        old_token = "rt_old_token"
        
        # Setup mock DB query for verification
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_token_model
        mock_db.query.return_value = mock_query
        
        # Perform token refresh
        response = auth_service.refresh_tokens(old_token)
        
        # Verify response format
        assert "access_token" in response
        assert "refresh_token" in response
        assert response["token_type"] == "bearer"
        assert response["expires_in"] == 30 * 60
        
        # Verify old token was revoked
        assert mock_token_model.revoke.called
        assert mock_db.commit.called
        
        # Verify new tokens are valid
        assert response["refresh_token"].startswith("rt_")
        user_id, _ = auth_service.verify_token(response["access_token"])
        assert user_id == test_user_id

    def test_revoke_refresh_token(
        self, auth_service, mock_db, mock_token_model
    ):
        """Test revoking a specific refresh token."""
        token = "rt_test_token"
        
        # Setup mock DB query
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_token_model
        mock_db.query.return_value = mock_query
        
        # Revoke token
        auth_service.revoke_refresh_token(token)
        
        # Verify token was revoked
        assert mock_token_model.revoke.called
        assert mock_db.commit.called

    def test_revoke_all_user_tokens(
        self, auth_service, test_user_id, mock_db
    ):
        """Test revoking all refresh tokens for a user."""
        # Setup mock query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.update = MagicMock()
        mock_db.query.return_value = mock_query
        
        # Revoke all tokens
        auth_service.revoke_all_user_tokens(test_user_id)
        
        # Verify bulk update was performed
        assert mock_query.update.called
        assert mock_db.commit.called
