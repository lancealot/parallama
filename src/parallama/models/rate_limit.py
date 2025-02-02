"""Models for rate limiting and usage tracking."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .base import BaseModel

class GatewayRateLimit(BaseModel):
    """Model for storing gateway rate limits."""

    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    gateway_type = Column(String, nullable=False)
    token_limit_hourly = Column(Integer, nullable=False)
    token_limit_daily = Column(Integer, nullable=False)
    request_limit_hourly = Column(Integer, nullable=False)
    request_limit_daily = Column(Integer, nullable=False)

    # Relationships
    user = relationship("User", back_populates="rate_limits")

    def to_dict(self) -> dict:
        """Convert rate limit to dictionary representation.
        
        Returns:
            dict: Dictionary containing rate limit metadata
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "gateway_type": self.gateway_type,
            "token_limit_hourly": self.token_limit_hourly,
            "token_limit_daily": self.token_limit_daily,
            "request_limit_hourly": self.request_limit_hourly,
            "request_limit_daily": self.request_limit_daily,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class GatewayUsageLog(BaseModel):
    """Model for tracking gateway usage."""

    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    gateway_type = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    tokens_used = Column(Integer)
    model_name = Column(String)
    request_duration = Column(Integer)  # in milliseconds
    status_code = Column(Integer)
    error_message = Column(String)

    # Relationships
    user = relationship("User", back_populates="usage_logs")

    def to_dict(self) -> dict:
        """Convert usage log to dictionary representation.
        
        Returns:
            dict: Dictionary containing usage log metadata
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "gateway_type": self.gateway_type,
            "endpoint": self.endpoint,
            "tokens_used": self.tokens_used,
            "model_name": self.model_name,
            "request_duration": self.request_duration,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def create_log(
        cls,
        user_id: str,
        gateway_type: str,
        endpoint: str,
        tokens_used: Optional[int] = None,
        model_name: Optional[str] = None,
        request_duration: Optional[int] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> "GatewayUsageLog":
        """Create a new usage log entry.
        
        Args:
            user_id: User ID
            gateway_type: Gateway type (e.g., "ollama", "openai")
            endpoint: API endpoint
            tokens_used: Number of tokens used
            model_name: Model name
            request_duration: Request duration in milliseconds
            status_code: HTTP status code
            error_message: Error message if any
            
        Returns:
            GatewayUsageLog: Created usage log
        """
        return cls(
            user_id=user_id,
            gateway_type=gateway_type,
            endpoint=endpoint,
            tokens_used=tokens_used,
            model_name=model_name,
            request_duration=request_duration,
            status_code=status_code,
            error_message=error_message
        )
