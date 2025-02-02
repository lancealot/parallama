"""Authentication service for managing user authentication."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
import jwt
from uuid import UUID

from sqlalchemy.orm import Session
from redis import Redis

from ..models.user import User
from ..models.refresh_token import RefreshToken
from ..services.role import RoleService
from ..core.exceptions import AuthenticationError, ResourceNotFoundError

class TokenError(AuthenticationError):
    """Token-related errors."""
    pass

class AuthService:
    """Service for handling user authentication."""

    def __init__(self, db: Session, redis: Redis):
        """Initialize auth service.
        
        Args:
            db: Database session
            redis: Redis client
        """
        self.db = db
        self.redis = redis
        self.role_service = RoleService(db)
        self.secret_key = "your-secret-key"  # TODO: Move to config
        self.token_expiry = timedelta(hours=1)
        self.refresh_token_expiry = timedelta(days=30)

    def create_access_token(
        self,
        user_id: UUID,
        permissions: Optional[list] = None
    ) -> str:
        """Create a new access token.
        
        Args:
            user_id: User ID
            permissions: Optional list of permissions
            
        Returns:
            str: Generated JWT token
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": now + self.token_expiry
        }
        if permissions:
            payload["permissions"] = permissions

        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def verify_token(self, token: str) -> Tuple[UUID, Optional[list]]:
        """Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Tuple[UUID, Optional[list]]: User ID and optional permissions
            
        Raises:
            TokenError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # Verify token type
            if payload.get("type") != "access":
                raise TokenError("Invalid token type")
            
            # Get user ID and permissions
            user_id = payload.get("sub")
            if not user_id:
                raise TokenError("Missing user ID in token")
            
            permissions = payload.get("permissions")
            
            return UUID(user_id), permissions

        except jwt.ExpiredSignatureError:
            raise TokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise TokenError(f"Invalid token: {str(e)}")
        except ValueError as e:
            raise TokenError(f"Invalid user ID in token: {str(e)}")

    def create_token_response(
        self,
        user: User,
        include_permissions: bool = True
    ) -> Dict:
        """Create response with access and refresh tokens.
        
        Args:
            user: User to create tokens for
            include_permissions: Whether to include permissions in token
            
        Returns:
            Dict: Response with tokens and metadata
        """
        # Get permissions if needed
        permissions = None
        if include_permissions and user.role:
            permissions = user.role.permissions

        # Create tokens
        access_token = self.create_access_token(user.id, permissions)
        refresh_token = self.create_refresh_token(user.id)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(self.token_expiry.total_seconds()),
            "refresh_token": refresh_token,
            "permissions": permissions
        }

    def create_refresh_token(self, user_id: UUID) -> str:
        """Create a new refresh token.
        
        Args:
            user_id: User ID
            
        Returns:
            str: Generated refresh token
        """
        token = RefreshToken(
            user_id=str(user_id),
            expires_at=datetime.now(timezone.utc) + self.refresh_token_expiry
        )
        self.db.add(token)
        self.db.commit()
        return str(token.id)

    def verify_refresh_token(self, token: str) -> UUID:
        """Verify a refresh token.
        
        Args:
            token: Refresh token to verify
            
        Returns:
            UUID: User ID
            
        Raises:
            TokenError: If token is invalid or expired
        """
        try:
            # Check rate limiting
            key = f"refresh_token_attempts:{token}"
            attempts = self.redis.incr(key)
            if attempts == 1:
                self.redis.expire(key, 300)  # 5 minute window
            if attempts > 5:
                raise TokenError("Too many refresh attempts")

            # Get token from database
            token_model = self.db.query(RefreshToken).filter(
                RefreshToken.id == token,
                RefreshToken.revoked_at.is_(None)
            ).first()

            if not token_model:
                raise TokenError("Invalid refresh token")

            if token_model.expires_at < datetime.now(timezone.utc):
                raise TokenError("Refresh token has expired")

            # Revoke token after use
            token_model.revoke()
            self.db.commit()

            return UUID(token_model.user_id)

        except ValueError as e:
            raise TokenError(f"Invalid token format: {str(e)}")

    def refresh_tokens(
        self,
        refresh_token: str,
        include_permissions: bool = True
    ) -> Dict:
        """Refresh access and refresh tokens.
        
        Args:
            refresh_token: Current refresh token
            include_permissions: Whether to include permissions in new token
            
        Returns:
            Dict: Response with new tokens and metadata
            
        Raises:
            TokenError: If refresh token is invalid
            ResourceNotFoundError: If user not found
        """
        # Verify refresh token
        user_id = self.verify_refresh_token(refresh_token)

        # Get user
        user = self.db.query(User).filter(User.id == str(user_id)).first()
        if not user:
            raise ResourceNotFoundError(f"User {user_id} not found")

        # Create new tokens
        return self.create_token_response(user, include_permissions)

    def revoke_refresh_token(self, token: str) -> None:
        """Revoke a refresh token.
        
        Args:
            token: Refresh token to revoke
        """
        token_model = self.db.query(RefreshToken).filter(
            RefreshToken.id == token,
            RefreshToken.revoked_at.is_(None)
        ).first()

        if token_model:
            token_model.revoke()
            self.db.commit()

    def revoke_all_user_tokens(self, user_id: UUID) -> None:
        """Revoke all refresh tokens for a user.
        
        Args:
            user_id: User ID
        """
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == str(user_id),
            RefreshToken.revoked_at.is_(None)
        ).update({
            RefreshToken.revoked_at: datetime.now(timezone.utc)
        })
        self.db.commit()
