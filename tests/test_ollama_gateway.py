import pytest
from httpx import AsyncClient
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from parallama.gateway.config import OllamaConfig
from parallama.gateway.ollama import OllamaGateway

@pytest.fixture
def ollama_config():
    """Create a test Ollama gateway configuration."""
    return OllamaConfig(
        name="test-ollama",
        host="http://localhost",
        port=11434,
        base_path="/ollama/v1",
        enabled=True
    )

@pytest_asyncio.fixture
async def ollama_gateway(ollama_config):
    """Create a test Ollama gateway instance."""
    gateway = OllamaGateway(ollama_config)
    yield gateway
    await gateway.close()

@pytest.mark.asyncio
async def test_gateway_initialization(ollama_config):
    """Test gateway initialization with valid config."""
    gateway = OllamaGateway(ollama_config)
    assert gateway.base_url == "http://localhost:11434/ollama/v1"
    await gateway.close()

@pytest.mark.asyncio
async def test_gateway_initialization_invalid():
    """Test gateway initialization with invalid config."""
    config = OllamaConfig(
        name="test-ollama",
        base_path="/ollama/v1",
        enabled=True
    )
    config.host = None  # Make config invalid
    
    with pytest.raises(ValueError, match="Ollama gateway requires host configuration"):
        OllamaGateway(config)

@pytest.mark.asyncio
async def test_transform_request(ollama_gateway):
    """Test request transformation."""
    mock_request = AsyncMock()
    mock_request.json.return_value = {
        "model": "llama2",
        "prompt": "Hello, world!"
    }
    
    result = await ollama_gateway.transform_request(mock_request)
    assert result == {
        "model": "llama2",
        "prompt": "Hello, world!"
    }

@pytest.mark.asyncio
async def test_transform_request_with_mapping(ollama_gateway):
    """Test request transformation with model mapping."""
    # Add a model mapping
    ollama_gateway.config.model_mappings = {"gpt-3.5-turbo": "llama2"}
    
    mock_request = AsyncMock()
    mock_request.json.return_value = {
        "model": "gpt-3.5-turbo",
        "prompt": "Hello, world!"
    }
    
    result = await ollama_gateway.transform_request(mock_request)
    assert result == {
        "model": "llama2",
        "prompt": "Hello, world!"
    }

@pytest.mark.asyncio
async def test_transform_response(ollama_gateway):
    """Test response transformation."""
    mock_response = {
        "model": "llama2",
        "response": "Hello! How can I help you today?"
    }
    
    result = await ollama_gateway.transform_response(mock_response)
    assert result.status_code == 200
    assert result.body.decode() == '{"model":"llama2","response":"Hello! How can I help you today?"}'

@pytest.mark.asyncio
async def test_get_status_healthy(ollama_gateway):
    """Test status check with healthy response."""
    # Mock successful responses
    mock_models_response = AsyncMock()
    mock_models_response.status_code = 200
    mock_models_response.json = AsyncMock(return_value=["llama2", "codellama"])
    mock_models_response.raise_for_status = AsyncMock()
    
    mock_version_response = AsyncMock()
    mock_version_response.status_code = 200
    mock_version_response.json = AsyncMock(return_value={"version": "0.1.0"})
    mock_version_response.raise_for_status = AsyncMock()
    
    # Patch the client's get method
    with patch.object(ollama_gateway.client, 'get') as mock_get:
        mock_get.side_effect = [mock_models_response, mock_version_response]
        
        status = await ollama_gateway.get_status()
        
        # Verify the mock was called correctly
        assert mock_get.call_count == 2
        mock_get.assert_any_call("/api/tags")
        mock_get.assert_any_call("/api/version")
        
        # Verify the response
        assert status["status"] == "healthy"
        assert status["models"] == ["llama2", "codellama"]
        assert status["version"] == {"version": "0.1.0"}
        assert status["gateway_type"] == "ollama"
        assert status["endpoint"] == ollama_gateway.base_url

@pytest.mark.asyncio
async def test_get_status_unhealthy(ollama_gateway):
    """Test status check with unhealthy response."""
    # Mock failed response
    with patch.object(ollama_gateway.client, 'get', side_effect=Exception("Connection failed")):
        status = await ollama_gateway.get_status()
        
        assert status["status"] == "unhealthy"
        assert "error" in status
        assert "Connection failed" in status["error"]
        assert status["gateway_type"] == "ollama"
        assert status["endpoint"] == ollama_gateway.base_url
