"""Service for managing API keys."""

from datetime import datetime, timezone
from typing import List, Optional, Union
import secrets
import string
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from redis import Redis

from ..models.api_key import APIKey
from ..core.exceptions import ResourceNotFoundError, DuplicateResourceError

class APIKeyError(Exception):
    """Base class for API key related errors."""
    pass

class APIKeyService:
    """Service for managing API keys."""

    def __init__(self, db: Session, redis: Redis):
        """Initialize API key service.
        
        Args:
            db: Database session
            redis: Redis client
        """
        self.db = db
        self.redis = redis
        self.key_length = 32
        self.key_prefix = "pk_"
        self.key_cache_ttl = 300  # 5 minutes

    def _generate_key(self) -> str:
        """Generate a random API key.
        
        Returns:
            str: Generated API key
        """
        alphabet = string.ascii_letters + string.digits
        key = ''.join(secrets.choice(alphabet) for _ in range(self.key_length))
        return f"{self.key_prefix}{key}"

    def create_key(
        self,
        user_id: str,
        name: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> APIKey:
        """Create a new API key.
        
        Args:
            user_id: User ID
            name: Optional key name
            expires_at: Optional expiry date
            
        Returns:
            APIKey: Created API key
            
        Raises:
            DuplicateResourceError: If key with name already exists for user
            APIKeyError: If key creation fails
        """
        try:
            # Check for duplicate name
            if name:
                existing = self.db.query(APIKey).filter(
                    APIKey.user_id == user_id,
                    APIKey.name == name
                ).first()
                if existing:
                    raise DuplicateResourceError(
                        f"API key with name '{name}' already exists for user {user_id}"
                    )

            # Generate key
            key_value = self._generate_key()
            
            # Create key
            key = APIKey(
                user_id=user_id,
                name=name,
                expires_at=expires_at,
                created_at=datetime.now(timezone.utc)
            )
            key.set_key(key_value)
            
            try:
                self.db.add(key)
                self.db.commit()
                return key
            except Exception as e:
                self.db.rollback()
                raise APIKeyError(f"Failed to create API key: {str(e)}")

        except Exception as e:
            raise APIKeyError(f"Failed to create API key: {str(e)}")

    def get_key(self, key_id: Union[str, UUID]) -> Optional[APIKey]:
        """Get API key by ID.
        
        Args:
            key_id: Key ID (string or UUID)
            
        Returns:
            Optional[APIKey]: API key if found, None otherwise
        """
        key_id_str = str(key_id)
        return self.db.query(APIKey).filter(APIKey.id == key_id_str).first()

    def get_key_by_value(self, key: str) -> Optional[APIKey]:
        """Get API key by value.
        
        Args:
            key: API key value
            
        Returns:
            Optional[APIKey]: API key if found, None otherwise
        """
        return self.db.query(APIKey).filter(APIKey.key == key).first()

    def list_keys(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        include_expired: bool = False
    ) -> List[APIKey]:
        """List API keys.
        
        Args:
            user_id: Optional user ID to filter by
            include_expired: Whether to include expired keys
            
        Returns:
            List[APIKey]: List of API keys
            
        Raises:
            APIKeyError: If listing keys fails
        """
        try:
            query = self.db.query(APIKey)

            if user_id:
                query = query.filter(APIKey.user_id == str(user_id))

            if not include_expired:
                query = query.filter(
                    (APIKey.expires_at.is_(None)) |
                    (APIKey.expires_at > datetime.now(timezone.utc))
                )

            return query.all()
        except Exception as e:
            raise APIKeyError(f"Failed to list API keys: {str(e)}")

    def verify_key(self, key: str) -> Optional[str]:
        """Verify an API key.
        
        Args:
            key: API key to verify
            
        Returns:
            Optional[str]: User ID if key is valid, None otherwise
            
        Raises:
            APIKeyError: If verification fails
        """
        try:
            # Check cache first
            cache_key = f"api_key:{key}"
            try:
                cached_user_id = self.redis.get(cache_key)
                if cached_user_id:
                    return cached_user_id.decode()
            except Exception as e:
                raise APIKeyError(f"Failed to check Redis cache: {str(e)}")

            # Get key from database
            api_key = self.get_key_by_value(key)
            if not api_key:
                return None

            # Check if key is expired
            if api_key.is_expired():
                return None

            # Check if key is revoked
            if api_key.is_revoked():
                return None

            # Update last used timestamp
            api_key.update_last_used()
            try:
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                raise APIKeyError(f"Failed to update last used timestamp: {str(e)}")

            # Cache key
            try:
                self.redis.setex(
                    cache_key,
                    self.key_cache_ttl,
                    api_key.user_id
                )
            except Exception as e:
                # Log but don't fail if caching fails
                print(f"Failed to cache API key: {str(e)}")

            return api_key.user_id
        except APIKeyError:
            raise
        except Exception as e:
            raise APIKeyError(f"Failed to verify API key: {str(e)}")

    def revoke_key(self, key_id: str) -> None:
        """Revoke an API key.
        
        Args:
            key_id: Key ID
            
        Raises:
            ResourceNotFoundError: If key not found
            APIKeyError: If revocation fails
        """
        try:
            key = self.get_key(key_id)
            if not key:
                raise ResourceNotFoundError(f"API key {key_id} not found")

            key.revoke()
            try:
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                raise APIKeyError(f"Failed to revoke API key: {str(e)}")

            # Clear cache
            try:
                cache_key = f"api_key:{key.key}"
                self.redis.delete(cache_key)
            except Exception as e:
                # Log but don't fail if cache clear fails
                print(f"Failed to clear API key cache: {str(e)}")
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise APIKeyError(f"Failed to revoke API key: {str(e)}")

    def revoke_all_user_keys(self, user_id: str) -> None:
        """Revoke all API keys for a user.
        
        Args:
            user_id: User ID
            
        Raises:
            APIKeyError: If revocation fails
        """
        try:
            keys = self.list_keys(user_id, include_expired=True)
            for key in keys:
                key.revoke()
                try:
                    cache_key = f"api_key:{key.key}"
                    self.redis.delete(cache_key)
                except Exception as e:
                    # Log but don't fail if cache clear fails
                    print(f"Failed to clear API key cache: {str(e)}")

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise APIKeyError(f"Failed to revoke user API keys: {str(e)}")

    def delete_key(self, key_id: str) -> None:
        """Delete an API key.
        
        Args:
            key_id: Key ID
            
        Raises:
            ResourceNotFoundError: If key not found
            APIKeyError: If deletion fails
        """
        try:
            key = self.get_key(key_id)
            if not key:
                raise ResourceNotFoundError(f"API key {key_id} not found")

            # Clear cache
            try:
                cache_key = f"api_key:{key.key}"
                self.redis.delete(cache_key)
            except Exception as e:
                # Log but don't fail if cache clear fails
                print(f"Failed to clear API key cache: {str(e)}")

            self.db.delete(key)
            self.db.commit()
        except ResourceNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            raise APIKeyError(f"Failed to delete API key: {str(e)}")

    def delete_all_user_keys(self, user_id: str) -> None:
        """Delete all API keys for a user.
        
        Args:
            user_id: User ID
            
        Raises:
            APIKeyError: If deletion fails
        """
        try:
            keys = self.list_keys(user_id, include_expired=True)
            for key in keys:
                try:
                    cache_key = f"api_key:{key.key}"
                    self.redis.delete(cache_key)
                except Exception as e:
                    # Log but don't fail if cache clear fails
                    print(f"Failed to clear API key cache: {str(e)}")
                self.db.delete(key)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise APIKeyError(f"Failed to delete user API keys: {str(e)}")
