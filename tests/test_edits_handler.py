"""Tests for the edits endpoint handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request

from parallama.gateway.config import OpenAIConfig, TokenCounterConfig, EndpointConfig
from parallama.gateway.endpoints.edits import EditsHandler

@pytest.fixture
def edits_config():
    """Create a test configuration with edits enabled."""
    return OpenAIConfig(
        name="test-openai",
        base_path="/openai/v1",
        enabled=True,
        compatibility_mode=True,
        model_mappings={
            "text-davinci-edit-001": "llama2"
        },
        token_counter=TokenCounterConfig(
            enabled=True,
            cache_size=100,
            cache_ttl=60
        ),
        endpoints=EndpointConfig(
            edits=True
        )
    )

@pytest.fixture
def edits_handler(edits_config):
    """Create a test edits handler."""
    return EditsHandler(edits_config)

@pytest.mark.asyncio
async def test_edits_basic_request(edits_handler):
    """Test basic edit request."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.app.state.token_counter.count_tokens.return_value = 5
    mock_request.state.start_time = 1234567890
    
    mock_request.json.return_value = {
        "model": "text-davinci-edit-001",
        "input": "teh cat",
        "instruction": "Fix spelling"
    }
    
    response = await edits_handler.handle_request(mock_request)
    assert response.status_code == 200
    
    data = response.body.decode()
    response_json = eval(data)  # Safe since we control the input
    
    assert response_json["object"] == "edit"
    assert len(response_json["choices"]) == 1
    assert "the cat" in response_json["choices"][0]["text"]
    assert response_json["usage"]["prompt_tokens"] == 5

@pytest.mark.asyncio
async def test_edits_multiple_outputs(edits_handler):
    """Test generating multiple edits."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.app.state.token_counter.count_tokens.return_value = 3
    mock_request.state.start_time = 1234567890
    
    mock_request.json.return_value = {
        "model": "text-davinci-edit-001",
        "input": "hello world",
        "instruction": "Make variations",
        "n": 3,
        "temperature": 0.8
    }
    
    response = await edits_handler.handle_request(mock_request)
    assert response.status_code == 200
    
    data = response.body.decode()
    response_json = eval(data)
    
    assert len(response_json["choices"]) == 3
    # Check variations are different
    texts = [choice["text"] for choice in response_json["choices"]]
    assert len(set(texts)) == 3

@pytest.mark.asyncio
async def test_edits_disabled(edits_config):
    """Test behavior when edits endpoint is disabled."""
    edits_config.endpoints.edits = False
    handler = EditsHandler(edits_config)
    
    mock_request = AsyncMock()
    mock_request.json.return_value = {
        "model": "text-davinci-edit-001",
        "input": "test",
        "instruction": "uppercase"
    }
    
    response = await handler.handle_request(mock_request)
    assert response.status_code == 404
    assert "not enabled" in response.body.decode()

@pytest.mark.asyncio
async def test_edits_validation(edits_handler):
    """Test edits request validation."""
    # Test missing instruction
    result = await edits_handler.validate_request({})
    assert "required" in result["error"]
    
    # Test invalid instruction type
    result = await edits_handler.validate_request({
        "instruction": 123
    })
    assert "must be a string" in result["error"]
    
    # Test invalid input type
    result = await edits_handler.validate_request({
        "instruction": "test",
        "input": 123
    })
    assert "must be a string" in result["error"]
    
    # Test invalid n
    result = await edits_handler.validate_request({
        "instruction": "test",
        "n": 0
    })
    assert "between 1 and 20" in result["error"]
    
    result = await edits_handler.validate_request({
        "instruction": "test",
        "n": 21
    })
    assert "between 1 and 20" in result["error"]
    
    # Test invalid temperature
    result = await edits_handler.validate_request({
        "instruction": "test",
        "temperature": -1
    })
    assert "between 0 and 2" in result["error"]
    
    result = await edits_handler.validate_request({
        "instruction": "test",
        "temperature": 3
    })
    assert "between 0 and 2" in result["error"]
    
    # Test valid request
    result = await edits_handler.validate_request({
        "instruction": "test",
        "input": "hello",
        "n": 2,
        "temperature": 0.7
    })
    assert not result

@pytest.mark.asyncio
async def test_edits_token_counting_disabled(edits_config):
    """Test behavior when token counting is disabled."""
    edits_config.token_counter.enabled = False
    handler = EditsHandler(edits_config)
    
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.state.start_time = 1234567890
    mock_request.json.return_value = {
        "model": "text-davinci-edit-001",
        "input": "test",
        "instruction": "uppercase"
    }
    
    response = await handler.handle_request(mock_request)
    assert response.status_code == 200
    
    data = response.body.decode()
    response_json = eval(data)
    
    # Token counts should be 0 when disabled
    assert response_json["usage"]["prompt_tokens"] == 0
    assert response_json["usage"]["completion_tokens"] == 0
    assert response_json["usage"]["total_tokens"] == 0
    
    # Token counter should not have been called
    mock_request.app.state.token_counter.count_tokens.assert_not_called()

@pytest.mark.asyncio
async def test_edits_specific_instructions(edits_handler):
    """Test specific editing instructions."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.state.start_time = 1234567890
    
    # Test uppercase instruction
    mock_request.json.return_value = {
        "input": "hello world",
        "instruction": "uppercase"
    }
    response = await edits_handler.handle_request(mock_request)
    data = eval(response.body.decode())
    assert data["choices"][0]["text"] == "HELLO WORLD"
    
    # Test lowercase instruction
    mock_request.json.return_value = {
        "input": "HELLO WORLD",
        "instruction": "lowercase"
    }
    response = await edits_handler.handle_request(mock_request)
    data = eval(response.body.decode())
    assert data["choices"][0]["text"] == "hello world"
    
    # Test spell fix instruction
    mock_request.json.return_value = {
        "input": "teh recieve",
        "instruction": "fix spelling"
    }
    response = await edits_handler.handle_request(mock_request)
    data = eval(response.body.decode())
    assert data["choices"][0]["text"] == "the receive"

@pytest.mark.asyncio
async def test_edits_temperature_effect(edits_handler):
    """Test temperature effect on variations."""
    mock_request = AsyncMock()
    mock_request.app = MagicMock()
    mock_request.app.state.token_counter = AsyncMock()
    mock_request.state.start_time = 1234567890
    
    # Test with low temperature
    mock_request.json.return_value = {
        "input": "hello",
        "instruction": "test",
        "n": 3,
        "temperature": 0.1
    }
    response = await edits_handler.handle_request(mock_request)
    data = eval(response.body.decode())
    texts = [choice["text"] for choice in data["choices"]]
    # Low temperature should produce similar outputs
    assert all("variation" not in text for text in texts)
    
    # Test with high temperature
    mock_request.json.return_value = {
        "input": "hello",
        "instruction": "test",
        "n": 3,
        "temperature": 0.8
    }
    response = await edits_handler.handle_request(mock_request)
    data = eval(response.body.decode())
    texts = [choice["text"] for choice in data["choices"]]
    # High temperature should produce variations
    assert any("variation" in text for text in texts[1:])
