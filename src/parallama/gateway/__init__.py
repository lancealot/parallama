"""Gateway module for handling LLM service integrations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from fastapi import Request, Response

from .config import (
    GatewayType,
    RateLimitConfig,
    GatewayConfig,
    OllamaConfig,
    OpenAIConfig
)
from .ollama import OllamaGateway
from .openai import OpenAIGateway

class LLMGateway(ABC):
    """Base class for LLM service gateways."""

    @abstractmethod
    async def validate_auth(self, credentials: str) -> bool:
        """Validate authentication credentials.
        
        Args:
            credentials: The authentication token or API key
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        pass

    @abstractmethod
    async def transform_request(self, request: Request) -> Dict[str, Any]:
        """Transform incoming request to LLM service format.
        
        Args:
            request: The incoming FastAPI request
            
        Returns:
            Dict[str, Any]: The transformed request data
        """
        pass

    @abstractmethod
    async def transform_response(self, response: Dict[str, Any]) -> Response:
        """Transform LLM service response to API format.
        
        Args:
            response: The raw response from LLM service
            
        Returns:
            Response: The transformed FastAPI response
        """
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get gateway status and available models.
        
        Returns:
            Dict[str, Any]: Status information including:
                - available models
                - gateway health
                - version information
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close any open connections."""
        pass

    @abstractmethod
    async def handle_error(self, error: Exception) -> Response:
        """Handle errors and return appropriate responses.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Response: An error response with appropriate status code
        """
        pass

class GatewayRegistry:
    """Registry for managing gateway implementations."""

    _instances: Dict[str, LLMGateway] = {}
    _gateway_types: Dict[str, Type[LLMGateway]] = {}

    @classmethod
    def register(cls, gateway_type: str, gateway_class: Type[LLMGateway]) -> None:
        """Register a gateway implementation.
        
        Args:
            gateway_type: The type identifier for this gateway
            gateway_class: The gateway class to register
        """
        cls._gateway_types[gateway_type] = gateway_class

    @classmethod
    def get_gateway(cls, gateway_type: str) -> Optional[LLMGateway]:
        """Get a gateway instance by type.
        
        Args:
            gateway_type: The type identifier for the gateway
            
        Returns:
            Optional[LLMGateway]: The gateway instance if found, None otherwise
        """
        return cls._instances.get(gateway_type)

    @classmethod
    def list_gateways(cls) -> Dict[str, Type[LLMGateway]]:
        """List all registered gateway types.
        
        Returns:
            Dict[str, Type[LLMGateway]]: Map of gateway types to their implementations
        """
        return cls._gateway_types

    @classmethod
    def clear(cls) -> None:
        """Clear all registered gateways."""
        cls._instances.clear()
        cls._gateway_types.clear()

__all__ = [
    'GatewayType',
    'LLMGateway',
    'GatewayRegistry',
    'GatewayConfig',
    'RateLimitConfig',
    'OllamaConfig',
    'OpenAIConfig',
    'OllamaGateway',
    'OpenAIGateway'
]
