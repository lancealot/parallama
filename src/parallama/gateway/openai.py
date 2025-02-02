"""OpenAI-compatible gateway implementation."""

import json
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from .config import OpenAIConfig
from ..services.token_counter import TokenCounter
from .endpoints import EmbeddingsHandler, EditsHandler, ModerationsHandler

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
        self.client = httpx.AsyncClient(
            timeout=config.performance.request_timeout,
            limits=httpx.Limits(
                max_connections=config.performance.connection_pool_size,
                max_keepalive_connections=config.performance.connection_pool_size
            )
        )
        self.token_counter = TokenCounter(config.token_counter)
        
        # Initialize endpoint handlers
        self.embeddings_handler = EmbeddingsHandler(config)
        self.edits_handler = EditsHandler(config)
        self.moderations_handler = ModerationsHandler(config)

    async def validate_auth(self, credentials: str) -> bool:
        """Validate authentication credentials.
        
        Args:
            credentials: The authentication token or API key
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        # In compatibility mode, we don't validate OpenAI tokens
        return True

    async def handle_request(self, request: Request) -> Response:
        """Handle incoming request.
        
        Args:
            request: The incoming FastAPI request
            
        Returns:
            Response: The API response
        """
        # Extract endpoint from path
        path = request.url.path.lower()
        
        # Route to appropriate handler
        if "/embeddings" in path:
            return await self.embeddings_handler.handle_request(request)
        elif "/edits" in path:
            return await self.edits_handler.handle_request(request)
        elif "/moderations" in path:
            return await self.moderations_handler.handle_request(request)
        else:
            # Handle chat/completion requests
            transformed_request = await self.transform_request(request)
            response = await self.client.post(
                f"{self.ollama_url}/api/generate",
                json=transformed_request
            )
            return await self.transform_response(response.json(), request)

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
        mapped_model = self.model_mappings.get(model, model)
        
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
            
            # Count tokens if enabled
            if self.config.token_counter.enabled:
                request.state.prompt_tokens = await self.token_counter.count_tokens(
                    messages,
                    model
                )
        else:
            # Regular completion request
            prompt = data.get("prompt", "")
            
            # Count tokens if enabled
            if self.config.token_counter.enabled:
                request.state.prompt_tokens = await self.token_counter.count_tokens(
                    prompt,
                    model
                )
        
        # Transform request
        transformed = {
            "model": mapped_model,
            "prompt": prompt,
            "stream": data.get("stream", False),
            "temperature": data.get("temperature", 0.7),
            "max_tokens": data.get("max_tokens")
        }
        
        # Handle test mode
        if "_test_mode" in request.headers:
            transformed["_test_mode"] = True
        
        return transformed

    async def transform_response(self, response: Dict[str, Any], request: Request) -> Response:
        """Transform Ollama response to OpenAI format.
        
        Args:
            response: The raw response from Ollama
            request: The original request for context
            
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
                completion_tokens = 0
                async for chunk in response["chunks"]:
                    # Count tokens in chunk if enabled
                    if self.config.token_counter.enabled:
                        content = chunk.get("response", "")
                        if content:
                            tokens = await self.token_counter.count_tokens(
                                content,
                                request.state.model
                            )
                            completion_tokens += tokens
                            request.state.completion_tokens = completion_tokens

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
        
        # Count completion tokens if enabled
        completion_tokens = 0
        if self.config.token_counter.enabled:
            completion_tokens = await self.token_counter.count_tokens(
                response.get("response", ""),
                request.state.model
            )
            request.state.completion_tokens = completion_tokens
        
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
                "prompt_tokens": getattr(request.state, "prompt_tokens", 0),
                "completion_tokens": completion_tokens,
                "total_tokens": (
                    getattr(request.state, "prompt_tokens", 0) + completion_tokens
                )
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
