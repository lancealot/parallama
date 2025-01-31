from typing import Dict, Any
import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .base import LLMGateway
from .config import OllamaConfig

class OllamaGateway(LLMGateway):
    """Ollama gateway implementation.
    
    This gateway provides native Ollama API compatibility, handling model discovery,
    request/response transformation, and authentication validation.
    """
    
    def __init__(self, config: OllamaConfig):
        """Initialize the Ollama gateway.
        
        Args:
            config: Ollama-specific gateway configuration
        """
        self.config = config
        self.base_url = config.get_endpoint_url()
        if not self.base_url:
            raise ValueError("Ollama gateway requires host configuration")
            
        # Initialize HTTP client with base URL
        self.client = httpx.AsyncClient(base_url=self.base_url)
        
    async def validate_auth(self, credentials: str) -> bool:
        """Validate authentication credentials.
        
        For Ollama gateway, this validates the API key and checks role permissions.
        
        Args:
            credentials: The authentication token or API key
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        # TODO: Implement authentication validation using the auth service
        # For now, return True for development
        return True
        
    async def transform_request(self, request: Request) -> Dict[str, Any]:
        """Transform incoming request to Ollama format.
        
        The Ollama gateway mostly passes through requests with minimal transformation
        since we're using the native API format.
        
        Args:
            request: The incoming FastAPI request
            
        Returns:
            Dict[str, Any]: The transformed request data
        """
        # Read request body
        body = await request.json()
        
        # Map model name if configured
        if "model" in body:
            body["model"] = self.config.get_model_mapping(body["model"])
            
        return body
        
    async def transform_response(self, response: Dict[str, Any]) -> Response:
        """Transform Ollama response to standardized format.
        
        Args:
            response: The raw response from Ollama
            
        Returns:
            Response: The transformed FastAPI response
        """
        # For now, pass through the response with minimal transformation
        return JSONResponse(content=response)
        
    async def get_status(self) -> Dict[str, Any]:
        """Get Ollama gateway status and available models.
        
        Fetches available models and gateway health information from Ollama.
        
        Returns:
            Dict[str, Any]: Status information including:
                - available models
                - gateway health
                - version information
        """
        try:
            # Fetch available models
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            models = await response.json()
            
            # Get version information
            version_response = await self.client.get("/api/version")
            version_response.raise_for_status()
            version = await version_response.json()
            
            return {
                "status": "healthy",
                "models": models,
                "version": version,
                "gateway_type": "ollama",
                "endpoint": self.base_url
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "gateway_type": "ollama",
                "endpoint": self.base_url
            }
            
    async def close(self):
        """Close the HTTP client connection."""
        await self.client.aclose()
