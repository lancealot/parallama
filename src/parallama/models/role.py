from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
import json

from parallama.core.permissions import Permission
from parallama.models.base import Base

class Role(Base):
    """
    Role model for storing user roles and their associated permissions.
    """
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, unique=True, nullable=False)
    permissions = Column(Text, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, name: str, permissions: List[Permission], description: str = None):
        """
        Initialize a new role.
        
        Args:
            name: Unique name for the role
            permissions: List of Permission enums defining role capabilities
            description: Optional description of the role
        """
        self.name = name
        self.permissions = json.dumps([str(p) for p in permissions])  # Store permissions as JSON string
        self.description = description

    def has_permission(self, permission: Permission) -> bool:
        """
        Check if the role has a specific permission.
        
        Args:
            permission: Permission to check for
            
        Returns:
            bool: True if the role has the permission, False otherwise
        """
        return str(permission) in json.loads(self.permissions)

    def add_permission(self, permission: Permission) -> None:
        """
        Add a permission to the role if it doesn't already have it.
        
        Args:
            permission: Permission to add
        """
        perms = json.loads(self.permissions)
        if not str(permission) in perms:
            perms.append(str(permission))
            self.permissions = json.dumps(perms)

    def remove_permission(self, permission: Permission) -> None:
        """
        Remove a permission from the role if it has it.
        
        Args:
            permission: Permission to remove
        """
        perms = json.loads(self.permissions)
        if str(permission) in perms:
            perms.remove(str(permission))
            self.permissions = json.dumps(perms)

    def get_permissions(self) -> List[Permission]:
        """
        Get the list of permissions as Permission enums.
        
        Returns:
            List[Permission]: List of Permission enums
        """
        return [Permission(p) for p in json.loads(self.permissions)]

    def __repr__(self) -> str:
        return f"<Role(name='{self.name}', permissions={len(self.permissions)})>"
