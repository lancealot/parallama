"""Model for role assignments."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .base import BaseModel

class RoleAssignment(BaseModel):
    """Model for storing role assignments."""

    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role_id = Column(String, ForeignKey("user_roles.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="role_assignments")
    role = relationship("UserRole", back_populates="role_assignments")

    def __init__(self, **kwargs):
        """Initialize a new role assignment.
        
        Args:
            **kwargs: Role assignment attributes
        """
        # Convert UUID to string for ids
        if "user_id" in kwargs and isinstance(kwargs["user_id"], UUID):
            kwargs["user_id"] = str(kwargs["user_id"])
        if "role_id" in kwargs and isinstance(kwargs["role_id"], UUID):
            kwargs["role_id"] = str(kwargs["role_id"])
        
        super().__init__(**kwargs)

    def is_active(self) -> bool:
        """Check if role assignment is active.
        
        Returns:
            bool: True if active, False if expired
        """
        return not self.expires_at or self.expires_at > datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Convert role assignment to dictionary representation.
        
        Returns:
            dict: Dictionary containing role assignment metadata
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self) -> str:
        """Get string representation of role assignment.
        
        Returns:
            str: String representation
        """
        return (
            f"RoleAssignment(id={self.id}, user_id={self.user_id}, "
            f"role_id={self.role_id}, expires_at={self.expires_at})"
        )
