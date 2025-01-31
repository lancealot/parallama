"""User model and related functionality."""
import uuid
import hashlib
from sqlalchemy import Column, String, Boolean, event
from sqlalchemy.orm import relationship
from .base import BaseModel

@event.listens_for(BaseModel, 'before_insert', propagate=True)
def set_uuid_before_insert(mapper, connection, target):
    """Convert UUID to string before insert."""
    if hasattr(target, 'id') and isinstance(target.id, uuid.UUID):
        target.id = str(target.id)

class User(BaseModel):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="basic", nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    rate_limits = relationship("GatewayRateLimit", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("GatewayUsageLog", back_populates="user", cascade="all, delete-orphan")

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256 (for testing only)."""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return self.password_hash == self.hash_password(password)

    def set_password(self, password: str) -> None:
        """Set the user's password, hashing it first."""
        self.password_hash = self.hash_password(password)

    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User {self.username}>"
