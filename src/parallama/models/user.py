"""User model and related functionality."""
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from passlib.context import CryptContext
from .base import BaseModel

# Configure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return pwd_context.verify(password, self.password_hash)

    def set_password(self, password: str) -> None:
        """Set the user's password, hashing it first."""
        self.password_hash = self.hash_password(password)

    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User {self.username}>"
