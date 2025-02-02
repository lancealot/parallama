"""Tests for the gateway base class and registry."""

import pytest
from unittest.mock import AsyncMock, patch

from parallama.gateway import GatewayRegistry, GatewayType
from parallama.gateway.config import GatewayConfig, RateLimitConfig
from .test_utils import MockGateway

@pytest.fixture
def test_config():
    """Create test gateway configuration."""
    return GatewayConfig(
        name="test-gateway",
        base_path="/test",
        enabled=True
    )

@pytest.fixture
def test_gateway(test_config):
    """Create test gateway instance."""
    return MockGateway(test_config)

def test_gateway_registration(test_config):
    """Test gateway registration and retrieval."""
    GatewayRegistry.clear()
    
    # Register gateway
    GatewayRegistry.register(GatewayType.OLLAMA, MockGateway)
    assert GatewayType.OLLAMA in GatewayRegistry.list_gateways()
    
    # Create and store instance
    gateway_instance = MockGateway(test_config)
    GatewayRegistry._instances[GatewayType.OLLAMA] = gateway_instance
    
    # Get gateway
    gateway = GatewayRegistry.get_gateway(GatewayType.OLLAMA)
    assert isinstance(gateway, MockGateway)
    
    GatewayRegistry.clear()

def test_gateway_config():
    """Test gateway configuration."""
    config = GatewayConfig(
        name="test",
        base_path="/test",
        enabled=True,
        rate_limits=RateLimitConfig(
            requests_per_hour=100,
            requests_per_day=1000
        )
    )
    
    assert config.name == "test"
    assert config.base_path == "/test"
    assert config.enabled is True
    assert config.rate_limits.requests_per_hour == 100

def test_gateway_discovery():
    """Test gateway discovery."""
    GatewayRegistry.clear()
    
    # Register multiple gateways
    GatewayRegistry.register(GatewayType.OLLAMA, MockGateway)
    GatewayRegistry.register(GatewayType.OPENAI, MockGateway)
    
    gateways = GatewayRegistry.list_gateways()
    assert len(gateways) == 2
    assert GatewayType.OLLAMA in gateways
    assert GatewayType.OPENAI in gateways
    
    GatewayRegistry.clear()

@pytest.mark.asyncio
async def test_gateway_routing(test_gateway):
    """Test request routing through gateway."""
    mock_request = AsyncMock()
    mock_request.headers = {"Authorization": "Bearer test-token", "_test_mode": "true"}
    mock_request.json = AsyncMock(return_value={"test": "data"})
    
    # Test request transformation
    transformed = await test_gateway.transform_request(mock_request)
    assert transformed == {"test": "data"}
    
    # Test response transformation
    response = await test_gateway.transform_response(transformed)
    assert response.status_code == 200
    assert response.body == b'{"status":"ok"}'

def test_gateway_type_enum():
    """Test gateway type enumeration."""
    assert GatewayType.OLLAMA == "ollama"
    assert GatewayType.OPENAI == "openai"
    assert list(GatewayType) == ["ollama", "openai"]

def test_gateway_registry_clear():
    """Test gateway registry cleanup."""
    GatewayRegistry.clear()
    assert len(GatewayRegistry.list_gateways()) == 0
    
    GatewayRegistry.register(GatewayType.OLLAMA, MockGateway)
    assert len(GatewayRegistry.list_gateways()) == 1
    
    GatewayRegistry.clear()
    assert len(GatewayRegistry.list_gateways()) == 0
