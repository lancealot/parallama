"""Gateway module for managing LLM service integrations.

This module provides the infrastructure for integrating with various LLM services
through a unified gateway interface. It includes components for routing requests,
managing configurations, and handling different gateway implementations.
"""

from .base import LLMGateway
from .config import (
    GatewayType,
    GatewayConfig,
    RateLimitConfig,
    OllamaConfig,
    OpenAIConfig,
)
from .registry import GatewayRegistry
from .router import router as gateway_router

__all__ = [
    # Base interface
    "LLMGateway",
    
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
