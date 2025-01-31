"""Rate limiting models for tracking usage and limits."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import BaseModel
from .user import User

class GatewayRateLimit(BaseModel):
    """Stores rate limit configurations per user and gateway."""
    __tablename__ = "gateway_rate_limits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    gateway_type = Column(String(50), nullable=False)
    token_limit_hourly = Column(Integer)
    token_limit_daily = Column(Integer)
    request_limit_hourly = Column(Integer)
    request_limit_daily = Column(Integer)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="rate_limits")

    class Config:
        """Pydantic model configuration."""
        orm_mode = True

class GatewayUsageLog(BaseModel):
    """Tracks API usage per user and gateway."""
    __tablename__ = "gateway_usage_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    gateway_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    endpoint = Column(String(255), nullable=False)
    model_name = Column(String(255))
    tokens_used = Column(Integer)
    request_duration = Column(Integer)  # Duration in milliseconds
    status_code = Column(Integer)
    error_message = Column(String)

    # Relationships
    user = relationship("User", back_populates="usage_logs")

    class Config:
        """Pydantic model configuration."""
        orm_mode = True
