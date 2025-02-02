"""Rate limiting service."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import redis
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.rate_limit import GatewayRateLimit, GatewayUsageLog

def get_redis():
    """Get Redis client."""
    yield redis.Redis(host='localhost', port=6379, db=0)

class RateLimitService:
    """Service for managing rate limits."""

    def __init__(self, db: Session):
        """Initialize the service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.redis = next(get_redis())

    async def check_rate_limit(
        self,
        user_id: UUID,
        gateway_type: str,
        tokens: Optional[int] = None
    ) -> None:
        """Check if the request exceeds rate limits.
        
        Args:
            user_id: User ID
            gateway_type: Gateway type (e.g., 'ollama', 'openai')
            tokens: Number of tokens used in request
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        # Get rate limits for user and gateway
        limits = self.db.query(GatewayRateLimit).filter_by(
            user_id=str(user_id),
            gateway_type=gateway_type
        ).first()

        if not limits:
            return

        # Check Redis connection
        try:
            self.redis.ping()
        except redis.ConnectionError:
            raise redis.ConnectionError("Rate limiting service unavailable")

        # Get current usage from Redis
        pipe = self.redis.pipeline()
        now = datetime.utcnow()
        hour_key = f"{user_id}:{gateway_type}:tokens:hour:{now.strftime('%Y-%m-%d-%H')}"
        day_key = f"{user_id}:{gateway_type}:tokens:day:{now.strftime('%Y-%m-%d')}"
        hour_req_key = f"{user_id}:{gateway_type}:requests:hour:{now.strftime('%Y-%m-%d-%H')}"
        day_req_key = f"{user_id}:{gateway_type}:requests:day:{now.strftime('%Y-%m-%d')}"

        # Get current usage
        pipe.get(hour_key)
        pipe.get(day_key)
        pipe.get(hour_req_key)
        pipe.get(day_req_key)

        results = pipe.execute()

        # Check token limits
        if tokens:
            hour_tokens = int(results[0] or 0)
            day_tokens = int(results[1] or 0)
            if hour_tokens + tokens > limits.token_limit_hourly:
                raise HTTPException(
                    status_code=429,
                    detail=f"Hourly token limit ({limits.token_limit_hourly}) exceeded"
                )
            if day_tokens + tokens > limits.token_limit_daily:
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily token limit ({limits.token_limit_daily}) exceeded"
                )

        # Check request limits
        hour_reqs = int(results[2] or 0)
        day_reqs = int(results[3] or 0)
        if hour_reqs + 1 > limits.request_limit_hourly:
            raise HTTPException(
                status_code=429,
                detail=f"Hourly request limit ({limits.request_limit_hourly}) exceeded"
            )
        if day_reqs + 1 > limits.request_limit_daily:
            raise HTTPException(
                status_code=429,
                detail=f"Daily request limit ({limits.request_limit_daily}) exceeded"
            )

        # Increment usage
        if tokens:
            pipe.incrby(hour_key, tokens)
            pipe.incrby(day_key, tokens)
        pipe.incr(hour_req_key)
        pipe.incr(day_req_key)

        # Set expiry
        pipe.expire(hour_key, 3600)  # 1 hour
        pipe.expire(day_key, 86400)  # 24 hours
        pipe.expire(hour_req_key, 3600)
        pipe.expire(day_req_key, 86400)

        pipe.execute()

    async def record_usage(
        self,
        user_id: UUID,
        gateway_type: str,
        endpoint: str,
        tokens: Optional[int],
        model_name: Optional[str],
        duration: int,
        status_code: int,
        error_message: Optional[str] = None
    ) -> None:
        """Record API usage.
        
        Args:
            user_id: User ID
            gateway_type: Gateway type (e.g., 'ollama', 'openai')
            endpoint: API endpoint
            tokens: Number of tokens used
            model_name: Model name
            duration: Request duration in milliseconds
            status_code: Response status code
            error_message: Error message if request failed
        """
        log = GatewayUsageLog(
            user_id=str(user_id),
            gateway_type=gateway_type,
            endpoint=endpoint,
            tokens=tokens,
            model_name=model_name,
            request_duration=duration,
            status_code=status_code,
            error_message=error_message,
            timestamp=datetime.utcnow()
        )
        self.db.add(log)
        self.db.commit()

    def close(self):
        """Close Redis connection."""
        try:
            self.redis.close()
        except:
            pass

    async def cleanup(self):
        """Cleanup resources."""
        self.close()
