from abc import ABC, abstractmethod
from typing import Dict, Any
from fastapi import Request, Response

class LLMGateway(ABC):
    """Base class for LLM gateway implementations.
    
    This abstract class defines the interface that all gateway implementations
    must follow. Each gateway type (Ollama, OpenAI, etc.) will implement
    these methods according to their specific requirements.
    """
    
    @abstractmethod
    async def validate_auth(self, credentials: str) -> bool:
        """Validate gateway-specific authentication credentials.
        
        Args:
            credentials: The authentication credentials to validate
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def transform_request(self, request: Request) -> Dict[str, Any]:
        """Transform incoming request to gateway-specific format.
        
        Args:
            request: The incoming FastAPI request
            
        Returns:
            Dict[str, Any]: The transformed request data
        """
        pass
    
    @abstractmethod
    async def transform_response(self, response: Dict[str, Any]) -> Response:
        """Transform gateway response to standardized format.
        
        Args:
            response: The raw response from the LLM service
            
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
                - additional gateway-specific metadata
        """
        pass
