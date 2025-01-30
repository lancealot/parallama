"""API Key model and related functionality."""
import secrets
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel

class APIKey(BaseModel):
    """API Key model for authentication."""
    __tablename__ = "api_keys"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    revoked_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="api_keys")

    @staticmethod
    def generate_key() -> str:
        """Generate a new API key."""
        # Format: pk_live_[32 chars]
        return f"pk_live_{secrets.token_urlsafe(24)}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for storage."""
        # In a real implementation, use a proper key hashing algorithm
        # This is a placeholder that should be replaced with a secure hashing method
        from hashlib import sha256
        return sha256(key.encode()).hexdigest()

    def set_key(self, key: str) -> None:
        """Set the API key hash."""
        self.key_hash = self.hash_key(key)

    @staticmethod
    def verify_key(key: str, key_hash: str) -> bool:
        """Verify an API key against a stored hash."""
        return APIKey.hash_key(key) == key_hash

    def __repr__(self) -> str:
        """String representation of the API key."""
        return f"<APIKey user_id={self.user_id}>"
