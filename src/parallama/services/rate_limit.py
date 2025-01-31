"""Rate limiting service for managing API usage limits and tracking."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from redis import Redis, ConnectionError, RedisError
from sqlalchemy.orm import Session

from ..core.redis import get_redis
from ..models.rate_limit import GatewayRateLimit, GatewayUsageLog

class RateLimitService:
    """Service for managing rate limits and usage tracking."""

    def __init__(self, db: Session):
        """Initialize the rate limit service.
        
        Args:
            db: Database session
            
        Raises:
            HTTPException: If Redis connection fails
        """
        self.db = db
        try:
            self.redis = next(get_redis())
            # Test connection
            self.redis.ping()
        except (ConnectionError, RedisError) as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting service temporarily unavailable"
            ) from e

    def _get_rate_limit_keys(self, user_id: UUID, gateway_type: str) -> Tuple[str, str, str, str]:
        """Get Redis keys for rate limiting.
        
        Args:
            user_id: User ID
            gateway_type: Gateway type (e.g., 'ollama', 'openai')
            
        Returns:
            Tuple of Redis keys for hourly tokens, daily tokens,
            hourly requests, and daily requests
        """
        base = f"rate_limit:{user_id}:{gateway_type}"
        hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
        day = datetime.utcnow().strftime("%Y-%m-%d")
        return (
            f"{base}:tokens:hour:{hour}",
            f"{base}:tokens:day:{day}",
            f"{base}:requests:hour:{hour}",
            f"{base}:requests:day:{day}"
        )

    async def get_user_limits(self, user_id: UUID, gateway_type: str) -> Optional[GatewayRateLimit]:
        """Get rate limits for a user and gateway.
        
        Args:
            user_id: User ID
            gateway_type: Gateway type
            
        Returns:
            Rate limit configuration if found. If both specific and wildcard limits exist,
            returns the specific limits.
        """
        # First try to find specific limits for this gateway
        limits = self.db.query(GatewayRateLimit).filter(
            GatewayRateLimit.user_id == user_id,
            GatewayRateLimit.gateway_type == gateway_type
        ).first()
        
        if limits:
            return limits
            
        # If no specific limits, check for wildcard limits
        return self.db.query(GatewayRateLimit).filter(
            GatewayRateLimit.user_id == user_id,
            GatewayRateLimit.gateway_type == "*"
        ).first()

    async def check_rate_limit(
        self, 
        user_id: UUID, 
        gateway_type: str,
        tokens: Optional[int] = None
    ) -> bool:
        """Check if a request would exceed rate limits.
        
        Args:
            user_id: User ID
            gateway_type: Gateway type
            tokens: Number of tokens for this request (if known)
            
        Returns:
            True if request is allowed, False if it would exceed limits
            
        Raises:
            HTTPException: If rate limit is exceeded
            ValueError: If tokens is negative
        """
        if tokens is not None and tokens < 0:
            raise ValueError("Token count cannot be negative")

        limits = await self.get_user_limits(user_id, gateway_type)
        if not limits:
            return True  # No limits configured

        if (limits.token_limit_hourly == 0 or limits.token_limit_daily == 0 or 
            limits.request_limit_hourly == 0 or limits.request_limit_daily == 0):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limits are set to zero"
            )

        # Get current usage for both specific and wildcard gateway types
        specific_keys = self._get_rate_limit_keys(user_id, gateway_type)
        wildcard_keys = self._get_rate_limit_keys(user_id, "*")

        try:
            pipe = self.redis.pipeline()
            # Get specific gateway usage
            pipe.get(specific_keys[0])  # hourly tokens
            pipe.get(specific_keys[1])  # daily tokens
            pipe.get(specific_keys[2])  # hourly requests
            pipe.get(specific_keys[3])  # daily requests
            # Get wildcard gateway usage
            pipe.get(wildcard_keys[0])  # hourly tokens
            pipe.get(wildcard_keys[1])  # daily tokens
            pipe.get(wildcard_keys[2])  # hourly requests
            pipe.get(wildcard_keys[3])  # daily requests
            current = pipe.execute()
        except (ConnectionError, RedisError) as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting service temporarily unavailable"
            ) from e

        # Split results into specific and wildcard usage
        specific_usage = current[:4]
        wildcard_usage = current[4:]

        print(f"\nRate Limit Check:")
        print(f"Gateway Type: {gateway_type}")
        print(f"Limit Config: {limits.gateway_type} (hourly={limits.token_limit_hourly}, daily={limits.token_limit_daily})")
        print(f"Tokens for this request: {tokens}")
        print(f"Specific keys: {specific_keys}")
        print(f"Wildcard keys: {wildcard_keys}")
        print(f"Specific usage: {specific_usage}")
        print(f"Wildcard usage: {wildcard_usage}")

        # Combine usage if using wildcard limits
        if limits.gateway_type == "*":
            tokens_hour = int(specific_usage[0] or 0) + int(wildcard_usage[0] or 0)
            tokens_day = int(specific_usage[1] or 0) + int(wildcard_usage[1] or 0)
            requests_hour = int(specific_usage[2] or 0) + int(wildcard_usage[2] or 0)
            requests_day = int(specific_usage[3] or 0) + int(wildcard_usage[3] or 0)
            print(f"Using wildcard limits - Combined usage: tokens_hour={tokens_hour}, tokens_day={tokens_day}")
        else:
            tokens_hour = int(specific_usage[0] or 0)
            tokens_day = int(specific_usage[1] or 0)
            requests_hour = int(specific_usage[2] or 0)
            requests_day = int(specific_usage[3] or 0)
            print(f"Using specific limits - Usage: tokens_hour={tokens_hour}, tokens_day={tokens_day}")

        print(f"Checking limits:")
        print(f"- Hourly tokens: {tokens_hour} + {tokens} <= {limits.token_limit_hourly}")
        print(f"- Daily tokens: {tokens_day} + {tokens} <= {limits.token_limit_daily}")
        print(f"- Hourly requests: {requests_hour} + 1 <= {limits.request_limit_hourly}")
        print(f"- Daily requests: {requests_day} + 1 <= {limits.request_limit_daily}")

        # Check token limits if tokens are provided
        if tokens is not None:
            if (limits.token_limit_hourly and 
                tokens_hour + tokens > limits.token_limit_hourly):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Hourly token limit ({limits.token_limit_hourly}) exceeded"
                )

            if (limits.token_limit_daily and 
                tokens_day + tokens > limits.token_limit_daily):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Daily token limit ({limits.token_limit_daily}) exceeded"
                )

        # Check request limits
        if (limits.request_limit_hourly and 
            requests_hour + 1 > limits.request_limit_hourly):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Hourly request limit ({limits.request_limit_hourly}) exceeded"
            )

        if (limits.request_limit_daily and 
            requests_day + 1 > limits.request_limit_daily):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily request limit ({limits.request_limit_daily}) exceeded"
            )

        # Do not update counters here, let record_usage handle it

        return True

    async def record_usage(
        self,
        user_id: UUID,
        gateway_type: str,
        endpoint: str,
        tokens: Optional[int] = None,
        model_name: Optional[str] = None,
        duration: Optional[int] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Record API usage.
        
        Args:
            user_id: User ID
            gateway_type: Gateway type
            endpoint: API endpoint path
            tokens: Number of tokens used
            model_name: Name of the model used
            duration: Request duration in milliseconds
            status_code: HTTP status code
            error_message: Error message if request failed
        """
        try:
            # Record usage in database first
            usage_log = GatewayUsageLog(
                user_id=user_id,
                gateway_type=gateway_type,
                endpoint=endpoint,
                model_name=model_name,
                tokens_used=tokens,
                request_duration=duration,
                status_code=status_code,
                error_message=error_message,
                timestamp=datetime.utcnow()
            )
            self.db.add(usage_log)
            self.db.commit()

            # Update Redis counters for both specific and wildcard types
            specific_keys = self._get_rate_limit_keys(user_id, gateway_type)
            wildcard_keys = self._get_rate_limit_keys(user_id, "*")

            try:
                pipe = self.redis.pipeline()
                
                # Update specific gateway counters
                pipe.incr(specific_keys[2])  # hourly requests
                pipe.expire(specific_keys[2], 3600)  # 1 hour
                pipe.incr(specific_keys[3])  # daily requests
                pipe.expire(specific_keys[3], 86400)  # 24 hours

                if tokens is not None:
                    pipe.incrby(specific_keys[0], tokens)  # hourly tokens
                    pipe.expire(specific_keys[0], 3600)  # 1 hour
                    pipe.incrby(specific_keys[1], tokens)  # daily tokens
                    pipe.expire(specific_keys[1], 86400)  # 24 hours

                # Update wildcard gateway counters
                pipe.incr(wildcard_keys[2])  # hourly requests
                pipe.expire(wildcard_keys[2], 3600)  # 1 hour
                pipe.incr(wildcard_keys[3])  # daily requests
                pipe.expire(wildcard_keys[3], 86400)  # 24 hours

                if tokens is not None:
                    pipe.incrby(wildcard_keys[0], tokens)  # hourly tokens
                    pipe.expire(wildcard_keys[0], 3600)  # 1 hour
                    pipe.incrby(wildcard_keys[1], tokens)  # daily tokens
                    pipe.expire(wildcard_keys[1], 86400)  # 24 hours

                pipe.execute()
            except (ConnectionError, RedisError):
                # Redis errors during usage recording are not critical
                pass

        except Exception:
            self.db.rollback()
            raise

    async def cleanup_old_logs(self, days: int = 30) -> None:
        """Clean up old usage logs.
        
        Args:
            days: Number of days of logs to keep
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            self.db.query(GatewayUsageLog).filter(
                GatewayUsageLog.timestamp < cutoff
            ).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def close(self) -> None:
        """Close Redis connection."""
        self.redis.close()
