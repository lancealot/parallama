"""Tests for the embeddings endpoint handler."""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request

from parallama.gateway.config import OpenAIConfig, TokenCounterConfig, EndpointConfig
from parallama.gateway.endpoints.embeddings import EmbeddingsHandler

@pytest.fixture
def embeddings_config():
    """Create a test configuration with embeddings enabled."""
    return OpenAIConfig(
        name="test-openai",
        base_path="/openai/v1",
        enabled=True,
        compatibility_mode=True,
        model_mappings={
            "text-embedding-ada-002": "llama2"
        },
        token_counter=TokenCounterConfig(
            enabled=True,
            cache_size=100,
            cache_ttl=60
        ),
        endpoints=EndpointConfig(
            embeddings=True
        )
    )

@pytest.fixture
def embeddings_handler(embeddings_config):
    """Create a test embeddings handler."""
    return EmbeddingsHandler(embeddings_config)

@pytest.mark.asyncio
async def test_embeddings_single_text(embeddings_handler):
    """Test generating embeddings for a single text input."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.app.state.token_counter.count_tokens.return_value = 5
    
    mock_request.json.return_value = {
        "model": "text-embedding-ada-002",
        "input": "Hello, world!"
    }
    
    response = await embeddings_handler.handle_request(mock_request)
    assert response.status_code == 200
    
    data = response.body.decode()
    response_json = eval(data)  # Safe since we control the input
    
    assert response_json["object"] == "list"
    assert len(response_json["data"]) == 1
    assert response_json["data"][0]["object"] == "embedding"
    assert len(response_json["data"][0]["embedding"]) == 1536  # Default dimension
    assert response_json["usage"]["prompt_tokens"] == 5
    assert response_json["usage"]["total_tokens"] == 5

@pytest.mark.asyncio
async def test_embeddings_batch(embeddings_handler):
    """Test generating embeddings for multiple texts."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.app.state.token_counter.count_tokens.return_value = 3
    
    mock_request.json.return_value = {
        "model": "text-embedding-ada-002",
        "input": ["Hello", "World", "!"]
    }
    
    response = await embeddings_handler.handle_request(mock_request)
    assert response.status_code == 200
    
    data = response.body.decode()
    response_json = eval(data)
    
    assert len(response_json["data"]) == 3
    assert response_json["usage"]["prompt_tokens"] == 9  # 3 tokens per text
    
    # Check embeddings are different
    embeddings = [item["embedding"] for item in response_json["data"]]
    assert not np.allclose(embeddings[0], embeddings[1])

@pytest.mark.asyncio
async def test_embeddings_disabled(embeddings_config):
    """Test behavior when embeddings endpoint is disabled."""
    embeddings_config.endpoints.embeddings = False
    handler = EmbeddingsHandler(embeddings_config)
    
    mock_request = AsyncMock()
    mock_request.json.return_value = {
        "model": "text-embedding-ada-002",
        "input": "test"
    }
    
    response = await handler.handle_request(mock_request)
    assert response.status_code == 404
    assert "not enabled" in response.body.decode()

@pytest.mark.asyncio
async def test_embeddings_validation(embeddings_handler):
    """Test embeddings request validation."""
    # Test missing input
    result = await embeddings_handler.validate_request({})
    assert "required" in result["error"]
    
    # Test empty input
    result = await embeddings_handler.validate_request({"input": []})
    assert "empty" in result["error"]
    
    # Test invalid input type
    result = await embeddings_handler.validate_request({"input": [1, 2, 3]})
    assert "strings" in result["error"]
    
    # Test too many inputs
    result = await embeddings_handler.validate_request({
        "input": ["test"] * 101
    })
    assert "100" in result["error"]
    
    # Test valid input
    result = await embeddings_handler.validate_request({
        "input": ["test1", "test2"]
    })
    assert not result

@pytest.mark.asyncio
async def test_embeddings_token_counting_disabled(embeddings_config):
    """Test behavior when token counting is disabled."""
    embeddings_config.token_counter.enabled = False
    handler = EmbeddingsHandler(embeddings_config)
    
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.json.return_value = {
        "model": "text-embedding-ada-002",
        "input": "test"
    }
    
    response = await handler.handle_request(mock_request)
    assert response.status_code == 200
    
    data = response.body.decode()
    response_json = eval(data)
    
    # Token counts should be 0 when disabled
    assert response_json["usage"]["prompt_tokens"] == 0
    assert response_json["usage"]["total_tokens"] == 0
    
    # Token counter should not have been called
    mock_request.app.state.token_counter.count_tokens.assert_not_called()

@pytest.mark.asyncio
async def test_embeddings_dimensions(embeddings_handler):
    """Test embedding dimensions for different models."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    
    # Test OpenAI model dimension
    mock_request.json.return_value = {
        "model": "text-embedding-ada-002",
        "input": "test"
    }
    response = await embeddings_handler.handle_request(mock_request)
    data = eval(response.body.decode())
    assert len(data["data"][0]["embedding"]) == 1536
    
    # Test Llama model dimension
    mock_request.json.return_value = {
        "model": "llama2",
        "input": "test"
    }
    response = await embeddings_handler.handle_request(mock_request)
    data = eval(response.body.decode())
    assert len(data["data"][0]["embedding"]) == 4096

@pytest.mark.asyncio
async def test_embeddings_reproducibility(embeddings_handler):
    """Test that embeddings are reproducible for same input."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.json.return_value = {
        "model": "text-embedding-ada-002",
        "input": "test"
    }
    
    # Generate embeddings twice
    response1 = await embeddings_handler.handle_request(mock_request)
    response2 = await embeddings_handler.handle_request(mock_request)
    
    data1 = eval(response1.body.decode())
    data2 = eval(response2.body.decode())
    
    # Embeddings should be identical for same input
    assert np.allclose(
        data1["data"][0]["embedding"],
        data2["data"][0]["embedding"]
    )

@pytest.mark.asyncio
async def test_embeddings_normalization(embeddings_handler):
    """Test that embeddings are normalized to unit length."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.json.return_value = {
        "model": "text-embedding-ada-002",
        "input": "test"
    }
    
    response = await embeddings_handler.handle_request(mock_request)
    data = eval(response.body.decode())
    embedding = np.array(data["data"][0]["embedding"])
    
    # Check L2 norm is approximately 1
    norm = np.linalg.norm(embedding)
    assert abs(norm - 1.0) < 1e-6
