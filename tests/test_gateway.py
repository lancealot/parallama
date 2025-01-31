import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient
from typing import Dict, Any

from parallama.gateway import (
    LLMGateway,
    GatewayRegistry,
    GatewayType,
    GatewayConfig,
    OllamaConfig,
    gateway_router,
)

# Mock Gateway Implementation
class MockGateway(LLMGateway):
    """Mock gateway implementation for testing."""
    
    def __init__(self):
        self._test_mode = True
        self.base_url = "http://mock-service"
    
    async def validate_auth(self, credentials: str) -> bool:
        return credentials == "valid-token"
    
    async def transform_request(self, request: Request) -> Dict[str, Any]:
        return {
            "mock": "request",
            "path": request.url.path,
            "method": request.method,
            "response": {"status": "ok"}
        }
    
    async def transform_response(self, response: Dict[str, Any]) -> Response:
        from fastapi.responses import JSONResponse
        return JSONResponse(content=response)
    
    async def get_status(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "models": ["mock-model-1", "mock-model-2"],
            "version": "1.0.0"
        }

@pytest.fixture
def mock_gateway():
    """Fixture to create and register a mock gateway."""
    GatewayRegistry.clear()  # Clear any existing registrations
    gateway = MockGateway()
    GatewayRegistry.register("mock", MockGateway)
    return gateway

@pytest.fixture
def client():
    """Fixture to create a FastAPI test client."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(gateway_router)
    return TestClient(app)

def test_gateway_registration(mock_gateway):
    """Test gateway registration and retrieval."""
    # Test registration
    assert "mock" in GatewayRegistry.list_gateways()
    
    # Test gateway class retrieval
    gateway_class = GatewayRegistry.get_gateway_class("mock")
    assert gateway_class == MockGateway
    
    # Test gateway instance retrieval
    gateway = GatewayRegistry.get_gateway("mock")
    assert isinstance(gateway, MockGateway)
    
    # Test duplicate registration
    with pytest.raises(ValueError):
        GatewayRegistry.register("mock", MockGateway)

def test_gateway_config():
    """Test gateway configuration validation."""
    # Test basic config
    config = GatewayConfig(
        name="test",
        type=GatewayType.OLLAMA,
        base_path="/test"
    )
    assert config.base_path == "/test"
    assert config.enabled is True
    
    # Test Ollama config defaults
    ollama_config = OllamaConfig(name="ollama")
    assert ollama_config.base_path == "/ollama/v1"
    assert ollama_config.host == "http://localhost"
    assert ollama_config.port == 11434
    
    # Test endpoint URL construction
    assert ollama_config.get_endpoint_url() == "http://localhost:11434/ollama/v1"

@pytest.mark.asyncio
async def test_gateway_discovery(client, mock_gateway):
    """Test gateway discovery endpoint."""
    response = client.get("/gateway/discovery")
    assert response.status_code == 200
    
    data = response.json()
    assert "gateways" in data
    assert "mock" in data["gateways"]
    assert data["gateways"]["mock"]["status"] == "available"
    
    # Verify gateway info
    gateway_info = data["gateways"]["mock"]["info"]
    assert gateway_info["status"] == "healthy"
    assert "mock-model-1" in gateway_info["models"]

@pytest.mark.asyncio
async def test_gateway_routing(client, mock_gateway):
    """Test request routing through gateway."""
    # Test without auth header
    response = client.post("/gateway/mock/test")
    assert response.status_code == 401
    
    # Test with invalid auth
    response = client.post(
        "/gateway/mock/test",
        headers={"Authorization": "invalid-token"}
    )
    assert response.status_code == 401
    
    # Test with valid auth
    response = client.post(
        "/gateway/mock/test",
        headers={"Authorization": "valid-token"}
    )
    assert response.status_code == 200
    
    # Test non-existent gateway
    response = client.post(
        "/gateway/nonexistent/test",
        headers={"Authorization": "valid-token"}
    )
    assert response.status_code == 404

def test_gateway_registry_clear(mock_gateway):
    """Test clearing the gateway registry."""
    assert len(GatewayRegistry.list_gateways()) > 0
    GatewayRegistry.clear()
    assert len(GatewayRegistry.list_gateways()) == 0
