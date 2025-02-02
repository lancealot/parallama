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
    role_id = Column(String, ForeignKey("user_roles.id"))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))

    # Relationships
    role = relationship("UserRole", back_populates="users")
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
        
        # Convert UUID to string for id and role_id
        if "id" in kwargs and isinstance(kwargs["id"], UUID):
            kwargs["id"] = str(kwargs["id"])
        if "role_id" in kwargs and isinstance(kwargs["role_id"], UUID):
            kwargs["role_id"] = str(kwargs["role_id"])
        
        super().__init__(**kwargs)

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
        return self.role and self.role.has_permission(permission)

    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions.
        
        Args:
            permissions: List of permissions to check
            
        Returns:
            bool: True if user has any permission, False otherwise
        """
        return self.role and self.role.has_any_permission(permissions)

    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if user has all specified permissions.
        
        Args:
            permissions: List of permissions to check
            
        Returns:
            bool: True if user has all permissions, False otherwise
        """
        return self.role and self.role.has_all_permissions(permissions)

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
            "role_id": self.role_id,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            result["password_hash"] = self.password_hash
        
        if self.role:
            result["role"] = self.role.to_dict()
            result["permissions"] = self.role.permissions
        
        return result

    def __repr__(self) -> str:
        """Get string representation of user.
        
        Returns:
            str: String representation
        """
        return (
            f"User(id={self.id}, username={self.username}, "
            f"email={self.email}, role_id={self.role_id})"
        )
