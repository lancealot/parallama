"""Test utilities and helper classes."""

from typing import Dict, Any
from unittest.mock import AsyncMock
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from parallama.gateway import LLMGateway
from parallama.gateway.config import GatewayConfig

class MockGateway(LLMGateway):
    """Mock gateway implementation for testing."""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.ollama_url = "http://localhost:11434"
        self._validate_auth_mock = AsyncMock(return_value=True)
        self._transform_request_mock = AsyncMock(return_value={"test": "data"})
        self._transform_response_mock = AsyncMock(return_value=JSONResponse(content={"status": "ok"}))
        self._handle_error_mock = AsyncMock(return_value=JSONResponse(content={"error": "test error"}, status_code=500))

    async def validate_auth(self, credentials: str) -> bool:
        return await self._validate_auth_mock(credentials)

    async def transform_request(self, request: Request) -> Dict[str, Any]:
        return await self._transform_request_mock(request)

    async def transform_response(self, response: Dict[str, Any]) -> Response:
        return await self._transform_response_mock(response)

    async def handle_error(self, error: Exception) -> Response:
        return await self._handle_error_mock(error)

    async def get_status(self):
        return {"status": "healthy"}

    async def close(self):
        pass
