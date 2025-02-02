"""API key model for managing API access."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import hashlib

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .base import BaseModel

class APIKey(BaseModel):
    """Model for storing API keys."""

    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String)
    key = Column(String, unique=True, nullable=False)
    key_hash = Column(String, unique=True, nullable=False)
    description = Column(String)
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="api_keys")

    @staticmethod
    def generate_key() -> str:
        """Generate a new API key.
        
        Returns:
            str: Generated API key
        """
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        key = ''.join(secrets.choice(alphabet) for _ in range(32))
        return f"pk_{key}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key.
        
        Args:
            key: API key to hash
            
        Returns:
            str: Hashed key
        """
        return hashlib.sha256(key.encode()).hexdigest()

    def set_key(self, key: str) -> None:
        """Set the API key value and hash.
        
        Args:
            key: API key value
        """
        self.key = key
        self.key_hash = self.hash_key(key)

    def __init__(self, **kwargs):
        """Initialize a new API key.
        
        Args:
            **kwargs: Key attributes
        """
        # Convert UUID to string for id and user_id
        if "id" in kwargs and isinstance(kwargs["id"], UUID):
            kwargs["id"] = str(kwargs["id"])
        if "user_id" in kwargs and isinstance(kwargs["user_id"], UUID):
            kwargs["user_id"] = str(kwargs["user_id"])
        
        super().__init__(**kwargs)

    def is_expired(self) -> bool:
        """Check if key is expired.
        
        Returns:
            bool: True if key is expired, False otherwise
        """
        return self.expires_at and self.expires_at < datetime.now(timezone.utc)

    def is_revoked(self) -> bool:
        """Check if key is revoked.
        
        Returns:
            bool: True if key is revoked, False otherwise
        """
        return self.revoked_at is not None

    def is_valid(self) -> bool:
        """Check if key is valid.
        
        Returns:
            bool: True if key is valid, False otherwise
        """
        return not (self.is_expired() or self.is_revoked())

    def revoke(self) -> None:
        """Revoke this key."""
        self.revoked_at = datetime.now(timezone.utc)

    def update_last_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.now(timezone.utc)

    def to_dict(self, include_key: bool = False) -> dict:
        """Convert key to dictionary representation.
        
        Args:
            include_key: Whether to include the actual key value
            
        Returns:
            dict: Dictionary containing key metadata
        """
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_valid": self.is_valid()
        }
        
        if include_key:
            result["key"] = self.key
        
        return result

    def __repr__(self) -> str:
        """Get string representation of key.
        
        Returns:
            str: String representation
        """
        return (
            f"APIKey(id={self.id}, user_id={self.user_id}, "
            f"name={self.name}, expires_at={self.expires_at})"
        )
