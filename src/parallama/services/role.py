from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from parallama.core.permissions import Permission, DefaultRoles
from parallama.models.role import Role
from parallama.models.user_role import UserRole
from parallama.core.exceptions import ResourceNotFoundError, DuplicateResourceError

class RoleService:
    """
    Service for managing roles and user role assignments.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_role(self, name: str, permissions: List[Permission], description: str = None) -> Role:
        """
        Create a new role with specified permissions.
        
        Args:
            name: Unique name for the role
            permissions: List of permissions to assign to the role
            description: Optional description of the role
            
        Returns:
            Role: The created role
            
        Raises:
            DuplicateResourceError: If a role with the given name already exists
        """
        try:
            role = Role(name=name, permissions=permissions, description=description)
            self.db.add(role)
            self.db.commit()
            return role
        except IntegrityError:
            self.db.rollback()
            raise DuplicateResourceError(f"Role with name '{name}' already exists")

    def get_role(self, role_id: UUID) -> Optional[Role]:
        """
        Get a role by its ID.
        
        Args:
            role_id: UUID of the role to retrieve
            
        Returns:
            Optional[Role]: The role if found, None otherwise
        """
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_role_by_name(self, name: str) -> Optional[Role]:
        """
        Get a role by its name.
        
        Args:
            name: Name of the role to retrieve
            
        Returns:
            Optional[Role]: The role if found, None otherwise
        """
        return self.db.query(Role).filter(Role.name == name).first()

    def assign_role_to_user(
        self, 
        user_id: UUID, 
        role_id: UUID, 
        assigned_by: Optional[UUID] = None,
        expires_at: Optional[datetime] = None
    ) -> UserRole:
        """
        Assign a role to a user.
        
        Args:
            user_id: ID of the user to assign the role to
            role_id: ID of the role to assign
            assigned_by: Optional ID of the user making the assignment
            expires_at: Optional expiration date for the role assignment
            
        Returns:
            UserRole: The created user role assignment
            
        Raises:
            ResourceNotFoundError: If the role doesn't exist
            DuplicateResourceError: If the user already has this role
        """
        role = self.get_role(role_id)
        if not role:
            raise ResourceNotFoundError(f"Role with ID '{role_id}' not found")

        try:
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by,
                expires_at=expires_at
            )
            self.db.add(user_role)
            self.db.commit()
            return user_role
        except IntegrityError:
            self.db.rollback()
            raise DuplicateResourceError(f"User already has role '{role.name}'")

    def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> None:
        """
        Remove a role from a user.
        
        Args:
            user_id: ID of the user to remove the role from
            role_id: ID of the role to remove
        """
        self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        ).delete()
        self.db.commit()

    def get_user_roles(self, user_id: UUID) -> List[Role]:
        """
        Get all active (non-expired) roles for a user.
        
        Args:
            user_id: ID of the user to get roles for
            
        Returns:
            List[Role]: List of active roles for the user
        """
        now = datetime.utcnow()
        user_roles = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            (UserRole.expires_at.is_(None) | (UserRole.expires_at > now))
        ).all()
        return [ur.role for ur in user_roles]

    def check_permission(self, user_id: UUID, permission: Permission) -> bool:
        """
        Check if a user has a specific permission through any of their roles.
        
        Args:
            user_id: ID of the user to check permissions for
            permission: Permission to check for
            
        Returns:
            bool: True if the user has the permission, False otherwise
        """
        roles = self.get_user_roles(user_id)
        return any(role.has_permission(permission) for role in roles)

    def initialize_default_roles(self) -> None:
        """
        Initialize the default roles in the system if they don't exist.
        Should be called during application startup.
        """
        for role_name, role_data in DefaultRoles.get_all_roles().items():
            if not self.get_role_by_name(role_name):
                self.create_role(
                    name=role_name,
                    permissions=role_data["permissions"],
                    description=f"Default {role_name} role"
                )
