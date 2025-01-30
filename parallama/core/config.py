"""Application configuration."""

from datetime import timedelta
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

    @property
    def access_token_expires_delta(self) -> timedelta:
        """Get access token expiration delta."""
        return timedelta(minutes=self.access_token_expire_minutes)

    @property
    def refresh_token_expires_delta(self) -> timedelta:
        """Get refresh token expiration delta."""
        return timedelta(days=self.refresh_token_expire_days)


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = Field(default="postgresql://localhost/parallama")
    pool_size: int = Field(default=5)
    max_overflow: int = Field(default=10)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=1800)
    echo_sql: bool = Field(default=False)


class RedisConfig(BaseModel):
    """Redis configuration."""
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: Optional[str] = Field(default=None)
    max_connections: int = Field(default=10)
    socket_timeout: int = Field(default=5)
    connect_timeout: int = Field(default=5)


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


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    directory: Path = Field(default=Path("/var/log/parallama"))
    max_size: str = Field(default="100M")
    backup_count: int = Field(default=10)


class Config(BaseModel):
    """Main application configuration."""
    auth: AuthConfig = Field(default_factory=AuthConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# Create global config instance
config = Config()

def load_config(config_path: Optional[Path] = None) -> None:
    """
    Load configuration from file and environment variables.
    
    Args:
        config_path: Optional path to config file
    """
    global config
    
    # Load from file if provided
    if config_path and config_path.exists():
        config = Config.parse_file(config_path)
    
    # Override with environment variables
    # TODO: Implement environment variable loading
    pass
