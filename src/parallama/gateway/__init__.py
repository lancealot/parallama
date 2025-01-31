"""Gateway module for managing LLM service integrations.

This module provides the infrastructure for integrating with various LLM services
through a unified gateway interface. It includes components for routing requests,
managing configurations, and handling different gateway implementations.
"""

from .base import LLMGateway
from .ollama import OllamaGateway
from .config import (
    GatewayType,
    GatewayConfig,
    RateLimitConfig,
    OllamaConfig,
    OpenAIConfig,
)
from .registry import GatewayRegistry
from .router import router as gateway_router

# Register gateway implementations
GatewayRegistry.register(GatewayType.OLLAMA, OllamaGateway)

__all__ = [
    # Base interface
    "LLMGateway",
    
    # Gateway implementations
    "OllamaGateway",
    
    # Configuration
    "GatewayType",
    "GatewayConfig",
    "RateLimitConfig",
    "OllamaConfig",
    "OpenAIConfig",
    
    # Registry
    "GatewayRegistry",
    
    # Router
    "gateway_router",
]
