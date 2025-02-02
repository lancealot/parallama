"""Tests for the gateway router."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.testclient import TestClient
import httpx

from parallama.gateway import LLMGateway, GatewayRegistry, GatewayType
from parallama.gateway.router import router as gateway_router

class MockGateway(LLMGateway):
    """Mock gateway for testing."""
    
    def __init__(self, name="test", base_path="/test"):
        self.name = name
        self.base_path = base_path
        self.ollama_url = "http://localhost:11434"
        self._validate_auth_mock = AsyncMock(side_effect=lambda token: token == "valid-token")
        self._transform_request_mock = AsyncMock(return_value={"test": "data"})
        self._transform_response_mock = AsyncMock(return_value={"status": "ok"})
        self._handle_error_mock = AsyncMock()

    async def validate_auth(self, credentials: str) -> bool:
        return await self._validate_auth_mock(credentials)

    async def transform_request(self, request: Request) -> dict:
        return await self._transform_request_mock(request)

    async def transform_response(self, response: dict) -> dict:
        return await self._transform_response_mock(response)

    async def handle_error(self, error: Exception) -> dict:
        return await self._handle_error_mock(error)

    async def get_status(self):
        return {"status": "healthy"}

    async def close(self):
        pass

class FailingGateway(MockGateway):
    """Mock gateway that fails auth."""
    
    def __init__(self):
        super().__init__(name="failing", base_path="/failing")
        self._validate_auth_mock = AsyncMock(return_value=False)

class WorkingGateway(MockGateway):
    """Mock gateway that works."""
    
    def __init__(self):
        super().__init__(name="working", base_path="/working")

@pytest.fixture
def setup_gateways():
    """Set up test gateways."""
    GatewayRegistry.clear()
    GatewayRegistry.register("working", WorkingGateway)
    GatewayRegistry.register("failing", FailingGateway)
    GatewayRegistry._instances = {
        "working": WorkingGateway(),
        "failing": FailingGateway()
    }
    yield
    GatewayRegistry.clear()

@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(gateway_router)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)

def test_discovery_endpoint(client, setup_gateways):
    """Test gateway discovery endpoint."""
    response = client.get("/gateway/discovery")
    assert response.status_code == 200
    
    data = response.json()
    assert "gateways" in data
    assert "working" in data["gateways"]
    assert "failing" in data["gateways"]
    assert data["gateways"]["working"]["status"] == "available"

@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
def test_gateway_methods(client, setup_gateways, method):
    """Test different HTTP methods through gateway."""
    headers = {
        "Authorization": "valid-token",
        "Content-Type": "application/json",
        "_test_mode": "true"
    }
    data = {"test": "data"}

    response = client.request(
        method=method,
        url="/gateway/working/test",
        headers=headers,
        json=data
    )
    assert response.status_code == 200

def test_gateway_auth_validation(client, setup_gateways):
    """Test authentication validation scenarios."""
    # Test missing auth header
    response = client.post(
        "/gateway/working/test",
        headers={"Content-Type": "application/json"},
        json={"test": "data"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authentication credentials"

    # Test invalid auth
    response = client.post(
        "/gateway/failing/test",
        headers={
            "Authorization": "invalid-token",
            "Content-Type": "application/json"
        },
        json={"test": "data"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"

    # Test valid auth
    response = client.post(
        "/gateway/working/test",
        headers={
            "Authorization": "valid-token",
            "Content-Type": "application/json",
            "_test_mode": "true"
        },
        json={"test": "data"}
    )
    assert response.status_code == 200

def test_gateway_not_found(client, setup_gateways):
    """Test handling of non-existent gateway."""
    response = client.post(
        "/gateway/nonexistent/test",
        headers={"Authorization": "valid-token"},
        json={"test": "data"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_gateway_error_handling(client, setup_gateways):
    """Test error handling in gateway."""
    gateway = GatewayRegistry._instances["working"]
    gateway._handle_error_mock.return_value = JSONResponse(
        content={"detail": "Test error"},
        status_code=500
    )
    gateway._transform_request_mock.side_effect = Exception("Test error")

    response = client.post(
        "/gateway/working/test",
        headers={"Authorization": "valid-token"},
        json={"test": "data"}
    )
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]

def test_path_parameters(client, setup_gateways):
    """Test handling of path parameters in gateway routes."""
    response = client.post(
        "/gateway/working/models/test-model/generate",
        headers={
            "Authorization": "valid-token",
            "Content-Type": "application/json",
            "_test_mode": "true"
        },
        json={"prompt": "test"}
    )
    assert response.status_code == 200

def test_embeddings_endpoint(client, setup_gateways):
    """Test embeddings endpoint routing."""
    response = client.post(
        "/gateway/working/embeddings",
        headers={
            "Authorization": "valid-token",
            "Content-Type": "application/json",
            "_test_mode": "true"
        },
        json={
            "input": "test text",
            "model": "text-embedding-ada-002"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) == 1
    assert len(data["data"][0]["embedding"]) == 1536

def test_edits_endpoint(client, setup_gateways):
    """Test edits endpoint routing."""
    response = client.post(
        "/gateway/working/edits",
        headers={
            "Authorization": "valid-token",
            "Content-Type": "application/json",
            "_test_mode": "true"
        },
        json={
            "input": "teh cat",
            "instruction": "Fix spelling",
            "model": "text-davinci-edit-001"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "edit"
    assert len(data["choices"]) == 1
    assert "text" in data["choices"][0]

def test_moderations_endpoint(client, setup_gateways):
    """Test moderations endpoint routing."""
    response = client.post(
        "/gateway/working/moderations",
        headers={
            "Authorization": "valid-token",
            "Content-Type": "application/json",
            "_test_mode": "true"
        },
        json={
            "input": "test text",
            "model": "text-moderation-latest"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "text-moderation-latest"
    assert len(data["results"]) == 1
    assert "flagged" in data["results"][0]
    assert "categories" in data["results"][0]
    assert "category_scores" in data["results"][0]

def test_endpoint_disabled(client, setup_gateways):
    """Test behavior when endpoint is disabled."""
    gateway = GatewayRegistry._instances["working"]
    gateway.config.endpoints.embeddings = False
    
    response = client.post(
        "/gateway/working/embeddings",
        headers={
            "Authorization": "valid-token",
            "Content-Type": "application/json"
        },
        json={"input": "test"}
    )
    assert response.status_code == 404
    assert "not enabled" in response.json()["detail"].lower()

def test_streaming_response(client, setup_gateways):
    """Test handling of streaming responses."""
    gateway = GatewayRegistry._instances["working"]
    gateway._transform_request_mock.return_value = {"stream": True}
    
    chunks = ["data: chunk1\n\n", "data: chunk2\n\n"]
    
    gateway._transform_response_mock.return_value = StreamingResponse(
        content=iter(chunks),
        media_type="text/event-stream"
    )

    response = client.post(
        "/gateway/working/stream",
        headers={
            "Authorization": "valid-token",
            "Content-Type": "application/json",
            "_test_mode": "true"
        },
        json={"stream": True}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

def test_error_response_format(client, setup_gateways):
    """Test error response formatting."""
    gateway = GatewayRegistry._instances["working"]
    gateway._transform_request_mock.side_effect = HTTPException(
        status_code=400,
        detail="Invalid request"
    )

    response = client.post(
        "/gateway/working/test",
        headers={"Authorization": "valid-token"},
        json={"test": "data"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid request"
