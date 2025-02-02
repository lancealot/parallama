"""Tests for the OpenAI gateway."""

import pytest
from unittest.mock import AsyncMock, patch

from parallama.gateway.config import OpenAIConfig
from parallama.gateway.openai import OpenAIGateway

@pytest.fixture
def openai_config():
    """Create a test OpenAI gateway configuration."""
    return OpenAIConfig(
        name="test-openai",
        base_path="/openai/v1",
        enabled=True,
        compatibility_mode=True,
        model_mappings={
            "gpt-3.5-turbo": "llama2",
            "gpt-4": "llama2:70b"
        }
    )

@pytest.fixture
async def openai_gateway(openai_config):
    """Create a test OpenAI gateway instance."""
    gateway = OpenAIGateway(openai_config)
    yield gateway
    await gateway.close()

@pytest.mark.asyncio
async def test_gateway_initialization(openai_config):
    """Test gateway initialization with valid config."""
    gateway = OpenAIGateway(openai_config)
    assert gateway.ollama_url == "http://localhost:11434"
    assert gateway.model_mappings == {
        "gpt-3.5-turbo": "llama2",
        "gpt-4": "llama2:70b"
    }
    await gateway.close()

@pytest.mark.asyncio
async def test_transform_chat_completion_request(openai_gateway):
    """Test chat completion request transformation."""
    mock_request = AsyncMock()
    mock_request.url.path = "/openai/v1/chat/completions"
    mock_request.json.return_value = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ],
        "temperature": 0.8,
        "stream": False
    }
    
    result = await openai_gateway.transform_request(mock_request)
    assert result == {
        "model": "llama2",
        "prompt": "System: You are a helpful assistant.\nAssistant: Hi there!\nUser: How are you?",
        "stream": False,
        "temperature": 0.8,
        "max_tokens": None
    }

@pytest.mark.asyncio
async def test_transform_completion_request(openai_gateway):
    """Test completion request transformation."""
    mock_request = AsyncMock()
    mock_request.url.path = "/openai/v1/completions"
    mock_request.json.return_value = {
        "model": "gpt-4",
        "prompt": "Translate 'hello' to French",
        "temperature": 0.5,
        "max_tokens": 100
    }
    
    result = await openai_gateway.transform_request(mock_request)
    assert result == {
        "model": "llama2:70b",
        "prompt": "Translate 'hello' to French",
        "stream": False,
        "temperature": 0.5,
        "max_tokens": 100
    }

@pytest.mark.asyncio
async def test_transform_response(openai_gateway):
    """Test response transformation."""
    mock_response = {
        "id": "test-123",
        "response": "Bonjour!",
        "model": "llama2",
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "_test_mode": True
    }
    
    result = await openai_gateway.transform_response(mock_response)
    assert result.status_code == 200
    
    response_data = result.body.decode()
    assert "cmpl-" in response_data
    assert "chat.completion" in response_data
    assert "Bonjour!" in response_data
    assert "15" in response_data

@pytest.mark.asyncio
async def test_transform_streaming_response(openai_gateway):
    """Test streaming response transformation."""
    mock_response = {
        "stream": True,
        "chunks": [
            {"id": "1", "response": "Hello", "model": "llama2", "done": False},
            {"id": "2", "response": " world", "model": "llama2", "done": True}
        ]
    }
    
    result = await openai_gateway.transform_response(mock_response)
    assert result.media_type == "text/event-stream"
    
    # Test the first chunk format
    chunk = openai_gateway._format_stream_chunk(mock_response["chunks"][0])
    assert chunk["object"] == "chat.completion.chunk"
    assert chunk["choices"][0]["delta"]["content"] == "Hello"
    assert chunk["choices"][0]["finish_reason"] is None

    # Test the last chunk format
    chunk = openai_gateway._format_stream_chunk(mock_response["chunks"][1])
    assert chunk["choices"][0]["delta"]["content"] == " world"
    assert chunk["choices"][0]["finish_reason"] == "stop"

@pytest.mark.asyncio
async def test_get_status_healthy(openai_gateway):
    """Test status check with healthy response."""
    mock_version_response = AsyncMock()
    mock_version_response.status_code = 200
    mock_version_response.json = AsyncMock(return_value={"version": "1.0.0"})
    mock_version_response.raise_for_status = AsyncMock()
    mock_version_response.aread = AsyncMock()

    mock_tags_response = AsyncMock()
    mock_tags_response.status_code = 200
    mock_tags_response.json = AsyncMock(return_value=[
        {"name": "llama2"},
        {"name": "llama2:70b"}
    ])
    mock_tags_response.raise_for_status = AsyncMock()
    mock_tags_response.aread = AsyncMock()

    with patch.object(openai_gateway.client, 'get') as mock_get:
        mock_get.side_effect = [mock_version_response, mock_tags_response]
        
        status = await openai_gateway.get_status()
        
        assert status["status"] == "healthy"
        assert len(status["models"]) == 2
        assert status["models"][0]["object"] == "model"
        assert status["models"][0]["owned_by"] == "ollama"
        assert status["gateway_type"] == "openai"
        assert status["compatibility_mode"] is True

@pytest.mark.asyncio
async def test_get_status_unhealthy(openai_gateway):
    """Test status check with unhealthy response."""
    with patch.object(openai_gateway.client, 'get', side_effect=Exception("Connection failed")):
        status = await openai_gateway.get_status()
        
        assert status["status"] == "unhealthy"
        assert "error" in status
        assert "Connection failed" in status["error"]
        assert status["gateway_type"] == "openai"
        assert status["compatibility_mode"] is True
