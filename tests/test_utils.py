"""Test utilities and helper classes."""

from typing import Dict, Any, List
from unittest.mock import AsyncMock
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import numpy as np

from parallama.gateway import LLMGateway
from parallama.gateway.config import GatewayConfig
from parallama.gateway.endpoints import (
    EmbeddingsHandler,
    EditsHandler,
    ModerationsHandler
)

class MockEmbeddingsHandler(EmbeddingsHandler):
    """Mock embeddings handler for testing."""

    def __init__(self, config: GatewayConfig):
        super().__init__(config)
        self._handle_request_mock = AsyncMock(return_value=JSONResponse(
            content={
                "object": "list",
                "data": [{
                    "object": "embedding",
                    "embedding": [0.1] * 1536,
                    "index": 0
                }],
                "model": "text-embedding-ada-002",
                "usage": {
                    "prompt_tokens": 5,
                    "total_tokens": 5
                }
            }
        ))

    async def handle_request(self, request: Request) -> Response:
        return await self._handle_request_mock(request)

class MockEditsHandler(EditsHandler):
    """Mock edits handler for testing."""

    def __init__(self, config: GatewayConfig):
        super().__init__(config)
        self._handle_request_mock = AsyncMock(return_value=JSONResponse(
            content={
                "object": "edit",
                "created": 1234567890,
                "choices": [{
                    "text": "Edited text",
                    "index": 0
                }],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 3,
                    "total_tokens": 8
                }
            }
        ))

    async def handle_request(self, request: Request) -> Response:
        return await self._handle_request_mock(request)

class MockModerationsHandler(ModerationsHandler):
    """Mock moderations handler for testing."""

    def __init__(self, config: GatewayConfig):
        super().__init__(config)
        self._handle_request_mock = AsyncMock(return_value=JSONResponse(
            content={
                "id": "modr-1234",
                "model": "text-moderation-latest",
                "results": [{
                    "flagged": False,
                    "categories": {
                        "hate": False,
                        "hate/threatening": False,
                        "self-harm": False,
                        "sexual": False,
                        "sexual/minors": False,
                        "violence": False,
                        "violence/graphic": False
                    },
                    "category_scores": {
                        "hate": 0.0,
                        "hate/threatening": 0.0,
                        "self-harm": 0.0,
                        "sexual": 0.0,
                        "sexual/minors": 0.0,
                        "violence": 0.0,
                        "violence/graphic": 0.0
                    }
                }],
                "usage": {
                    "prompt_tokens": 5,
                    "total_tokens": 5
                }
            }
        ))

    async def handle_request(self, request: Request) -> Response:
        return await self._handle_request_mock(request)

class MockGateway(LLMGateway):
    """Mock gateway implementation for testing."""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.ollama_url = "http://localhost:11434"
        self._validate_auth_mock = AsyncMock(return_value=True)
        self._transform_request_mock = AsyncMock(return_value={"test": "data"})
        self._transform_response_mock = AsyncMock(return_value=JSONResponse(content={"status": "ok"}))
        self._handle_error_mock = AsyncMock(return_value=JSONResponse(content={"error": "test error"}, status_code=500))
        
        # Initialize mock endpoint handlers
        self.embeddings_handler = MockEmbeddingsHandler(config)
        self.edits_handler = MockEditsHandler(config)
        self.moderations_handler = MockModerationsHandler(config)

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
