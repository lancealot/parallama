"""Tests for the authentication service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from jose import jwt

from parallama.core.config import AuthConfig
from parallama.services.auth import AuthService, TokenError


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
def auth_service(jwt_secret_file) -> AuthService:
    """Fixture providing an AuthService instance with test configuration."""
    with patch('parallama.services.auth.config') as mock_config:
        # Create test auth config
        auth_config = AuthConfig(
            jwt_secret_key_file=jwt_secret_file,
            access_token_expire_minutes=30
        )
        mock_config.auth = auth_config
        return AuthService()


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


def test_verify_token(auth_service: AuthService, test_user_id: UUID):
    """Test verifying a valid token."""
    token = auth_service.create_access_token(test_user_id)
    user_id = auth_service.verify_token(token)
    assert user_id == test_user_id


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


def test_create_token_response(auth_service: AuthService, test_user_id: UUID):
    """Test creating a complete token response."""
    response = auth_service.create_token_response(test_user_id)
    
    assert "access_token" in response
    assert response["token_type"] == auth_service.TOKEN_TYPE
    assert response["expires_in"] == 30 * 60  # 30 minutes in seconds
    
    # Verify the access token is valid
    user_id = auth_service.verify_token(response["access_token"])
    assert user_id == test_user_id
