from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

class GatewayType(str, Enum):
    """Supported gateway types."""
    OLLAMA = "ollama"
    OPENAI = "openai"

class RateLimitConfig(BaseModel):
    """Rate limiting configuration for a gateway."""
    requests_per_minute: int = Field(default=60, ge=1)
    requests_per_hour: int = Field(default=1000, ge=1)
    tokens_per_minute: Optional[int] = Field(default=None, ge=1)
    tokens_per_hour: Optional[int] = Field(default=None, ge=1)

    @validator("requests_per_hour")
    def validate_hourly_rate(cls, v: int, values: Dict[str, Any]) -> int:
        """Ensure hourly rate is greater than per-minute rate * 60."""
        if "requests_per_minute" in values and v < values["requests_per_minute"] * 60:
            raise ValueError("Hourly rate must be >= per-minute rate * 60")
        return v

class GatewayConfig(BaseModel):
    """Base configuration for LLM gateways.
    
    This class defines the common configuration parameters that all
    gateway implementations should support. Gateway-specific parameters
    can be added through the custom_config field.
    """
    name: str
    type: GatewayType
    enabled: bool = True
    base_path: str
    host: Optional[str] = None
    port: Optional[int] = None
    rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig)
    model_mappings: Dict[str, str] = Field(default_factory=dict)
    custom_config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic model configuration."""
        use_enum_values = True

    @validator("base_path")
    def validate_base_path(cls, v: str) -> str:
        """Ensure base_path starts with a forward slash."""
        if not v.startswith("/"):
            v = f"/{v}"
        return v.rstrip("/")  # Remove trailing slashes

    def get_endpoint_url(self) -> Optional[str]:
        """Construct the full endpoint URL if host is provided."""
        if not self.host:
            return None
            
        url = self.host.rstrip("/")
        if self.port:
            url = f"{url}:{self.port}"
        return f"{url}{self.base_path}"

    def get_model_mapping(self, model_name: str) -> str:
        """Get the internal model name for a given external model name."""
        return self.model_mappings.get(model_name, model_name)

class OllamaConfig(GatewayConfig):
    """Ollama-specific gateway configuration."""
    type: GatewayType = GatewayType.OLLAMA
    base_path: str = "/ollama/v1"
    host: str = "http://localhost"
    port: int = 11434

class OpenAIConfig(GatewayConfig):
    """OpenAI-compatible gateway configuration."""
    type: GatewayType = GatewayType.OPENAI
    base_path: str = "/openai/v1"
    compatibility_mode: bool = True
