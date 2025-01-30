"""Authentication service for JWT token management."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt

from ..core.config import config


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

    def __init__(self):
        """Initialize the authentication service."""
        self.secret_key = config.auth.jwt_secret_key

    def create_access_token(self, user_id: UUID) -> str:
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

            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.ALGORITHM
            )

            return encoded_jwt

        except Exception as e:
            raise TokenError(f"Error creating access token: {str(e)}")

    def verify_token(self, token: str) -> UUID:
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

            return UUID(user_id)

        except JWTError as e:
            raise TokenError(f"Invalid token: {str(e)}")
        except ValueError as e:
            raise TokenError(f"Invalid user ID format: {str(e)}")

    def create_token_response(self, user_id: UUID) -> dict:
        """
        Create a complete token response including access token and metadata.

        Args:
            user_id: The UUID of the user to create the token for.

        Returns:
            dict: Token response containing access token and metadata.
        """
        access_token = self.create_access_token(user_id)
        
        return {
            "access_token": access_token,
            "token_type": self.TOKEN_TYPE,
            "expires_in": config.auth.access_token_expire_minutes * 60
        }
