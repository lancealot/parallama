"""Tests for the OpenAI gateway integration."""

import json
import pytest
import httpx
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from parallama.gateway import GatewayRegistry, OpenAIGateway, GatewayType
from parallama.gateway.config import OpenAIConfig
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
    
    # Create and register OpenAI gateway
    config = OpenAIConfig(
        name="test-openai",
        base_path="/openai/v1",
        enabled=True,
        compatibility_mode=True,
        model_mappings={
            "gpt-3.5-turbo": "llama2",
            "gpt-4": "llama2:70b"
        }
    )
    gateway = OpenAIGateway(config)
    
    # Mock validate_auth to always return True
    gateway.validate_auth = AsyncMock(return_value=True)
    
    # Register the gateway
    GatewayRegistry._instances[GatewayType.OPENAI] = gateway
    GatewayRegistry.register(GatewayType.OPENAI, OpenAIGateway)
    
    yield gateway
    
    # Cleanup
    GatewayRegistry.clear()

@pytest.mark.asyncio
async def test_openai_gateway_discovery(test_client):
    """Test the gateway discovery endpoint with OpenAI gateway."""
    response = test_client.get("/gateway/discovery")
    assert response.status_code == 200
    
    data = response.json()
    assert "gateways" in data
    assert "supported_types" in data
    assert GatewayType.OPENAI in data["supported_types"]
    assert data["gateways"].get("openai") is not None

@pytest.mark.asyncio
async def test_openai_chat_completion(test_client, setup_gateway):
    """Test chat completion through the OpenAI gateway."""
    # Mock the Ollama service response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={
        "model": "llama2",
        "response": "Hello! How can I help you today?",
        "done": True
    })
    
    # Test request data in OpenAI format
    request_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hi! How are you?"}
        ],
        "temperature": 0.7,
        "stream": False
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        response = test_client.post(
            "/gateway/openai/chat/completions",
            json=request_data,
            headers={
                "Authorization": "Bearer test-token",
                "_test_mode": "true"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "chat.completion"
        assert len(data["choices"]) == 1
        assert data["choices"][0]["message"]["content"] == "Hello! How can I help you today?"

@pytest.mark.asyncio
async def test_openai_streaming_chat(test_client, setup_gateway):
    """Test streaming chat completion through the OpenAI gateway."""
    # Mock streaming response from Ollama
    async def mock_aiter_lines():
        responses = [
            '{"model": "llama2", "response": "Hello", "done": false}',
            '{"model": "llama2", "response": " there", "done": false}',
            '{"model": "llama2", "response": "!", "done": true}'
        ]
        for line in responses:
            yield line.encode()
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines
    mock_response.aiter_raw = mock_aiter_lines
    mock_response.raise_for_status = AsyncMock()
    
    # Test request data
    request_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Say hi!"}
        ],
        "stream": True
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        response = test_client.post(
            "/gateway/openai/chat/completions",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        
        # Read streaming response
        chunks = list(response.iter_lines())
        assert len(chunks) == 3
        for chunk in chunks:
            assert chunk.startswith("data: ")
            data = json.loads(chunk.replace("data: ", ""))
            assert data["object"] == "chat.completion.chunk"
            assert "content" in data["choices"][0]["delta"]

@pytest.mark.asyncio
async def test_openai_gateway_error_handling(test_client, setup_gateway):
    """Test error handling in the OpenAI gateway."""
    request_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ]
    }
    
    # Test timeout error
    with patch("httpx.AsyncClient.post", side_effect=httpx.ReadTimeout("Request timed out")):
        response = test_client.post(
            "/gateway/openai/chat/completions",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 504
        assert "Request to LLM service timed out" in response.json()["detail"]
    
    # Test connection error
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection failed")):
        response = test_client.post(
            "/gateway/openai/chat/completions",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 502
        assert "Failed to connect to LLM service" in response.json()["detail"]
    
    # Test LLM service error
    mock_error_response = AsyncMock()
    mock_error_response.status_code = 400
    mock_error_response.json = AsyncMock(return_value={"error": "Invalid model specified"})
    mock_error_response.raise_for_status = AsyncMock(side_effect=httpx.HTTPStatusError(
        "400 Bad Request",
        request=AsyncMock(),
        response=mock_error_response
    ))
    
    with patch("httpx.AsyncClient.post", return_value=mock_error_response):
        response = test_client.post(
            "/gateway/openai/chat/completions",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 400
        assert "Invalid model specified" in response.json()["detail"]

@pytest.mark.asyncio
async def test_openai_gateway_auth_validation(test_client, setup_gateway):
    """Test authentication validation in the OpenAI gateway."""
    request_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ]
    }
    
    # Mock validate_auth to return False for invalid tokens
    setup_gateway.validate_auth = AsyncMock(side_effect=lambda token: token == "Bearer test-token")
    
    # Test missing auth header
    response = test_client.post(
        "/gateway/openai/chat/completions",
        json=request_data
    )
    assert response.status_code == 401
    assert "Missing authentication credentials" in response.json()["detail"]
    
    # Test invalid auth token
    response = test_client.post(
        "/gateway/openai/chat/completions",
        json=request_data,
        headers={"Authorization": "Invalid-Token"}
    )
    assert response.status_code == 401
    assert "Invalid authentication credentials" in response.json()["detail"]

@pytest.mark.asyncio
async def test_openai_model_mapping(test_client, setup_gateway):
    """Test model mapping in the OpenAI gateway."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={
        "model": "llama2:70b",
        "response": "Test response",
        "done": True
    })
    
    # Test request with GPT-4 model (should map to llama2:70b)
    request_data = {
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ]
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        response = test_client.post(
            "/gateway/openai/chat/completions",
            json=request_data,
            headers={
                "Authorization": "Bearer test-token",
                "_test_mode": "true"
            }
        )
        
        assert response.status_code == 200
        # Verify the model was mapped correctly in the request to Ollama
        called_request = mock_post.call_args[1]["json"]
        assert called_request["model"] == "llama2:70b"
