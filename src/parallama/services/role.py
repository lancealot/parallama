"""Role service for managing user roles and permissions."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models.user_role import UserRole
from ..core.exceptions import ResourceNotFoundError, DuplicateResourceError

class RoleService:
    """Service for managing user roles."""

    def __init__(self, db: Session):
        """Initialize role service.
        
        Args:
            db: Database session
        """
        self.db = db

    def create_role(self, name: str, permissions: List[str]) -> UserRole:
        """Create a new role.
        
        Args:
            name: Role name
            permissions: List of permission names
            
        Returns:
            UserRole: Created role
            
        Raises:
            DuplicateResourceError: If role with name already exists
        """
        try:
            role = UserRole(
                name=name,
                permissions=permissions,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(role)
            self.db.commit()
            return role
        except IntegrityError:
            self.db.rollback()
            raise DuplicateResourceError(f"Role '{name}' already exists")

    def get_role(self, role_id: UUID) -> Optional[UserRole]:
        """Get role by ID.
        
        Args:
            role_id: Role ID
            
        Returns:
            Optional[UserRole]: Role if found, None otherwise
        """
        return self.db.query(UserRole).filter(UserRole.id == str(role_id)).first()

    def get_role_by_name(self, name: str) -> Optional[UserRole]:
        """Get role by name.
        
        Args:
            name: Role name
            
        Returns:
            Optional[UserRole]: Role if found, None otherwise
        """
        return self.db.query(UserRole).filter(UserRole.name == name).first()

    def list_roles(self) -> List[UserRole]:
        """List all roles.
        
        Returns:
            List[UserRole]: List of roles
        """
        return self.db.query(UserRole).all()

    def update_role(
        self,
        role_id: UUID,
        name: Optional[str] = None,
        permissions: Optional[List[str]] = None
    ) -> UserRole:
        """Update role.
        
        Args:
            role_id: Role ID
            name: New role name
            permissions: New permissions list
            
        Returns:
            UserRole: Updated role
            
        Raises:
            ResourceNotFoundError: If role not found
            DuplicateResourceError: If new name already exists
        """
        role = self.get_role(role_id)
        if not role:
            raise ResourceNotFoundError(f"Role {role_id} not found")

        try:
            if name is not None:
                role.name = name
            if permissions is not None:
                role.permissions = permissions
            role.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            return role
        except IntegrityError:
            self.db.rollback()
            raise DuplicateResourceError(f"Role '{name}' already exists")

    def delete_role(self, role_id: UUID) -> None:
        """Delete role.
        
        Args:
            role_id: Role ID
            
        Raises:
            ResourceNotFoundError: If role not found
        """
        role = self.get_role(role_id)
        if not role:
            raise ResourceNotFoundError(f"Role {role_id} not found")

        self.db.delete(role)
        self.db.commit()

    def has_permission(self, role_name: str, permission: str) -> bool:
        """Check if role has permission.
        
        Args:
            role_name: Role name
            permission: Permission to check
            
        Returns:
            bool: True if role has permission, False otherwise
        """
        role = self.get_role_by_name(role_name)
        if not role:
            return False
        return permission in role.permissions

    def has_any_permission(self, role_name: str, permissions: List[str]) -> bool:
        """Check if role has any of the permissions.
        
        Args:
            role_name: Role name
            permissions: List of permissions to check
            
        Returns:
            bool: True if role has any permission, False otherwise
        """
        role = self.get_role_by_name(role_name)
        if not role:
            return False
        return any(p in role.permissions for p in permissions)

    def has_all_permissions(self, role_name: str, permissions: List[str]) -> bool:
        """Check if role has all permissions.
        
        Args:
            role_name: Role name
            permissions: List of permissions to check
            
        Returns:
            bool: True if role has all permissions, False otherwise
        """
        role = self.get_role_by_name(role_name)
        if not role:
            return False
        return all(p in role.permissions for p in permissions)
