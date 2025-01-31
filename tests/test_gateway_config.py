import pytest
from pydantic import ValidationError
from parallama.gateway import (
    GatewayType,
    GatewayConfig,
    RateLimitConfig,
    OllamaConfig,
    OpenAIConfig,
)

def test_rate_limit_config_validation():
    """Test rate limit configuration validation."""
    # Test valid configuration
    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=3600,
        tokens_per_minute=1000,
        tokens_per_hour=50000
    )
    assert config.requests_per_minute == 60
    assert config.requests_per_hour == 3600
    
    # Test hourly rate validation
    with pytest.raises(ValidationError) as exc_info:
        RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000  # Less than requests_per_minute * 60
        )
    assert "Hourly rate must be >= per-minute rate * 60" in str(exc_info.value)
    
    # Test minimum values
    with pytest.raises(ValidationError):
        RateLimitConfig(requests_per_minute=0)
    
    with pytest.raises(ValidationError):
        RateLimitConfig(requests_per_hour=0)

def test_gateway_config_validation():
    """Test gateway configuration validation."""
    # Test base path validation
    config = GatewayConfig(
        name="test",
        type=GatewayType.OLLAMA,
        base_path="test"  # Missing leading slash
    )
    assert config.base_path == "/test"  # Should add leading slash
    
    config = GatewayConfig(
        name="test",
        type=GatewayType.OLLAMA,
        base_path="/test/"  # With trailing slash
    )
    assert config.base_path == "/test"  # Should remove trailing slash
    
    # Test model mappings
    config = GatewayConfig(
        name="test",
        type=GatewayType.OLLAMA,
        base_path="/test",
        model_mappings={
            "gpt-3.5-turbo": "llama2",
            "gpt-4": "llama2-70b"
        }
    )
    assert config.get_model_mapping("gpt-3.5-turbo") == "llama2"
    assert config.get_model_mapping("unknown-model") == "unknown-model"

def test_ollama_config():
    """Test Ollama-specific configuration."""
    config = OllamaConfig(name="ollama")
    
    # Test defaults
    assert config.type == GatewayType.OLLAMA
    assert config.base_path == "/ollama/v1"
    assert config.host == "http://localhost"
    assert config.port == 11434
    
    # Test custom values
    config = OllamaConfig(
        name="ollama",
        host="http://custom-host",
        port=8080
    )
    assert config.get_endpoint_url() == "http://custom-host:8080/ollama/v1"

def test_openai_config():
    """Test OpenAI-compatible configuration."""
    config = OpenAIConfig(name="openai")
    
    # Test defaults
    assert config.type == GatewayType.OPENAI
    assert config.base_path == "/openai/v1"
    assert config.compatibility_mode is True
    
    # Test with host and port
    config = OpenAIConfig(
        name="openai",
        host="http://localhost",
        port=8000
    )
    assert config.get_endpoint_url() == "http://localhost:8000/openai/v1"
    
    # Test without port
    config = OpenAIConfig(
        name="openai",
        host="http://api.example.com"
    )
    assert config.get_endpoint_url() == "http://api.example.com/openai/v1"

def test_custom_config():
    """Test custom configuration options."""
    config = GatewayConfig(
        name="test",
        type=GatewayType.OLLAMA,
        base_path="/test",
        custom_config={
            "timeout": 30,
            "max_retries": 3,
            "features": ["streaming", "batch"]
        }
    )
    assert config.custom_config["timeout"] == 30
    assert "streaming" in config.custom_config["features"]
