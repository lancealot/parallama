"""Authentication and authorization middleware."""

from functools import wraps
from typing import Callable, List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN
)

from ..core.permissions import Permission
from ..services.auth import AuthService, TokenError
from ..services.api_key import APIKeyService
from ..services.role import RoleService
from ..core.database import get_db
from ..core.redis import get_redis

security = HTTPBearer()

def get_auth_service(
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
) -> AuthService:
    """Dependency for getting the auth service."""
    return AuthService(db, redis)

def get_api_key_service(
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
) -> APIKeyService:
    """Dependency for getting the API key service."""
    return APIKeyService(db, redis)

def get_role_service(
    db: Session = Depends(get_db)
) -> RoleService:
    """Dependency for getting the role service."""
    return RoleService(db)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth_service: AuthService = Depends(get_auth_service),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> UUID:
    """
    Get the current user ID from either JWT token or API key.
    
    Args:
        credentials: The authorization credentials
        auth_service: The authentication service
        api_key_service: The API key service
        
    Returns:
        UUID: The user ID
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        
        # Try JWT token first
        try:
            user_id, _ = auth_service.verify_token(token)
            return user_id
        except TokenError:
            # If JWT verification fails, try API key
            try:
                user_id = api_key_service.verify_key(token)
                return user_id
            except Exception as e:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"}
                )
                
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_user_permissions(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth_service: AuthService = Depends(get_auth_service),
    api_key_service: APIKeyService = Depends(get_api_key_service),
    role_service: RoleService = Depends(get_role_service)
) -> tuple[UUID, List[str]]:
    """
    Get the current user ID and permissions from either JWT token or API key.
    
    Args:
        credentials: The authorization credentials
        auth_service: The authentication service
        api_key_service: The API key service
        role_service: The role service
        
    Returns:
        tuple[UUID, List[str]]: The user ID and list of permissions
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        
        # Try JWT token first
        try:
            user_id, permissions = auth_service.verify_token(token)
            return user_id, permissions
        except TokenError:
            # If JWT verification fails, try API key
            try:
                user_id = api_key_service.verify_key(token)
                # Get permissions from roles for API key auth
                roles = role_service.get_user_roles(user_id)
                permissions = set()
                for role in roles:
                    permissions.update(role.get_permissions())
                return user_id, list(permissions)
            except Exception as e:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"}
                )
                
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

def requires_permission(permission: Permission) -> Callable:
    """
    Decorator for requiring a specific permission to access an endpoint.
    
    Args:
        permission: The required permission
        
    Returns:
        Callable: The decorated function
        
    Example:
        @app.get("/admin")
        @requires_permission(Permission.MANAGE_USERS)
        async def admin_endpoint(user_id: UUID = Depends(get_current_user)):
            return {"message": "Admin access granted"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user_id and permissions from kwargs
            user_id = kwargs.get("user_id")
            if not user_id:
                for arg in args:
                    if isinstance(arg, UUID):
                        user_id = arg
                        break
            
            if not user_id:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get role service from kwargs or create new one
            db = kwargs.get("db")
            if not db:
                db = next(get_db())
            role_service = RoleService(db)
            
            # Check permission
            if not role_service.check_permission(user_id, permission):
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def requires_any_permission(permissions: List[Permission]) -> Callable:
    """
    Decorator for requiring any of the specified permissions to access an endpoint.
    
    Args:
        permissions: List of permissions, any of which grant access
        
    Returns:
        Callable: The decorated function
        
    Example:
        @app.get("/gateway")
        @requires_any_permission([Permission.USE_OLLAMA, Permission.USE_OPENAI])
        async def gateway_endpoint(user_id: UUID = Depends(get_current_user)):
            return {"message": "Gateway access granted"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user_id from kwargs
            user_id = kwargs.get("user_id")
            if not user_id:
                for arg in args:
                    if isinstance(arg, UUID):
                        user_id = arg
                        break
            
            if not user_id:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get role service from kwargs or create new one
            db = kwargs.get("db")
            if not db:
                db = next(get_db())
            role_service = RoleService(db)
            
            # Check if user has any of the required permissions
            has_permission = any(
                role_service.check_permission(user_id, p)
                for p in permissions
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {[str(p) for p in permissions]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def requires_all_permissions(permissions: List[Permission]) -> Callable:
    """
    Decorator for requiring all specified permissions to access an endpoint.
    
    Args:
        permissions: List of permissions, all of which are required
        
    Returns:
        Callable: The decorated function
        
    Example:
        @app.post("/models")
        @requires_all_permissions([Permission.USE_OLLAMA, Permission.MANAGE_MODELS])
        async def create_model(user_id: UUID = Depends(get_current_user)):
            return {"message": "Model created"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user_id from kwargs
            user_id = kwargs.get("user_id")
            if not user_id:
                for arg in args:
                    if isinstance(arg, UUID):
                        user_id = arg
                        break
            
            if not user_id:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get role service from kwargs or create new one
            db = kwargs.get("db")
            if not db:
                db = next(get_db())
            role_service = RoleService(db)
            
            # Check if user has all required permissions
            has_all_permissions = all(
                role_service.check_permission(user_id, p)
                for p in permissions
            )
            
            if not has_all_permissions:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {[str(p) for p in permissions]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
