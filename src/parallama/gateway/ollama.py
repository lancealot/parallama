"""Ollama gateway implementation."""

import json
from typing import Dict, Any, Optional
import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from .config import OllamaConfig

class OllamaGateway:
    """Gateway for Ollama LLM service."""

    def __init__(self, config: OllamaConfig):
        """Initialize Ollama gateway.
        
        Args:
            config: Gateway configuration
        """
        self.config = config
        self.ollama_url = f"{config.host}:{config.port}/api".rstrip("/")
        print(f"DEBUG: Initialized OllamaGateway with URL: {self.ollama_url}")
        self.model_mappings = {}  # Ollama doesn't need model mappings
        self.client = httpx.AsyncClient(timeout=60.0)

    async def validate_auth(self, credentials: str) -> bool:
        """Validate authentication credentials.
        
        Args:
            credentials: The authentication token or API key
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        # Ollama doesn't require authentication
        return True

    async def transform_request(self, request: Request) -> Dict[str, Any]:
        """Transform incoming request to Ollama format.
        
        Args:
            request: The incoming FastAPI request
            
        Returns:
            Dict[str, Any]: The transformed request data
        """
        # Handle GET requests differently
        if request.method == "GET":
            return {}
            
        # For POST/PUT requests, transform the body
        data = await request.json()
        
        if request.url.path.endswith("/generate"):
            # Transform generate request format
            transformed = {
                "model": data.get("model", "llama2"),
                "prompt": data.get("prompt", ""),
                "stream": data.get("stream", False),
                "temperature": data.get("temperature", 0.7),
                "max_tokens": data.get("max_tokens")
            }
        else:
            # For other endpoints, pass through the data
            transformed = data
        
        # Handle test mode
        if "_test_mode" in request.headers:
            transformed["_test_mode"] = True
        
        return transformed

    async def transform_response(self, response: Dict[str, Any]) -> Response:
        """Transform Ollama response to API format.
        
        Args:
            response: The raw response from Ollama
            
        Returns:
            Response: The transformed FastAPI response
        """
        # Handle test mode
        if response.get("_test_mode"):
            return JSONResponse(content=response)
        
        # Handle streaming response
        if response.get("stream"):
            async def stream_generator():
                async for chunk in response["chunks"]:
                    yield f"data: {json.dumps(chunk)}\n\n"
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"}
            )
        
        # For /tags endpoint, return models list
        if "models" in response:
            return JSONResponse(content={
                "models": [
                    {
                        "id": model["name"],
                        "object": "model",
                        "owned_by": "ollama",
                        "permission": [],
                        "details": model.get("details", {})
                    }
                    for model in response["models"]
                ]
            })
        
        # For /generate endpoint
        if "response" in response:
            transformed = {
                "id": response.get("id", ""),
                "object": "completion",
                "created": response.get("created", 0),
                "model": response.get("model", ""),
                "choices": [{
                    "text": response.get("response", ""),
                    "index": 0,
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": response.get("prompt_tokens", 0),
                    "completion_tokens": response.get("completion_tokens", 0),
                    "total_tokens": response.get("total_tokens", 0)
                }
            }
            return JSONResponse(content=transformed)
        
        # For other endpoints, pass through the response
        return JSONResponse(content=response)

    async def get_status(self) -> Dict[str, Any]:
        """Get gateway status and available models.
        
        Returns:
            Dict[str, Any]: Status information including:
                - available models
                - gateway health
                - version information
        """
        try:
            # Get version info
            version_response = await self.client.get(f"{self.ollama_url}/version")
            version_response.raise_for_status()
            version_data = version_response.json()
            
            # Get available models
            tags_response = await self.client.get(f"{self.ollama_url}/tags")
            tags_response.raise_for_status()
            tags_data = tags_response.json()
            
            return {
                "status": "healthy",
                "version": version_data.get("version"),
                "models": [
                    {
                        "id": tag["name"],
                        "object": "model",
                        "owned_by": "ollama",
                        "permission": []
                    }
                    for tag in tags_data
                ],
                "gateway_type": "ollama"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "gateway_type": "ollama"
            }

    async def close(self) -> None:
        """Close any open connections."""
        await self.client.aclose()

    async def handle_error(self, error: Exception) -> Response:
        """Handle errors and return appropriate responses.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Response: An error response with appropriate status code
        """
        if isinstance(error, httpx.ReadTimeout):
            return JSONResponse(
                status_code=504,
                content={"detail": "Request to LLM service timed out"}
            )
        elif isinstance(error, httpx.ConnectError):
            return JSONResponse(
                status_code=502,
                content={"detail": f"Failed to connect to LLM service: {str(error)}"}
            )
        elif isinstance(error, httpx.HTTPStatusError):
            return JSONResponse(
                status_code=error.response.status_code,
                content={"detail": error.response.json().get("error", str(error))}
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"detail": str(error)}
            )
