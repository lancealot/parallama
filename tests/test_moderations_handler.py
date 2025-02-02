"""Tests for the moderations endpoint handler."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request

from parallama.gateway.config import OpenAIConfig, TokenCounterConfig, EndpointConfig
from parallama.gateway.endpoints.moderations import ModerationsHandler

@pytest.fixture
def moderations_config():
    """Create a test configuration with moderations enabled."""
    return OpenAIConfig(
        name="test-openai",
        base_path="/openai/v1",
        enabled=True,
        compatibility_mode=True,
        token_counter=TokenCounterConfig(
            enabled=True,
            cache_size=100,
            cache_ttl=60
        ),
        endpoints=EndpointConfig(
            moderations=True
        )
    )

@pytest.fixture
def moderations_handler(moderations_config):
    """Create a test moderations handler."""
    return ModerationsHandler(moderations_config)

@pytest.mark.asyncio
async def test_moderations_basic_request(moderations_handler):
    """Test basic moderation request."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.app.state.token_counter.count_tokens.return_value = 5
    mock_request.state.start_time = 1234567890
    
    mock_request.json.return_value = {
        "input": "Hello, world!"
    }
    
    response = await moderations_handler.handle_request(mock_request)
    assert response.status_code == 200
    
    data = response.body.decode()
    response_json = json.loads(data)
    
    assert response_json["model"] == "text-moderation-latest"
    assert len(response_json["results"]) == 1
    assert "flagged" in response_json["results"][0]
    assert "categories" in response_json["results"][0]
    assert "category_scores" in response_json["results"][0]
    assert response_json["usage"]["prompt_tokens"] == 5

@pytest.mark.asyncio
async def test_moderations_batch_request(moderations_handler):
    """Test batch moderation request."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.app.state.token_counter.count_tokens.return_value = 3
    mock_request.state.start_time = 1234567890
    
    mock_request.json.return_value = {
        "input": ["Hello", "World", "Test"]
    }
    
    response = await moderations_handler.handle_request(mock_request)
    assert response.status_code == 200
    
    data = response.body.decode()
    response_json = json.loads(data)
    
    assert len(response_json["results"]) == 3
    assert response_json["usage"]["prompt_tokens"] == 9  # 3 tokens per text

@pytest.mark.asyncio
async def test_moderations_disabled(moderations_config):
    """Test behavior when moderations endpoint is disabled."""
    moderations_config.endpoints.moderations = False
    handler = ModerationsHandler(moderations_config)
    
    mock_request = AsyncMock()
    mock_request.json.return_value = {
        "input": "test"
    }
    
    response = await handler.handle_request(mock_request)
    assert response.status_code == 404
    assert "not enabled" in response.body.decode()

@pytest.mark.asyncio
async def test_moderations_validation(moderations_handler):
    """Test moderations request validation."""
    # Test missing input
    result = await moderations_handler.validate_request({})
    assert "required" in result["error"]
    
    # Test invalid input type
    result = await moderations_handler.validate_request({
        "input": 123
    })
    assert "must be a string or array" in result["error"]
    
    # Test empty string input
    result = await moderations_handler.validate_request({
        "input": ""
    })
    assert "must not be empty" in result["error"]
    
    # Test empty array input
    result = await moderations_handler.validate_request({
        "input": []
    })
    assert "must not be empty" in result["error"]
    
    # Test invalid array items
    result = await moderations_handler.validate_request({
        "input": ["test", 123, "hello"]
    })
    assert "must be strings" in result["error"]
    
    # Test too many items
    result = await moderations_handler.validate_request({
        "input": ["test"] * 101
    })
    assert "maximum of 100" in result["error"]
    
    # Test valid requests
    result = await moderations_handler.validate_request({
        "input": "test"
    })
    assert not result
    
    result = await moderations_handler.validate_request({
        "input": ["test1", "test2"]
    })
    assert not result

@pytest.mark.asyncio
async def test_moderations_token_counting_disabled(moderations_config):
    """Test behavior when token counting is disabled."""
    moderations_config.token_counter.enabled = False
    handler = ModerationsHandler(moderations_config)
    
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.state.start_time = 1234567890
    mock_request.json.return_value = {
        "input": "test"
    }
    
    response = await handler.handle_request(mock_request)
    assert response.status_code == 200
    
    data = response.body.decode()
    response_json = json.loads(data)
    
    # Token counts should be 0 when disabled
    assert response_json["usage"]["prompt_tokens"] == 0
    assert response_json["usage"]["total_tokens"] == 0
    
    # Token counter should not have been called
    mock_request.app.state.token_counter.count_tokens.assert_not_called()

@pytest.mark.asyncio
async def test_moderations_content_detection(moderations_handler):
    """Test content moderation detection."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.state.start_time = 1234567890
    
    # Test safe content
    mock_request.json.return_value = {
        "input": "Hello, this is a friendly message!"
    }
    response = await moderations_handler.handle_request(mock_request)
    data = json.loads(response.body.decode())
    assert not data["results"][0]["flagged"]
    assert not any(data["results"][0]["categories"].values())
    
    # Test hate content
    mock_request.json.return_value = {
        "input": "I hate everyone and want to discriminate."
    }
    response = await moderations_handler.handle_request(mock_request)
    data = json.loads(response.body.decode())
    assert data["results"][0]["flagged"]
    assert data["results"][0]["categories"]["hate"]
    
    # Test violent content
    mock_request.json.return_value = {
        "input": "There was a violent fight with blood."
    }
    response = await moderations_handler.handle_request(mock_request)
    data = json.loads(response.body.decode())
    assert data["results"][0]["flagged"]
    assert data["results"][0]["categories"]["violence"]

@pytest.mark.asyncio
async def test_moderations_score_thresholds(moderations_handler):
    """Test moderation score thresholds."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.state.start_time = 1234567890
    
    # Test borderline content (single mention)
    mock_request.json.return_value = {
        "input": "One hate word."  # Single mention should be below threshold
    }
    response = await moderations_handler.handle_request(mock_request)
    data = json.loads(response.body.decode())
    assert not data["results"][0]["flagged"]
    assert data["results"][0]["category_scores"]["hate"] < 0.5
    
    # Test clear violation (multiple mentions)
    mock_request.json.return_value = {
        "input": "Hate hate hate hate hate."  # Multiple mentions should exceed threshold
    }
    response = await moderations_handler.handle_request(mock_request)
    data = json.loads(response.body.decode())
    assert data["results"][0]["flagged"]
    assert data["results"][0]["category_scores"]["hate"] > 0.5

@pytest.mark.asyncio
async def test_moderations_model_info(moderations_handler):
    """Test model info retrieval."""
    info = moderations_handler._get_model_info()
    assert info["id"] == "text-moderation-latest"
    assert info["ready"] is True
    assert info["status"]["status"] == "operational"
    assert info["status"]["error"] is None
