"""Refresh Token model and related functionality."""
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel

class RefreshToken(BaseModel):
    """Refresh Token model for JWT refresh functionality."""
    __tablename__ = "refresh_tokens"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, index=True)
    issued_at = Column(DateTime(timezone=True), nullable=False, server_default="now()")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    replaced_by_id = Column(UUID(as_uuid=True), ForeignKey("refresh_tokens.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
    replaced_by = relationship(
        "RefreshToken",
        foreign_keys=[replaced_by_id],
        remote_side="RefreshToken.id",
        uselist=False,
        post_update=True
    )

    @staticmethod
    def generate_token() -> str:
        """Generate a new refresh token."""
        # Format: rt_[48 chars]
        return f"rt_{secrets.token_urlsafe(36)}"

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a refresh token for storage."""
        from hashlib import sha256
        return sha256(token.encode()).hexdigest()

    def set_token(self, token: str, expiry_days: int = 30) -> None:
        """Set the refresh token hash and expiration."""
        self.token_hash = self.hash_token(token)
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)

    @staticmethod
    def verify_token(token: str, token_hash: str) -> bool:
        """Verify a refresh token against a stored hash."""
        return RefreshToken.hash_token(token) == token_hash

    def is_valid(self) -> bool:
        """Check if the refresh token is valid."""
        now = datetime.now(timezone.utc)
        return (
            not self.revoked_at 
            and self.expires_at > now 
            and not self.replaced_by_id
        )

    def revoke(self, replacement_token_id: UUID = None) -> None:
        """Revoke the refresh token."""
        self.revoked_at = datetime.now(timezone.utc)
        if replacement_token_id:
            self.replaced_by_id = replacement_token_id

    def __repr__(self) -> str:
        """String representation of the refresh token."""
        return f"<RefreshToken user_id={self.user_id}>"
