"""Gateway Rate Limit model and related functionality."""
from sqlalchemy import Column, String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel

class GatewayRateLimit(BaseModel):
    """Rate limit configuration for users per gateway."""
    __tablename__ = "gateway_rate_limits"
    __table_args__ = (
        UniqueConstraint('user_id', 'gateway_type', name='uq_user_gateway_limit'),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    gateway_type = Column(String, nullable=False)
    token_limit_hourly = Column(Integer)
    token_limit_daily = Column(Integer)
    request_limit_hourly = Column(Integer)
    request_limit_daily = Column(Integer)

    # Relationships
    user = relationship("User", back_populates="rate_limits")

    @classmethod
    def create_default(cls, user_id: UUID, gateway_type: str) -> "GatewayRateLimit":
        """Create a rate limit with default values."""
        return cls(
            user_id=user_id,
            gateway_type=gateway_type,
            token_limit_hourly=10000,    # 10k tokens per hour
            token_limit_daily=100000,    # 100k tokens per day
            request_limit_hourly=100,    # 100 requests per hour
            request_limit_daily=1000     # 1000 requests per day
        )

    def update_limits(
        self,
        token_limit_hourly: int = None,
        token_limit_daily: int = None,
        request_limit_hourly: int = None,
        request_limit_daily: int = None
    ) -> None:
        """Update rate limits with new values."""
        if token_limit_hourly is not None:
            self.token_limit_hourly = token_limit_hourly
        if token_limit_daily is not None:
            self.token_limit_daily = token_limit_daily
        if request_limit_hourly is not None:
            self.request_limit_hourly = request_limit_hourly
        if request_limit_daily is not None:
            self.request_limit_daily = request_limit_daily

    def __repr__(self) -> str:
        """String representation of the rate limit."""
        return (
            f"<GatewayRateLimit user_id={self.user_id} "
            f"gateway={self.gateway_type}>"
        )
