"""Gateway configuration handling."""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Union
import os

@dataclass
class EndpointConfig:
    """Configuration for API endpoints."""

    url: str
    method: str = "POST"
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    tokens_per_minute: int = 10000
    requests_per_day: int = 1000
    tokens_per_day: int = 100000

@dataclass
class TokenCounterConfig:
    """Configuration for token counting."""

    enabled: bool = True
    cache_size: int = 1000
    cache_ttl: int = 3600  # 1 hour default
    model_tokens: Dict[str, int] = field(default_factory=dict)
    default_tokens: int = 1000
    count_method: str = "simple"
    token_multiplier: float = 1.0

@dataclass
class GatewayConfig:
    """Base configuration for gateways."""

    gateway_type: str
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    headers: Optional[Dict[str, str]] = None

    @classmethod
    def from_env(cls, gateway_type: str, prefix: str = "") -> "GatewayConfig":
        """Create configuration from environment variables.
        
        Args:
            gateway_type: Gateway type identifier
            prefix: Optional prefix for environment variables
            
        Returns:
            GatewayConfig: Gateway configuration
            
        Example:
            For prefix="OLLAMA_":
            - OLLAMA_BASE_URL -> base_url
            - OLLAMA_TIMEOUT -> timeout
            - OLLAMA_MAX_RETRIES -> max_retries
            - OLLAMA_HEADERS -> headers (as JSON string)
        """
        # Build full prefix
        if prefix and not prefix.endswith("_"):
            prefix = f"{prefix}_"

        # Get base URL
        base_url = os.getenv(f"{prefix}BASE_URL", "")
        if not base_url:
            raise ValueError(f"Missing required environment variable: {prefix}BASE_URL")

        # Get optional settings
        timeout = int(os.getenv(f"{prefix}TIMEOUT", "30"))
        max_retries = int(os.getenv(f"{prefix}MAX_RETRIES", "3"))

        # Get optional headers
        headers_str = os.getenv(f"{prefix}HEADERS", "")
        headers = None
        if headers_str:
            try:
                import json
                headers = json.loads(headers_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid headers JSON: {str(e)}")

        return cls(
            gateway_type=gateway_type,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            headers=headers
        )

@dataclass
class OllamaConfig(GatewayConfig):
    """Configuration for Ollama gateway."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = 30,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None
    ):
        """Initialize Ollama configuration.
        
        Args:
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            headers: Optional request headers
        """
        super().__init__(
            gateway_type="ollama",
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            headers=headers
        )

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Create Ollama configuration from environment variables."""
        # Get base URL
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "30"))
        max_retries = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))

        # Get optional headers
        headers_str = os.getenv("OLLAMA_HEADERS", "")
        headers = None
        if headers_str:
            try:
                import json
                headers = json.loads(headers_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid headers JSON: {str(e)}")

        return cls(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            headers=headers
        )

class OpenAIConfig(GatewayConfig):
    """Configuration for OpenAI compatibility gateway."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1/",
        timeout: int = 30,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None
    ):
        """Initialize OpenAI configuration.
        
        Args:
            api_key: OpenAI API key
            base_url: OpenAI API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            headers: Optional request headers
        """
        super().__init__(
            gateway_type="openai",
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            headers=headers
        )
        self.api_key = api_key

    @classmethod
    def from_env(cls) -> "OpenAIConfig":
        """Create OpenAI configuration from environment variables."""
        # Get API key first
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("Missing required environment variable: OPENAI_API_KEY")

        # Get base URL and other settings
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/")
        timeout = int(os.getenv("OPENAI_TIMEOUT", "30"))
        max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))

        # Get optional headers
        headers_str = os.getenv("OPENAI_HEADERS", "")
        headers = None
        if headers_str:
            try:
                import json
                headers = json.loads(headers_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid headers JSON: {str(e)}")

        return cls(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            headers=headers
        )

__all__ = [
    "GatewayConfig",
    "OllamaConfig",
    "OpenAIConfig",
    "TokenCounterConfig",
    "EndpointConfig",
    "RateLimitConfig"
]
