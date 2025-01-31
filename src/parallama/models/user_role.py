from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, String
from sqlalchemy.orm import relationship

from parallama.models.base import Base

class UserRole(Base):
    """
    UserRole model for managing the many-to-many relationship between users and roles.
    Includes metadata about when the role was assigned and by whom.
    """
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(String(36), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    assigned_by = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    role = relationship("Role", backref="user_roles")
    user = relationship("User", foreign_keys=[user_id], backref="role_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])

    def __init__(self, user_id, role_id, assigned_by=None, expires_at=None):
        """
        Initialize a new user role assignment.
        
        Args:
            user_id: ID of the user receiving the role
            role_id: ID of the role being assigned
            assigned_by: Optional ID of the user making the assignment
            expires_at: Optional expiration date for the role assignment
        """
        self.user_id = user_id
        self.role_id = role_id
        self.assigned_by = assigned_by
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        """
        Check if the role assignment has expired.
        
        Returns:
            bool: True if the assignment has expired, False otherwise
        """
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def __repr__(self) -> str:
        return f"<UserRole(user_id='{self.user_id}', role_id='{self.role_id}')>"
