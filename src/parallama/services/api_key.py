"""API Key service for managing API key operations."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from redis import Redis

from ..models.api_key import APIKey


class APIKeyError(Exception):
    """Base class for API key-related errors."""
    pass


class APIKeyService:
    """Service for handling API key operations."""

    def __init__(self, db: Session, redis: Redis):
        """Initialize the API key service."""
        self.db = db
        self.redis = redis

    def create_key(self, user_id: UUID, description: str = None) -> str:
        """
        Create a new API key for a user.

        Args:
            user_id: The UUID of the user to create the key for.
            description: Optional description for the key.

        Returns:
            str: The generated API key.

        Raises:
            APIKeyError: If there is an error creating the key.
        """
        try:
            # Generate new key
            key = APIKey.generate_key()
            
            # Create key model
            key_model = APIKey(
                user_id=user_id,
                description=description
            )
            key_model.set_key(key)
            
            # Save to database
            self.db.add(key_model)
            self.db.commit()
            
            return key

        except Exception as e:
            self.db.rollback()
            raise APIKeyError(f"Error creating API key: {str(e)}")

    def verify_key(self, key: str) -> Optional[UUID]:
        """
        Verify an API key and return the user ID if valid.

        Args:
            key: The API key to verify.

        Returns:
            Optional[UUID]: The user ID if the key is valid, None otherwise.

        Raises:
            APIKeyError: If there is an error verifying the key.
        """
        try:
            # Check cache first
            cache_key = f"apikey:{APIKey.hash_key(key)}"
            cached_user_id = self.redis.get(cache_key)
            
            if cached_user_id:
                return UUID(cached_user_id.decode())
            
            # Find key in database
            key_model = self.db.query(APIKey).filter(
                APIKey.key_hash == APIKey.hash_key(key),
                APIKey.revoked_at.is_(None)
            ).first()
            
            if not key_model:
                return None
            
            if key_model:
                try:
                    # Update last used timestamp
                    key_model.last_used_at = datetime.now(timezone.utc)
                    self.db.commit()
                    
                    # Cache the result only after successful commit
                    self.redis.setex(
                        cache_key,
                        300,  # Cache for 5 minutes
                        str(key_model.user_id)
                    )
                    
                    return key_model.user_id
                except Exception as e:
                    self.db.rollback()
                    raise APIKeyError(f"Error verifying API key: {str(e)}")
            
            return None

        except Exception as e:
            raise APIKeyError(f"Error verifying API key: {str(e)}")

    def revoke_key(self, key_id: UUID) -> None:
        """
        Revoke an API key.

        Args:
            key_id: The UUID of the key to revoke.

        Raises:
            APIKeyError: If there is an error revoking the key.
        """
        try:
            key_model = self.db.query(APIKey).filter(
                APIKey.id == key_id,
                APIKey.revoked_at.is_(None)
            ).first()
            
            if key_model:
                key_model.revoked_at = datetime.now(timezone.utc)
                self.db.commit()
                
                # Invalidate cache
                self.redis.delete(f"apikey:{key_model.key_hash}")

        except Exception as e:
            self.db.rollback()
            raise APIKeyError(f"Error revoking API key: {str(e)}")

    def list_keys(self, user_id: UUID) -> List[dict]:
        """
        List all API keys for a user.

        Args:
            user_id: The UUID of the user whose keys to list.

        Returns:
            List[dict]: List of API key metadata dictionaries.

        Raises:
            APIKeyError: If there is an error listing the keys.
        """
        try:
            keys = self.db.query(APIKey).filter(
                APIKey.user_id == user_id
            ).all()
            
            return [{
                'id': key.id,
                'created_at': key.created_at,
                'last_used_at': key.last_used_at,
                'description': key.description,
                'revoked_at': key.revoked_at
            } for key in keys]

        except Exception as e:
            raise APIKeyError(f"Error listing API keys: {str(e)}")
