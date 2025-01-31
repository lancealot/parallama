import pytest
import httpx
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from parallama.gateway import GatewayRegistry, OllamaGateway, GatewayType
from parallama.gateway.config import OllamaConfig
from parallama.gateway.router import router as gateway_router

# Create test FastAPI app
app = FastAPI()
app.include_router(gateway_router)

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)

@pytest.fixture(autouse=True)
def setup_gateway():
    """Set up a test gateway in the registry."""
    # Clear any existing gateways
    GatewayRegistry.clear()
    
    # Create and register Ollama gateway
    config = OllamaConfig(
        name="test-ollama",
        host="http://localhost",
        port=11434,
        base_path="/ollama/v1",
        enabled=True
    )
    gateway = OllamaGateway(config)
    
    # Mock validate_auth to always return True
    gateway.validate_auth = AsyncMock(return_value=True)
    
    # Mock transform_response to return JSON response
    async def mock_transform_response(response_data):
        return JSONResponse(content=response_data)
    gateway.transform_response = mock_transform_response
    
    # Register the gateway
    GatewayRegistry._instances[GatewayType.OLLAMA] = gateway
    GatewayRegistry.register(GatewayType.OLLAMA, OllamaGateway)
    
    yield gateway
    
    # Cleanup
    GatewayRegistry.clear()

@pytest.mark.asyncio
async def test_gateway_discovery(test_client):
    """Test the gateway discovery endpoint."""
    response = test_client.get("/gateway/discovery")
    assert response.status_code == 200
    
    data = response.json()
    assert "gateways" in data
    assert "supported_types" in data
    assert GatewayType.OLLAMA in data["supported_types"]

@pytest.mark.asyncio
async def test_ollama_gateway_request(test_client, setup_gateway):
    """Test making a request through the Ollama gateway."""
    # Mock the LLM service response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={
        "model": "llama2",
        "response": "Test response",
        "done": True
    })
    
    # Test request data
    request_data = {
        "model": "llama2",
        "prompt": "Hello, world!",
        "stream": False
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        response = test_client.post(
            "/gateway/ollama/generate",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "llama2"
        assert "response" in data

@pytest.mark.asyncio
async def test_ollama_gateway_streaming(test_client, setup_gateway):
    """Test streaming response through the Ollama gateway."""
    # Mock streaming response
    async def mock_aiter_lines():
        responses = [
            '{"model": "llama2", "response": "Hello", "done": false}\n',
            '{"model": "llama2", "response": " world", "done": false}\n',
            '{"model": "llama2", "response": "!", "done": true}\n'
        ]
        for line in responses:
            yield bytes(line, "utf-8")
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines
    mock_response.aiter_raw = mock_aiter_lines  # FastAPI uses aiter_raw for streaming
    
    # Test request data
    request_data = {
        "model": "llama2",
        "prompt": "Hello, world!",
        "stream": True
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        response = test_client.post(
            "/gateway/ollama/generate",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        
        # Read streaming response
        chunks = list(response.iter_lines())
        assert len(chunks) == 3
        assert all(chunk.strip() for chunk in chunks)

@pytest.mark.asyncio
async def test_ollama_gateway_error_handling(test_client, setup_gateway):
    """Test error handling in the Ollama gateway."""
    # Test request data
    request_data = {
        "model": "llama2",
        "prompt": "Hello, world!"
    }
    
    # Test timeout error
    with patch("httpx.AsyncClient.post", side_effect=httpx.ReadTimeout("Request timed out")):
        response = test_client.post(
            "/gateway/ollama/generate",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 504
        assert "Request to LLM service timed out" in response.json()["detail"]
    
    # Test connection error
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection failed")):
        response = test_client.post(
            "/gateway/ollama/generate",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 502
        assert "Failed to connect to LLM service" in response.json()["detail"]
    
    # Test LLM service error
    mock_error_response = AsyncMock()
    mock_error_response.status_code = 400
    mock_error_response.json = AsyncMock(return_value={"error": "Invalid model specified"})
    
    with patch("httpx.AsyncClient.post", return_value=mock_error_response):
        response = test_client.post(
            "/gateway/ollama/generate",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 400
        assert "Invalid model specified" in response.json()["detail"]

@pytest.mark.asyncio
async def test_ollama_gateway_auth_validation(test_client, setup_gateway):
    """Test authentication validation in the Ollama gateway."""
    request_data = {
        "model": "llama2",
        "prompt": "Hello, world!"
    }
    
    # Mock validate_auth to return False for invalid tokens
    setup_gateway.validate_auth = AsyncMock(side_effect=lambda token: token == "Bearer test-token")
    
    # Test missing auth header
    response = test_client.post(
        "/gateway/ollama/generate",
        json=request_data
    )
    assert response.status_code == 401
    assert "Missing authentication credentials" in response.json()["detail"]
    
    # Test invalid auth token
    response = test_client.post(
        "/gateway/ollama/generate",
        json=request_data,
        headers={"Authorization": "Invalid-Token"}
    )
    assert response.status_code == 401
    assert "Invalid authentication credentials" in response.json()["detail"]
