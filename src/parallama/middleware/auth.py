"""Authentication middleware for API endpoints."""

from functools import wraps
from typing import Callable, List, Optional, Tuple
from uuid import UUID

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..services.auth import AuthService, TokenError
from ..services.api_key import APIKeyService
from ..core.database import get_db, get_redis
from ..models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current user from token or API key.
    
    Args:
        credentials: Authorization credentials
        
    Returns:
        User: Authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Get services
        db = next(get_db())
        redis = next(get_redis())
        auth_service = AuthService(db, redis)
        api_key_service = APIKeyService(db, redis)

        # Check token type
        auth_type = credentials.scheme.lower()
        token = credentials.credentials

        if auth_type == "bearer":
            # Verify JWT token
            user_id, _ = auth_service.verify_token(token)
        elif auth_type == "apikey":
            # Verify API key
            user_id = api_key_service.verify_key(token)
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme"
            )

        # Get user
        user = db.query(User).filter(User.id == str(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return user

    except TokenError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Authentication error: {str(e)}"
        )
    finally:
        db.close()
        redis.close()

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[UUID]:
    """Get current user ID from token or API key.
    
    Args:
        credentials: Authorization credentials
        
    Returns:
        Optional[UUID]: User ID if authenticated, None otherwise
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Get services
        db = next(get_db())
        redis = next(get_redis())
        auth_service = AuthService(db, redis)
        api_key_service = APIKeyService(db, redis)

        # Check token type
        auth_type = credentials.scheme.lower()
        token = credentials.credentials

        if auth_type == "bearer":
            # Verify JWT token
            user_id, _ = auth_service.verify_token(token)
            return user_id
        elif auth_type == "apikey":
            # Verify API key
            user_id = api_key_service.verify_key(token)
            return user_id
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme"
            )

    except TokenError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Authentication error: {str(e)}"
        )
    finally:
        db.close()
        redis.close()

async def get_current_user_permissions(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[List[str]]:
    """Get current user permissions from token.
    
    Args:
        credentials: Authorization credentials
        
    Returns:
        Optional[List[str]]: User permissions if authenticated with JWT, None otherwise
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Get services
        db = next(get_db())
        redis = next(get_redis())
        auth_service = AuthService(db, redis)

        # Check token type
        auth_type = credentials.scheme.lower()
        token = credentials.credentials

        if auth_type == "bearer":
            # Verify JWT token and get permissions
            _, permissions = auth_service.verify_token(token)
            return permissions
        else:
            return None

    except TokenError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Authentication error: {str(e)}"
        )
    finally:
        db.close()
        redis.close()

def requires_permission(permission: str) -> Callable:
    """Decorator to require a specific permission.
    
    Args:
        permission: Required permission
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Request object not found"
                )

            # Get user permissions
            permissions = await get_current_user_permissions(
                await security(request)
            )

            # Check permission
            if not permissions or permission not in permissions:
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

def requires_any_permission(permissions: List[str]) -> Callable:
    """Decorator to require any of the specified permissions.
    
    Args:
        permissions: List of permissions, any of which grant access
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Request object not found"
                )

            # Get user permissions
            user_permissions = await get_current_user_permissions(
                await security(request)
            )

            # Check permissions
            if not user_permissions or not any(p in user_permissions for p in permissions):
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

def requires_all_permissions(permissions: List[str]) -> Callable:
    """Decorator to require all specified permissions.
    
    Args:
        permissions: List of permissions, all of which are required
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Request object not found"
                )

            # Get user permissions
            user_permissions = await get_current_user_permissions(
                await security(request)
            )

            # Check permissions
            if not user_permissions or not all(p in user_permissions for p in permissions):
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
