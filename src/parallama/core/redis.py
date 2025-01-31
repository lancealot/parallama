"""Redis client configuration and connection management."""

from typing import Generator

import redis
from redis import Redis

from .config import config

# Create Redis connection pool
redis_pool = redis.ConnectionPool(
    host=config.redis.host,
    port=config.redis.port,
    db=config.redis.db,
    password=config.redis.password,
    decode_responses=True,  # Automatically decode responses to strings
    max_connections=config.redis.max_connections,
    socket_timeout=config.redis.socket_timeout,
    socket_connect_timeout=config.redis.connect_timeout,
    retry_on_timeout=True
)

def get_redis() -> Generator[Redis, None, None]:
    """
    Get a Redis client from the connection pool.
    
    Yields:
        Redis: Redis client
        
    Example:
        ```python
        redis = next(get_redis())
        try:
            value = redis.get("key")
        finally:
            redis.close()
        ```
    """
    client = Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        client.close()

def init_redis() -> None:
    """
    Initialize Redis connection and verify it's working.
    
    Raises:
        redis.ConnectionError: If Redis connection fails
    """
    redis = Redis(connection_pool=redis_pool)
    try:
        redis.ping()
    finally:
        redis.close()
