"""User role model for managing roles and permissions."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.orm import relationship

from .base import BaseModel

class UserRole(BaseModel):
    """Model for storing user roles and permissions."""

    name = Column(String, unique=True, nullable=False)
    permissions = Column(JSON, nullable=False, default=list)
    description = Column(String)

    # Relationships
    users = relationship("User", back_populates="role")

    def __init__(self, **kwargs):
        """Initialize a new user role.
        
        Args:
            **kwargs: Role attributes
        """
        # Convert UUID to string for id
        if "id" in kwargs and isinstance(kwargs["id"], UUID):
            kwargs["id"] = str(kwargs["id"])
        
        # Ensure permissions is a list
        if "permissions" in kwargs:
            if not isinstance(kwargs["permissions"], list):
                kwargs["permissions"] = list(kwargs["permissions"])
        else:
            kwargs["permissions"] = []
        
        super().__init__(**kwargs)

    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            bool: True if role has permission, False otherwise
        """
        return permission in self.permissions

    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if role has any of the specified permissions.
        
        Args:
            permissions: List of permissions to check
            
        Returns:
            bool: True if role has any permission, False otherwise
        """
        return any(p in self.permissions for p in permissions)

    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if role has all specified permissions.
        
        Args:
            permissions: List of permissions to check
            
        Returns:
            bool: True if role has all permissions, False otherwise
        """
        return all(p in self.permissions for p in permissions)

    def add_permission(self, permission: str) -> None:
        """Add a permission to the role.
        
        Args:
            permission: Permission to add
        """
        if permission not in self.permissions:
            self.permissions.append(permission)

    def remove_permission(self, permission: str) -> None:
        """Remove a permission from the role.
        
        Args:
            permission: Permission to remove
        """
        if permission in self.permissions:
            self.permissions.remove(permission)

    def to_dict(self) -> dict:
        """Convert role to dictionary representation.
        
        Returns:
            dict: Dictionary containing role metadata
        """
        return {
            "id": self.id,
            "name": self.name,
            "permissions": self.permissions,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self) -> str:
        """Get string representation of role.
        
        Returns:
            str: String representation
        """
        return f"UserRole(id={self.id}, name={self.name}, permissions={self.permissions})"
