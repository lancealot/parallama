"""Gateway registry for managing LLM gateways."""

from typing import Dict, Optional, Type
from fastapi import HTTPException

from .base import BaseGateway
from .config import GatewayConfig, OllamaConfig, OpenAIConfig
from .ollama import OllamaGateway
from .openai import OpenAIGateway
from ..services.rate_limit import RateLimitService

class GatewayRegistry:
    """Registry for managing LLM gateways."""

    def __init__(self, rate_limit_service: Optional[RateLimitService] = None):
        """Initialize gateway registry.
        
        Args:
            rate_limit_service: Optional rate limiting service
        """
        self._rate_limit_service = rate_limit_service
        self._gateways: Dict[str, BaseGateway] = {}
        self._gateway_types: Dict[str, Type[BaseGateway]] = {
            "ollama": OllamaGateway,
            "openai": OpenAIGateway
        }
        self._config_types: Dict[str, Type[GatewayConfig]] = {
            "ollama": OllamaConfig,
            "openai": OpenAIConfig
        }

    def register_gateway_type(
        self,
        gateway_type: str,
        gateway_class: Type[BaseGateway],
        config_class: Type[GatewayConfig]
    ) -> None:
        """Register a new gateway type.
        
        Args:
            gateway_type: Gateway type identifier
            gateway_class: Gateway class
            config_class: Configuration class
        """
        self._gateway_types[gateway_type] = gateway_class
        self._config_types[gateway_type] = config_class

    def get_gateway(self, gateway_type: str) -> BaseGateway:
        """Get gateway instance.
        
        Args:
            gateway_type: Gateway type identifier
            
        Returns:
            BaseGateway: Gateway instance
            
        Raises:
            HTTPException: If gateway type is not supported
        """
        if gateway_type not in self._gateways:
            if gateway_type not in self._gateway_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported gateway type: {gateway_type}"
                )
            
            # Create gateway instance
            gateway_class = self._gateway_types[gateway_type]
            config_class = self._config_types[gateway_type]
            try:
                config = config_class.from_env()
            except ValueError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Gateway configuration error: {str(e)}"
                )
            
            self._gateways[gateway_type] = gateway_class(
                config=config,
                rate_limit_service=self._rate_limit_service
            )
        
        return self._gateways[gateway_type]

    async def cleanup(self) -> None:
        """Cleanup all gateway instances."""
        for gateway in self._gateways.values():
            await gateway.cleanup()
        self._gateways.clear()

    # Class-level storage for gateways and types
    _instance_gateways: Dict[str, BaseGateway] = {}
    _instance_gateway_types: Dict[str, Type[BaseGateway]] = {
        "ollama": OllamaGateway,
        "openai": OpenAIGateway
    }
    _instance_config_types: Dict[str, Type[GatewayConfig]] = {
        "ollama": OllamaConfig,
        "openai": OpenAIConfig
    }

    @classmethod
    async def clear(cls) -> None:
        """Clear all registered gateways."""
        # This is a class method to allow clearing gateways in tests
        for gateway in cls._instance_gateways.values():
            await gateway.cleanup()
        cls._instance_gateways.clear()
        cls._instance_gateway_types = {
            "ollama": OllamaGateway,
            "openai": OpenAIGateway
        }
        cls._instance_config_types = {
            "ollama": OllamaConfig,
            "openai": OpenAIConfig
        }
