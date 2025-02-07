"""User model for managing user accounts."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import bcrypt

from .base import BaseModel

class User(BaseModel):
    """Model for storing user information."""

    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))

    # Relationships
    role_assignments = relationship("RoleAssignment", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    rate_limits = relationship("GatewayRateLimit", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("GatewayUsageLog", back_populates="user", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        """Initialize a new user.
        
        Args:
            **kwargs: User attributes
        """
        # Hash password if provided
        if "password" in kwargs:
            kwargs["password_hash"] = self.hash_password(kwargs.pop("password"))
        
        # Convert UUID to string for id
        if "id" in kwargs and isinstance(kwargs["id"], UUID):
            kwargs["id"] = str(kwargs["id"])
        
        # Handle role assignment if role is provided
        role = kwargs.pop("role", None)
        super().__init__(**kwargs)
        if role:
            self.role = role

    @property
    def roles(self) -> List["UserRole"]:
        """Get user's active roles.
        
        Returns:
            List[UserRole]: List of active roles
        """
        now = datetime.now(timezone.utc)
        return [
            assignment.role for assignment in self.role_assignments
            if not assignment.expires_at or assignment.expires_at > now
        ]

    @property
    def role(self) -> Optional["UserRole"]:
        """Get user's primary role.
        
        Returns:
            Optional[UserRole]: Primary role if any
        """
        roles = self.roles
        return roles[0] if roles else None

    @role.setter
    def role(self, role: "UserRole") -> None:
        """Set user's primary role.
        
        Args:
            role: Role to set
        """
        from .role_assignment import RoleAssignment
        
        # Clear existing assignments
        self.role_assignments = []
        
        # Create new assignment
        if role:
            assignment = RoleAssignment(
                user_id=self.id,
                role_id=role.id,
                created_at=datetime.now(timezone.utc)
            )
            self.role_assignments.append(assignment)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            password.encode(),
            self.password_hash.encode()
        )

    def update_password(self, password: str) -> None:
        """Update user's password.
        
        Args:
            password: New plain text password
        """
        self.password_hash = self.hash_password(password)
        self.updated_at = datetime.now(timezone.utc)

    def update_last_login(self) -> None:
        """Update user's last login timestamp."""
        self.last_login = datetime.now(timezone.utc)
        self.updated_at = self.last_login

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        return any(role.has_permission(permission) for role in self.roles)

    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions.
        
        Args:
            permissions: List of permissions to check
            
        Returns:
            bool: True if user has any permission, False otherwise
        """
        return any(role.has_any_permission(permissions) for role in self.roles)

    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if user has all specified permissions.
        
        Args:
            permissions: List of permissions to check
            
        Returns:
            bool: True if user has all permissions, False otherwise
        """
        return any(role.has_all_permissions(permissions) for role in self.roles)

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert user to dictionary representation.
        
        Args:
            include_sensitive: Whether to include sensitive fields
            
        Returns:
            dict: Dictionary containing user metadata
        """
        result = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            result["password_hash"] = self.password_hash
        
        roles = self.roles
        if roles:
            result["roles"] = [role.to_dict() for role in roles]
            result["permissions"] = list(set().union(*(role.permissions for role in roles)))
        
        return result

    def __repr__(self) -> str:
        """Get string representation of user.
        
        Returns:
            str: String representation
        """
        return (
            f"User(id={self.id}, username={self.username}, "
            f"email={self.email}, roles={len(self.roles)})"
        )
