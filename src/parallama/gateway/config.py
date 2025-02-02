"""Gateway configuration models."""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator

class GatewayType(str, Enum):
    """Supported gateway types."""
    OLLAMA = "ollama"
    OPENAI = "openai"

class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    requests_per_hour: Optional[int] = Field(None, ge=0)
    requests_per_day: Optional[int] = Field(None, ge=0)
    tokens_per_hour: Optional[int] = Field(None, ge=0)
    tokens_per_day: Optional[int] = Field(None, ge=0)

    @field_validator("requests_per_hour", "requests_per_day", "tokens_per_hour", "tokens_per_day")
    @classmethod
    def validate_limits(cls, v):
        """Validate rate limits are non-negative."""
        if v is not None and v < 0:
            raise ValueError("Rate limits must be non-negative")
        return v

class GatewayConfig(BaseModel):
    """Base gateway configuration."""

    name: str
    base_path: str
    enabled: bool = True
    rate_limits: Optional[RateLimitConfig] = None

    @field_validator("base_path")
    @classmethod
    def validate_base_path(cls, v):
        """Validate base path starts with /."""
        if not v.startswith("/"):
            raise ValueError("Base path must start with /")
        return v

class OllamaConfig(GatewayConfig):
    """Ollama gateway configuration."""

    ollama_url: str = "http://localhost:11434"
    model_mappings: Dict[str, str] = {}

class TokenCounterConfig(BaseModel):
    """Token counter configuration."""

    enabled: bool = True
    cache_size: int = Field(1000, ge=0)
    cache_ttl: int = Field(3600, ge=0)  # in seconds

class PerformanceConfig(BaseModel):
    """Performance configuration."""

    connection_pool_size: int = Field(100, ge=1)
    request_timeout: int = Field(60, ge=1)  # in seconds
    max_retries: int = Field(3, ge=0)
    batch_size: int = Field(10, ge=1)

class EndpointConfig(BaseModel):
    """Endpoint configuration."""

    chat: bool = True
    completions: bool = True
    embeddings: bool = False
    edits: bool = False
    moderations: bool = False

class OpenAIConfig(GatewayConfig):
    """OpenAI gateway configuration."""

    compatibility_mode: bool = True
    model_mappings: Dict[str, str] = {
        "gpt-3.5-turbo": "llama2",
        "gpt-4": "llama2:70b"
    }
    token_counter: TokenCounterConfig = TokenCounterConfig()
    performance: PerformanceConfig = PerformanceConfig()
    endpoints: EndpointConfig = EndpointConfig()

__all__ = [
    'GatewayType',
    'RateLimitConfig',
    'GatewayConfig',
    'OllamaConfig',
    'OpenAIConfig',
    'TokenCounterConfig',
    'PerformanceConfig',
    'EndpointConfig'
]
