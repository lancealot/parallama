"""Tests for authentication and authorization middleware."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from parallama.core.permissions import Permission, DefaultRoles
from parallama.middleware.auth import (
    get_current_user,
    get_current_user_permissions,
    requires_permission,
    requires_any_permission,
    requires_all_permissions
)
from parallama.models.role import Role
from parallama.services.auth import AuthService, TokenError
from parallama.services.api_key import APIKeyService
from parallama.services.role import RoleService


@pytest.fixture
def test_user_id() -> UUID:
    """Fixture providing a test user ID."""
    return uuid4()


@pytest.fixture
def mock_auth_service():
    """Fixture providing a mock AuthService."""
    return MagicMock(spec=AuthService)


@pytest.fixture
def mock_api_key_service():
    """Fixture providing a mock APIKeyService."""
    return MagicMock(spec=APIKeyService)


@pytest.fixture
def mock_role_service():
    """Fixture providing a mock RoleService."""
    return MagicMock(spec=RoleService)


@pytest.fixture
def mock_credentials():
    """Fixture providing mock HTTP credentials."""
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="test_token"
    )


@pytest.fixture
def app():
    """Fixture providing a test FastAPI application."""
    return FastAPI()


@pytest.mark.asyncio
async def test_get_current_user_jwt(
    test_user_id,
    mock_auth_service,
    mock_api_key_service,
    mock_credentials
):
    """Test getting current user with valid JWT token."""
    # Setup mock auth service to return user ID
    mock_auth_service.verify_token.return_value = (test_user_id, [])
    
    user_id = await get_current_user(
        mock_credentials,
        mock_auth_service,
        mock_api_key_service
    )
    
    assert user_id == test_user_id
    mock_auth_service.verify_token.assert_called_once_with(mock_credentials.credentials)
    mock_api_key_service.verify_key.assert_not_called()


@pytest.mark.asyncio
async def test_get_current_user_api_key(
    test_user_id,
    mock_auth_service,
    mock_api_key_service,
    mock_credentials
):
    """Test getting current user with valid API key."""
    # Setup mock auth service to fail JWT verification
    mock_auth_service.verify_token.side_effect = TokenError("Invalid token")
    # Setup mock API key service to return user ID
    mock_api_key_service.verify_key.return_value = test_user_id
    
    user_id = await get_current_user(
        mock_credentials,
        mock_auth_service,
        mock_api_key_service
    )
    
    assert user_id == test_user_id
    mock_auth_service.verify_token.assert_called_once_with(mock_credentials.credentials)
    mock_api_key_service.verify_key.assert_called_once_with(mock_credentials.credentials)


@pytest.mark.asyncio
async def test_get_current_user_invalid_credentials(
    mock_auth_service,
    mock_api_key_service,
    mock_credentials
):
    """Test getting current user with invalid credentials."""
    # Setup both services to fail verification
    mock_auth_service.verify_token.side_effect = TokenError("Invalid token")
    mock_api_key_service.verify_key.side_effect = Exception("Invalid key")
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            mock_credentials,
            mock_auth_service,
            mock_api_key_service
        )
    
    assert exc_info.value.status_code == 401
    assert "Invalid authentication credentials" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_current_user_permissions_jwt(
    test_user_id,
    mock_auth_service,
    mock_api_key_service,
    mock_role_service,
    mock_credentials
):
    """Test getting current user permissions with JWT token."""
    permissions = [Permission.MANAGE_USERS, Permission.VIEW_METRICS]
    mock_auth_service.verify_token.return_value = (test_user_id, permissions)
    
    user_id, user_permissions = await get_current_user_permissions(
        mock_credentials,
        mock_auth_service,
        mock_api_key_service,
        mock_role_service
    )
    
    assert user_id == test_user_id
    assert user_permissions == permissions
    mock_auth_service.verify_token.assert_called_once_with(mock_credentials.credentials)
    mock_api_key_service.verify_key.assert_not_called()
    mock_role_service.get_user_roles.assert_not_called()


@pytest.mark.asyncio
async def test_get_current_user_permissions_api_key(
    test_user_id,
    mock_auth_service,
    mock_api_key_service,
    mock_role_service,
    mock_credentials
):
    """Test getting current user permissions with API key."""
    # Setup mock services
    mock_auth_service.verify_token.side_effect = TokenError("Invalid token")
    mock_api_key_service.verify_key.return_value = test_user_id
    
    # Create test role with permissions
    admin_role = Role(
        name="admin",
        permissions=DefaultRoles.ADMIN["permissions"],
        description="Admin role"
    )
    mock_role_service.get_user_roles.return_value = [admin_role]
    
    user_id, permissions = await get_current_user_permissions(
        mock_credentials,
        mock_auth_service,
        mock_api_key_service,
        mock_role_service
    )
    
    assert user_id == test_user_id
    assert Permission.MANAGE_USERS in permissions
    mock_auth_service.verify_token.assert_called_once_with(mock_credentials.credentials)
    mock_api_key_service.verify_key.assert_called_once_with(mock_credentials.credentials)
    mock_role_service.get_user_roles.assert_called_once_with(test_user_id)


@pytest.mark.asyncio
async def test_requires_permission_decorator(test_user_id, mock_role_service):
    """Test the requires_permission decorator."""
    # Create test endpoint
    @requires_permission(Permission.MANAGE_USERS)
    async def test_endpoint(user_id: UUID):
        return {"message": "success"}
    
    # Test with permission granted
    mock_role_service.check_permission.return_value = True
    result = await test_endpoint(user_id=test_user_id)
    assert result == {"message": "success"}
    
    # Test with permission denied
    mock_role_service.check_permission.return_value = False
    with pytest.raises(HTTPException) as exc_info:
        await test_endpoint(user_id=test_user_id)
    
    assert exc_info.value.status_code == 403
    assert "Missing required permission" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_requires_any_permission_decorator(test_user_id, mock_role_service):
    """Test the requires_any_permission decorator."""
    required_permissions = [Permission.USE_OLLAMA, Permission.USE_OPENAI]
    
    @requires_any_permission(required_permissions)
    async def test_endpoint(user_id: UUID):
        return {"message": "success"}
    
    # Test with one permission granted
    mock_role_service.check_permission.side_effect = [True, False]
    result = await test_endpoint(user_id=test_user_id)
    assert result == {"message": "success"}
    
    # Test with no permissions granted
    mock_role_service.check_permission.side_effect = [False, False]
    with pytest.raises(HTTPException) as exc_info:
        await test_endpoint(user_id=test_user_id)
    
    assert exc_info.value.status_code == 403
    assert "Missing required permissions" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_requires_all_permissions_decorator(test_user_id, mock_role_service):
    """Test the requires_all_permissions decorator."""
    required_permissions = [Permission.USE_OLLAMA, Permission.MANAGE_MODELS]
    
    @requires_all_permissions(required_permissions)
    async def test_endpoint(user_id: UUID):
        return {"message": "success"}
    
    # Test with all permissions granted
    mock_role_service.check_permission.side_effect = [True, True]
    result = await test_endpoint(user_id=test_user_id)
    assert result == {"message": "success"}
    
    # Test with some permissions missing
    mock_role_service.check_permission.side_effect = [True, False]
    with pytest.raises(HTTPException) as exc_info:
        await test_endpoint(user_id=test_user_id)
    
    assert exc_info.value.status_code == 403
    assert "Missing required permissions" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_decorator_missing_user_id():
    """Test decorators when user_id is missing."""
    @requires_permission(Permission.MANAGE_USERS)
    async def test_endpoint():
        return {"message": "success"}
    
    with pytest.raises(HTTPException) as exc_info:
        await test_endpoint()
    
    assert exc_info.value.status_code == 401
    assert "Authentication required" in str(exc_info.value.detail)
