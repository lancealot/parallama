"""Tests for the OpenAI gateway."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import AsyncGenerator, Dict
from fastapi.responses import JSONResponse, StreamingResponse

from parallama.gateway.config import (
    OpenAIConfig,
    TokenCounterConfig,
    PerformanceConfig,
    EndpointConfig
)
from parallama.gateway.openai import OpenAIGateway
from parallama.gateway.endpoints import (
    EmbeddingsHandler,
    EditsHandler,
    ModerationsHandler
)

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
        },
        token_counter=TokenCounterConfig(
            enabled=True,
            cache_size=100,
            cache_ttl=60
        ),
        performance=PerformanceConfig(
            connection_pool_size=10,
            request_timeout=30,
            max_retries=2,
            batch_size=5
        ),
        endpoints=EndpointConfig(
            chat=True,
            completions=True,
            embeddings=True,
            edits=True,
            moderations=True
        )
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
async def test_endpoint_routing(openai_gateway):
    """Test routing requests to appropriate endpoint handlers."""
    mock_request = AsyncMock()
    mock_request.url.path = "/openai/v1/embeddings"
    mock_request.json.return_value = {
        "input": "test",
        "model": "text-embedding-ada-002"
    }
    
    # Mock handler responses
    mock_embeddings_response = JSONResponse(content={"test": "embeddings"})
    mock_edits_response = JSONResponse(content={"test": "edits"})
    mock_moderations_response = JSONResponse(content={"test": "moderations"})
    
    # Patch handler methods
    with patch.object(openai_gateway.embeddings_handler, 'handle_request', 
                     return_value=mock_embeddings_response) as mock_embeddings, \
         patch.object(openai_gateway.edits_handler, 'handle_request',
                     return_value=mock_edits_response) as mock_edits, \
         patch.object(openai_gateway.moderations_handler, 'handle_request',
                     return_value=mock_moderations_response) as mock_moderations:
        
        # Test embeddings routing
        mock_request.url.path = "/openai/v1/embeddings"
        response = await openai_gateway.handle_request(mock_request)
        assert response == mock_embeddings_response
        mock_embeddings.assert_called_once()
        mock_edits.assert_not_called()
        mock_moderations.assert_not_called()
        
        # Test edits routing
        mock_request.url.path = "/openai/v1/edits"
        response = await openai_gateway.handle_request(mock_request)
        assert response == mock_edits_response
        mock_edits.assert_called_once()
        
        # Test moderations routing
        mock_request.url.path = "/openai/v1/moderations"
        response = await openai_gateway.handle_request(mock_request)
        assert response == mock_moderations_response
        mock_moderations.assert_called_once()

@pytest.mark.asyncio
async def test_endpoint_handlers_initialization(openai_config):
    """Test endpoint handlers are properly initialized."""
    gateway = OpenAIGateway(openai_config)
    
    assert isinstance(gateway.embeddings_handler, EmbeddingsHandler)
    assert isinstance(gateway.edits_handler, EditsHandler)
    assert isinstance(gateway.moderations_handler, ModerationsHandler)
    
    assert gateway.embeddings_handler.config == openai_config
    assert gateway.edits_handler.config == openai_config
    assert gateway.moderations_handler.config == openai_config

@pytest.mark.asyncio
async def test_transform_chat_completion_request(openai_gateway):
    """Test chat completion request transformation."""
    mock_request = AsyncMock()
    mock_request.url.path = "/openai/v1/chat/completions"
    mock_request.state = MagicMock()
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
    assert hasattr(mock_request.state, "prompt_tokens")
    assert mock_request.state.prompt_tokens > 0

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
    mock_request = AsyncMock()
    mock_request.state = MagicMock()
    mock_request.state.prompt_tokens = 10
    mock_request.state.model = "gpt-3.5-turbo"

    mock_response = {
        "id": "test-123",
        "response": "Bonjour!",
        "model": "llama2",
        "_test_mode": True
    }
    
    result = await openai_gateway.transform_response(mock_response, mock_request)
    assert result.status_code == 200
    
    response_data = result.body.decode()
    assert "cmpl-" in response_data
    assert "chat.completion" in response_data
    assert "Bonjour!" in response_data
    
    # Verify token counting
    response_json = json.loads(response_data)
    assert response_json["usage"]["prompt_tokens"] == 10
    assert response_json["usage"]["completion_tokens"] > 0
    assert response_json["usage"]["total_tokens"] > 10

@pytest.mark.asyncio
async def test_transform_streaming_response(openai_gateway):
    """Test streaming response transformation."""
    mock_request = AsyncMock()
    mock_request.state = MagicMock()
    mock_request.state.model = "gpt-3.5-turbo"
    mock_request.state.completion_tokens = 0

    mock_response = {
        "stream": True,
        "chunks": [
            {"id": "1", "response": "Hello", "model": "llama2", "done": False},
            {"id": "2", "response": " world", "model": "llama2", "done": True}
        ]
    }
    
    result = await openai_gateway.transform_response(mock_response, mock_request)
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

    # Verify token counting was enabled
    assert hasattr(mock_request.state, "completion_tokens")
    assert mock_request.state.completion_tokens > 0

@pytest.mark.asyncio
async def test_performance_config(openai_gateway):
    """Test performance configuration."""
    # Verify client configuration
    assert openai_gateway.client.timeout == 30.0  # from config
    assert openai_gateway.client.limits.max_connections == 10  # from config
    assert openai_gateway.client.limits.max_keepalive_connections == 10  # from config

@pytest.mark.asyncio
async def test_token_counter_config(openai_gateway):
    """Test token counter configuration."""
    # Verify token counter configuration
    assert openai_gateway.token_counter.config.enabled is True
    assert openai_gateway.token_counter.config.cache_size == 100
    assert openai_gateway.token_counter.config.cache_ttl == 60

@pytest.mark.asyncio
async def test_endpoint_config(openai_gateway):
    """Test endpoint configuration."""
    # Verify endpoint configuration
    assert openai_gateway.config.endpoints.chat is True
    assert openai_gateway.config.endpoints.completions is True
    assert openai_gateway.config.endpoints.embeddings is False
    assert openai_gateway.config.endpoints.edits is False
    assert openai_gateway.config.endpoints.moderations is False

@pytest.mark.asyncio
async def test_token_counting_disabled(openai_config, openai_gateway):
    """Test behavior when token counting is disabled."""
    # Disable token counting
    openai_config.token_counter.enabled = False
    gateway = OpenAIGateway(openai_config)

    mock_request = AsyncMock()
    mock_request.url.path = "/openai/v1/chat/completions"
    mock_request.state = MagicMock()
    mock_request.json.return_value = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False
    }

    # Transform request should not set prompt_tokens
    result = await gateway.transform_request(mock_request)
    assert not hasattr(mock_request.state, "prompt_tokens")

    # Transform response should return 0 for token counts
    mock_response = {
        "id": "test-123",
        "response": "Hi!",
        "model": "llama2"
    }
    response = await gateway.transform_response(mock_response, mock_request)
    response_data = json.loads(response.body.decode())
    assert response_data["usage"]["prompt_tokens"] == 0
    assert response_data["usage"]["completion_tokens"] == 0
    assert response_data["usage"]["total_tokens"] == 0

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
async def test_token_counter_cache(openai_gateway):
    """Test token counter caching."""
    mock_request = AsyncMock()
    mock_request.url.path = "/openai/v1/completions"
    mock_request.state = MagicMock()
    mock_request.json.return_value = {
        "model": "gpt-3.5-turbo",
        "prompt": "Hello, world!",
        "stream": False
    }

    # First request should calculate tokens
    await openai_gateway.transform_request(mock_request)
    first_tokens = mock_request.state.prompt_tokens

    # Second request should use cache
    mock_request.state = MagicMock()  # Reset state
    await openai_gateway.transform_request(mock_request)
    second_tokens = mock_request.state.prompt_tokens

    assert first_tokens == second_tokens
    assert openai_gateway.token_counter.get_cache_stats()["hits"] > 0

@pytest.mark.asyncio
async def test_handle_error_timeout(openai_gateway):
    """Test error handling for timeout errors."""
    from httpx import ReadTimeout
    error = ReadTimeout("Request timed out")
    response = await openai_gateway.handle_error(error)
    
    assert response.status_code == 504
    assert "timed out" in response.body.decode()

@pytest.mark.asyncio
async def test_handle_error_connection(openai_gateway):
    """Test error handling for connection errors."""
    from httpx import ConnectError
    error = ConnectError("Failed to connect")
    response = await openai_gateway.handle_error(error)
    
    assert response.status_code == 502
    assert "Failed to connect" in response.body.decode()

@pytest.mark.asyncio
async def test_handle_error_http_status(openai_gateway):
    """Test error handling for HTTP status errors."""
    from httpx import HTTPStatusError
    mock_response = AsyncMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {"error": "Rate limit exceeded"}
    error = HTTPStatusError("Rate limit", request=AsyncMock(), response=mock_response)
    
    response = await openai_gateway.handle_error(error)
    assert response.status_code == 429
    assert "Rate limit" in response.body.decode()

@pytest.mark.asyncio
async def test_transform_request_invalid_model(openai_gateway):
    """Test request transformation with invalid model."""
    mock_request = AsyncMock()
    mock_request.url.path = "/openai/v1/completions"
    mock_request.state = MagicMock()
    mock_request.json.return_value = {
        "model": "invalid-model",
        "prompt": "test"
    }
    
    result = await openai_gateway.transform_request(mock_request)
    assert result["model"] == "invalid-model"  # Uses unmapped model name

@pytest.mark.asyncio
async def test_transform_chat_request_empty_messages(openai_gateway):
    """Test chat request transformation with empty messages."""
    mock_request = AsyncMock()
    mock_request.url.path = "/openai/v1/chat/completions"
    mock_request.state = MagicMock()
    mock_request.json.return_value = {
        "model": "gpt-3.5-turbo",
        "messages": []
    }
    
    result = await openai_gateway.transform_request(mock_request)
    assert result["prompt"] == ""
    assert result["model"] == "llama2"

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

@pytest.mark.asyncio
async def test_validate_auth(openai_gateway):
    """Test authentication validation in compatibility mode."""
    result = await openai_gateway.validate_auth("test-token")
    assert result is True  # Always returns True in compatibility mode

@pytest.mark.asyncio
async def test_transform_response_with_test_mode(openai_gateway):
    """Test response transformation in test mode."""
    mock_request = AsyncMock()
    mock_request.state = MagicMock()
    mock_request.state.prompt_tokens = 5
    mock_request.state.model = "gpt-3.5-turbo"
    mock_request.headers = {"_test_mode": "true"}

    mock_response = {
        "id": "test-123",
        "response": "Test response",
        "model": "llama2",
        "_test_mode": True,
        "prompt_tokens": 5,
        "completion_tokens": 3,
        "total_tokens": 8
    }
    
    result = await openai_gateway.transform_response(mock_response, mock_request)
    response_data = json.loads(result.body.decode())
    
    assert response_data["_test_mode"] is True
    assert response_data["prompt_tokens"] == 5
    assert response_data["completion_tokens"] == 3
    assert response_data["total_tokens"] == 8
