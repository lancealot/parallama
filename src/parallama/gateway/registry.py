from typing import Dict, Type, Optional
from .base import LLMGateway

class GatewayRegistry:
    """Registry for managing LLM gateway implementations.
    
    This class provides a central registry for all gateway implementations,
    allowing them to be registered and retrieved by name. It uses a class-level
    dictionary to store gateway implementations, making them globally accessible.
    """
    
    _gateways: Dict[str, Type[LLMGateway]] = {}
    _instances: Dict[str, LLMGateway] = {}
    
    @classmethod
    def register(cls, name: str, gateway_class: Type[LLMGateway]) -> None:
        """Register a new gateway implementation.
        
        Args:
            name: Unique identifier for the gateway
            gateway_class: The gateway class to register
            
        Raises:
            ValueError: If a gateway with the given name is already registered
        """
        if name in cls._gateways:
            raise ValueError(f"Gateway '{name}' is already registered")
        cls._gateways[name] = gateway_class
    
    @classmethod
    def get_gateway_class(cls, name: str) -> Optional[Type[LLMGateway]]:
        """Get a registered gateway class by name.
        
        Args:
            name: The name of the gateway to retrieve
            
        Returns:
            Optional[Type[LLMGateway]]: The gateway class if found, None otherwise
        """
        return cls._gateways.get(name)
    
    @classmethod
    def get_gateway(cls, name: str) -> Optional[LLMGateway]:
        """Get or create a gateway instance by name.
        
        This method implements a singleton pattern for gateway instances,
        ensuring only one instance exists per gateway type.
        
        Args:
            name: The name of the gateway to retrieve
            
        Returns:
            Optional[LLMGateway]: The gateway instance if found, None otherwise
        """
        if name not in cls._instances:
            gateway_class = cls.get_gateway_class(name)
            if gateway_class:
                cls._instances[name] = gateway_class()
        return cls._instances.get(name)
    
    @classmethod
    def list_gateways(cls) -> Dict[str, Type[LLMGateway]]:
        """List all registered gateways.
        
        Returns:
            Dict[str, Type[LLMGateway]]: Dictionary of gateway names and their classes
        """
        return cls._gateways.copy()
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered gateways and instances.
        
        This is primarily useful for testing purposes.
        """
        cls._gateways.clear()
        cls._instances.clear()
