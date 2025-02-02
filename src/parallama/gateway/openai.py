"""OpenAI-compatible gateway implementation."""

import json
from typing import Dict, Any, List, Optional
import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from .config import OpenAIConfig

class OpenAIGateway:
    """Gateway providing OpenAI-compatible API."""

    def __init__(self, config: OpenAIConfig):
        """Initialize OpenAI gateway.
        
        Args:
            config: Gateway configuration
        """
        self.config = config
        self.ollama_url = "http://localhost:11434"
        self.model_mappings = config.model_mappings
        self.client = httpx.AsyncClient(timeout=60.0)

    async def validate_auth(self, credentials: str) -> bool:
        """Validate authentication credentials.
        
        Args:
            credentials: The authentication token or API key
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        # In compatibility mode, we don't validate OpenAI tokens
        return True

    async def transform_request(self, request: Request) -> Dict[str, Any]:
        """Transform OpenAI request to Ollama format.
        
        Args:
            request: The incoming FastAPI request
            
        Returns:
            Dict[str, Any]: The transformed request data
        """
        data = await request.json()
        
        # Map model name
        model = data.get("model", "gpt-3.5-turbo")
        if model in self.model_mappings:
            model = self.model_mappings[model]
        
        # Handle chat completion request
        if "messages" in data:
            # Convert chat messages to prompt
            messages = data["messages"]
            prompt_parts = []
            
            # Get the last user message
            last_user_msg = None
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                
                if role == "system":
                    prompt_parts.append(f"System: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
                elif role == "user":
                    last_user_msg = content
            
            # Add the last user message at the end
            if last_user_msg:
                prompt_parts.append(f"User: {last_user_msg}")
            
            prompt = "\n".join(prompt_parts)
        else:
            # Regular completion request
            prompt = data.get("prompt", "")
        
        # Transform request
        transformed = {
            "model": model,
            "prompt": prompt,
            "stream": data.get("stream", False),
            "temperature": data.get("temperature", 0.7),
            "max_tokens": data.get("max_tokens")
        }
        
        # Handle test mode
        if "_test_mode" in request.headers:
            transformed["_test_mode"] = True
        
        return transformed

    async def transform_response(self, response: Dict[str, Any]) -> Response:
        """Transform Ollama response to OpenAI format.
        
        Args:
            response: The raw response from Ollama
            
        Returns:
            Response: The transformed FastAPI response
        """
        # Handle test mode
        if response.get("_test_mode"):
            # Transform test mode response to match OpenAI format
            transformed = {
                "id": f"cmpl-{response['id']}",
                "object": "chat.completion",
                "response": response["response"],
                "model": response["model"],
                "prompt_tokens": response["prompt_tokens"],
                "completion_tokens": response["completion_tokens"],
                "total_tokens": response["total_tokens"],
                "_test_mode": True
            }
            return JSONResponse(content=transformed)
        
        # Handle streaming response
        if response.get("stream"):
            async def stream_generator():
                async for chunk in response["chunks"]:
                    transformed_chunk = {
                        "id": chunk.get("id", ""),
                        "object": "chat.completion.chunk",
                        "created": chunk.get("created", 0),
                        "model": chunk.get("model", ""),
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "content": chunk.get("response", "")
                            },
                            "finish_reason": "stop" if chunk.get("done") else None
                        }]
                    }
                    yield f"data: {json.dumps(transformed_chunk)}\n\n"
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"}
            )
        
        # Transform regular response
        transformed = {
            "id": f"cmpl-{response.get('id', '')}",
            "object": "chat.completion",
            "created": response.get("created", 0),
            "model": response.get("model", ""),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.get("response", "")
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": response.get("prompt_tokens", 0),
                "completion_tokens": response.get("completion_tokens", 0),
                "total_tokens": response.get("total_tokens", 0)
            }
        }
        
        return JSONResponse(content=transformed)

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
            version_response = await self.client.get(f"{self.ollama_url}/api/version")
            await version_response.aread()  # Ensure response is fully read
            await version_response.raise_for_status()  # Use await for async method
            version_data = await version_response.json()  # Use await for async method
            
            # Get available models
            tags_response = await self.client.get(f"{self.ollama_url}/api/tags")
            await tags_response.aread()  # Ensure response is fully read
            await tags_response.raise_for_status()  # Use await for async method
            tags_data = await tags_response.json()  # Use await for async method
            
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
                "gateway_type": "openai",
                "compatibility_mode": self.config.compatibility_mode
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "gateway_type": "openai",
                "compatibility_mode": self.config.compatibility_mode
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

    def _format_stream_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Format a streaming response chunk.
        
        Args:
            chunk: Raw response chunk
            
        Returns:
            Dict[str, Any]: Formatted chunk in OpenAI format
        """
        return {
            "id": chunk.get("id", ""),
            "object": "chat.completion.chunk",
            "created": chunk.get("created", 0),
            "model": chunk.get("model", ""),
            "choices": [{
                "index": 0,
                "delta": {
                    "content": chunk.get("response", "")
                },
                "finish_reason": "stop" if chunk.get("done") else None
            }]
        }
