"""Refresh token model for managing token-based authentication."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .base import BaseModel

class RefreshToken(BaseModel):
    """Model for storing refresh tokens."""

    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def __init__(self, **kwargs):
        """Initialize a new refresh token.
        
        Args:
            **kwargs: Token attributes
        """
        # Convert UUID to string for id and user_id
        if "id" in kwargs and isinstance(kwargs["id"], UUID):
            kwargs["id"] = str(kwargs["id"])
        if "user_id" in kwargs and isinstance(kwargs["user_id"], UUID):
            kwargs["user_id"] = str(kwargs["user_id"])
        
        super().__init__(**kwargs)

    def is_expired(self) -> bool:
        """Check if token is expired.
        
        Returns:
            bool: True if token is expired, False otherwise
        """
        return self.expires_at < datetime.now(timezone.utc)

    def is_revoked(self) -> bool:
        """Check if token is revoked.
        
        Returns:
            bool: True if token is revoked, False otherwise
        """
        return self.revoked_at is not None

    def is_valid(self) -> bool:
        """Check if token is valid.
        
        Returns:
            bool: True if token is valid, False otherwise
        """
        return not (self.is_expired() or self.is_revoked())

    def revoke(self) -> None:
        """Revoke this token."""
        self.revoked_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Convert token to dictionary representation.
        
        Returns:
            dict: Dictionary containing token metadata
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_valid": self.is_valid()
        }

    def __repr__(self) -> str:
        """Get string representation of token.
        
        Returns:
            str: String representation
        """
        return (
            f"RefreshToken(id={self.id}, user_id={self.user_id}, "
            f"expires_at={self.expires_at}, revoked_at={self.revoked_at})"
        )
