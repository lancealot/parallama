"""Authentication service for JWT token management and role-based access control."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy.orm import Session
from redis import Redis

from ..core.config import config
from ..core.permissions import Permission
from ..models.refresh_token import RefreshToken
from ..services.role import RoleService


class AuthenticationError(Exception):
    """Base class for authentication-related errors."""
    pass


class TokenError(AuthenticationError):
    """Error raised for token-related issues."""
    pass


class AuthService:
    """Service for handling JWT token operations."""

    ALGORITHM = "HS256"
    TOKEN_TYPE = "bearer"

    def __init__(self, db: Session, redis: Redis):
        """Initialize the authentication service."""
        self.secret_key = config.auth.jwt_secret_key
        self.db = db
        self.redis = redis
        self.role_service = RoleService(db)

    def create_access_token(self, user_id: UUID, include_permissions: bool = True) -> str:
        """
        Create a new JWT access token for a user.

        Args:
            user_id: The UUID of the user to create the token for.

        Returns:
            str: The encoded JWT access token.

        Raises:
            TokenError: If there is an error creating the token.
        """
        try:
            expires_delta = config.auth.access_token_expires_delta
            expires_at = datetime.now(timezone.utc) + expires_delta

            to_encode = {
                "sub": str(user_id),
                "exp": expires_at,
                "type": "access"
            }

            if include_permissions:
                # Get user's roles and permissions
                roles = self.role_service.get_user_roles(user_id)
                permissions = set()
                for role in roles:
                    permissions.update(role.get_permissions())
                
                to_encode["roles"] = [role.name for role in roles]
                to_encode["permissions"] = [str(p) for p in permissions]

            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.ALGORITHM
            )

            return encoded_jwt

        except Exception as e:
            raise TokenError(f"Error creating access token: {str(e)}")

    def verify_token(self, token: str) -> Tuple[UUID, List[str]]:
        """
        Verify a JWT token and return the user ID if valid.

        Args:
            token: The JWT token to verify.

        Returns:
            UUID: The user ID from the token if valid.

        Raises:
            TokenError: If the token is invalid, expired, or malformed.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.ALGORITHM]
            )

            user_id = payload.get("sub")
            token_type = payload.get("type")

            if user_id is None:
                raise TokenError("Token missing user ID")

            if token_type != "access":
                raise TokenError("Invalid token type")

            permissions = payload.get("permissions", [])
            return UUID(user_id), permissions

        except JWTError as e:
            raise TokenError(f"Invalid token: {str(e)}")
        except ValueError as e:
            raise TokenError(f"Invalid user ID format: {str(e)}")

    def create_token_response(self, user_id: UUID, include_permissions: bool = True) -> dict:
        """
        Create a complete token response including access token and metadata.

        Args:
            user_id: The UUID of the user to create the token for.

        Returns:
            dict: Token response containing access token and metadata.
        """
        access_token = self.create_access_token(user_id, include_permissions)
        refresh_token, _ = self.create_refresh_token(user_id)
        
        response = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": self.TOKEN_TYPE,
            "expires_in": config.auth.access_token_expire_minutes * 60
        }

        if include_permissions:
            roles = self.role_service.get_user_roles(user_id)
            response["roles"] = [role.name for role in roles]
            permissions = set()
            for role in roles:
                permissions.update(role.get_permissions())
            response["permissions"] = [str(p) for p in permissions]

        return response

    def create_refresh_token(self, user_id: UUID) -> Tuple[str, RefreshToken]:
        """
        Create a new refresh token for a user.

        Args:
            user_id: The UUID of the user to create the token for.

        Returns:
            Tuple[str, RefreshToken]: The raw token string and the token model instance.

        Raises:
            TokenError: If there is an error creating the token.
        """
        try:
            # Generate new token
            token = RefreshToken.generate_token()
            
            # Create token model
            token_model = RefreshToken(
                user_id=user_id,
                expires_at=datetime.now(timezone.utc) + config.auth.refresh_token_expires_delta,
                issued_at=datetime.now(timezone.utc)
            )
            token_model.set_token(token)
            
            # Save to database
            self.db.add(token_model)
            self.db.commit()
            
            return token, token_model

        except Exception as e:
            self.db.rollback()
            raise TokenError(f"Error creating refresh token: {str(e)}")

    def verify_refresh_token(self, token: str) -> Tuple[UUID, RefreshToken]:
        """
        Verify a refresh token and return the user ID if valid.

        Args:
            token: The refresh token to verify.

        Returns:
            Tuple[UUID, RefreshToken]: The user ID and token model if valid.

        Raises:
            TokenError: If the token is invalid, expired, revoked, or rate limited.
        """
        try:
            # Check rate limiting
            token_hash = RefreshToken.hash_token(token)
            rate_key = f"refresh_rate:{token_hash}"
            attempt_count = self.redis.get(rate_key)
            
            if attempt_count and int(attempt_count) >= config.auth.refresh_token_rate_limit:
                raise TokenError("Rate limit exceeded for refresh token")
            
            # Increment rate limit counter
            self.redis.incr(rate_key)
            self.redis.expire(rate_key, 60)  # Reset after 1 minute
            
            # Find token in database
            token_model = self.db.query(RefreshToken).filter(
                RefreshToken.token_hash == token_hash
            ).first()
            
            if not token_model:
                raise TokenError("Invalid refresh token")
            
            # Check if token is valid
            if not token_model.is_valid():
                raise TokenError("Refresh token is expired or revoked")
            
            # Check for token reuse
            reuse_key = f"refresh_reuse:{token_hash}"
            if self.redis.get(reuse_key):
                # Token was already used - revoke entire chain
                self._revoke_token_chain(token_model)
                raise TokenError("Refresh token reuse detected")
            
            # Mark token as used
            self.redis.setex(
                reuse_key,
                config.auth.refresh_token_reuse_window,
                "1"
            )
            
            return token_model.user_id, token_model

        except TokenError:
            raise
        except Exception as e:
            raise TokenError(f"Error verifying refresh token: {str(e)}")

    def refresh_tokens(self, refresh_token: str, include_permissions: bool = True) -> dict:
        """
        Refresh both access and refresh tokens.

        Args:
            refresh_token: The current refresh token.

        Returns:
            dict: New access and refresh tokens with metadata.

        Raises:
            TokenError: If token refresh fails.
        """
        try:
            # Verify current refresh token
            user_id, old_token = self.verify_refresh_token(refresh_token)
            
            # Generate new tokens
            access_token = self.create_access_token(user_id, include_permissions)
            new_refresh_token, new_token_model = self.create_refresh_token(user_id)
            
            # Revoke old token with replacement
            old_token.revoke(new_token_model.id)
            self.db.commit()
            
            response = {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": self.TOKEN_TYPE,
                "expires_in": config.auth.access_token_expire_minutes * 60
            }

            if include_permissions:
                roles = self.role_service.get_user_roles(user_id)
                response["roles"] = [role.name for role in roles]
                permissions = set()
                for role in roles:
                    permissions.update(role.get_permissions())
                response["permissions"] = [str(p) for p in permissions]

            return response

        except Exception as e:
            self.db.rollback()
            raise TokenError(f"Error refreshing tokens: {str(e)}")

    def revoke_refresh_token(self, token: str) -> None:
        """
        Revoke a specific refresh token.

        Args:
            token: The refresh token to revoke.

        Raises:
            TokenError: If token revocation fails.
        """
        try:
            token_hash = RefreshToken.hash_token(token)
            token_model = self.db.query(RefreshToken).filter(
                RefreshToken.token_hash == token_hash
            ).first()
            
            if token_model:
                token_model.revoke()
                self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise TokenError(f"Error revoking refresh token: {str(e)}")

    def revoke_all_user_tokens(self, user_id: UUID) -> None:
        """
        Revoke all refresh tokens for a user.

        Args:
            user_id: The UUID of the user whose tokens should be revoked.

        Raises:
            TokenError: If bulk revocation fails.
        """
        try:
            self.db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None)
            ).update({
                RefreshToken.revoked_at: datetime.now(timezone.utc)
            })
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise TokenError(f"Error revoking all user tokens: {str(e)}")

    def _revoke_token_chain(self, token: RefreshToken) -> None:
        """
        Revoke a token and all its replacements.

        Args:
            token: The RefreshToken model starting the chain.
        """
        try:
            # Revoke the current token
            token.revoke()
            
            # Find and revoke all replacement tokens
            replacement = self.db.query(RefreshToken).filter(
                RefreshToken.id == token.replaced_by_id
            ).first()
            
            while replacement:
                replacement.revoke()
                replacement = self.db.query(RefreshToken).filter(
                    RefreshToken.id == replacement.replaced_by_id
                ).first()
            
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise TokenError(f"Error revoking token chain: {str(e)}")
