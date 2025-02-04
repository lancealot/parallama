"""Application configuration."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    """Authentication configuration."""
    jwt_secret_key: str = Field(default="")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=30)
    refresh_token_rate_limit: int = Field(default=5)
    refresh_token_reuse_window: int = Field(default=60)
    password_hash_rounds: int = Field(default=12)


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = Field(default=os.getenv('PARALLAMA_DB_URL', "postgresql://parallama:development@localhost:5432/parallama"))
    pool_size: int = Field(default=5)
    max_overflow: int = Field(default=10)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=1800)
    echo_sql: bool = Field(default=False)


class RedisConfig(BaseModel):
    """Redis configuration."""
    url: str = Field(default=os.getenv('PARALLAMA_REDIS_URL', "redis://localhost:6379/0"))
    max_connections: int = Field(default=10)
    socket_timeout: int = Field(default=5)
    connect_timeout: int = Field(default=5)

    @property
    def host(self) -> str:
        """Get Redis host from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return parsed.hostname or "localhost"
    
    @property
    def port(self) -> int:
        """Get Redis port from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return parsed.port or 6379
    
    @property
    def db(self) -> int:
        """Get Redis database from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        path = parsed.path.lstrip('/')
        return int(path) if path else 0
    
    @property
    def password(self) -> Optional[str]:
        """Get Redis password from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return parsed.password


class GatewayConfig(BaseModel):
    """Gateway configuration."""
    enabled: list[str] = Field(default_factory=lambda: ["ollama", "openai"])
    discovery_enabled: bool = Field(default=True)
    discovery_cache_ttl: int = Field(default=300)
    include_metrics: bool = Field(default=True)


class OllamaConfig(BaseModel):
    """Ollama gateway configuration."""
    host: str = Field(default="http://localhost")
    port: int = Field(default=11434)
    base_path: str = Field(default="/ollama/v1")
    default_model: str = Field(default="llama2")


class OpenAIPerformanceConfig(BaseModel):
    """OpenAI gateway performance configuration."""
    connection_pool_size: int = Field(default=100)
    request_timeout: int = Field(default=60)
    max_retries: int = Field(default=3)
    batch_size: int = Field(default=10)


class TokenCounterConfig(BaseModel):
    """Token counter configuration."""
    enabled: bool = Field(default=True)
    cache_size: int = Field(default=1000)
    cache_ttl: int = Field(default=3600)


class OpenAIConfig(BaseModel):
    """OpenAI compatibility gateway configuration."""
    base_path: str = Field(default="/openai/v1")
    compatibility_mode: bool = Field(default=True)
    model_mappings: dict[str, str] = Field(
        default_factory=lambda: {
            "gpt-3.5-turbo": "llama2",
            "gpt-4": "llama2:70b"
        }
    )
    performance: OpenAIPerformanceConfig = Field(default_factory=OpenAIPerformanceConfig)
    token_counter: TokenCounterConfig = Field(default_factory=TokenCounterConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    directory: Path = Field(default=Path("/var/log/parallama"))
    max_size: str = Field(default="100M")
    backup_count: int = Field(default=10)


class Settings(BaseModel):
    """Main application configuration."""
    auth: AuthConfig = Field(default_factory=AuthConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# Create global settings instance
settings = Settings()

def load_settings(config_path: Optional[Path] = None) -> None:
    """
    Load settings from file and environment variables.
    
    Args:
        config_path: Optional path to config file
    """
    global settings
    
    # Load from file if provided
    if config_path and config_path.exists():
        settings = Settings.parse_file(config_path)
    
    # Override with environment variables
    if os.getenv('PARALLAMA_JWT_SECRET'):
        settings.auth.jwt_secret_key = os.getenv('PARALLAMA_JWT_SECRET')
    
    if os.getenv('PARALLAMA_DB_URL'):
        settings.database.url = os.getenv('PARALLAMA_DB_URL')
    
    if os.getenv('PARALLAMA_REDIS_URL'):
        settings.redis.url = os.getenv('PARALLAMA_REDIS_URL')


# Initialize settings
load_settings()
