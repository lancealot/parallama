import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from typing import Dict, Any

from parallama.gateway import (
    LLMGateway,
    GatewayRegistry,
    gateway_router,
)

class TestGateway(LLMGateway):
    """Test gateway implementation with configurable responses."""
    
    def __init__(self, auth_valid=True, status_error=False):
        self.auth_valid = auth_valid
        self.status_error = status_error
    
    async def validate_auth(self, credentials: str) -> bool:
        return self.auth_valid
    
    async def transform_request(self, request: Request) -> Dict[str, Any]:
        from fastapi import HTTPException
        try:
            body = await request.json()
        except:
            raise HTTPException(
                status_code=422,
                detail="Invalid JSON in request body"
            )
        
        return {
            "method": request.method,
            "path": request.url.path,
            "body": body
        }
    
    async def transform_response(self, response: Dict[str, Any]) -> Response:
        from fastapi.responses import JSONResponse
        return JSONResponse(content=response)
    
    async def get_status(self) -> Dict[str, Any]:
        if self.status_error:
            raise Exception("Status check failed")
        return {
            "status": "ok",
            "models": ["test-model"]
        }

@pytest.fixture
def app():
    """Create FastAPI application with gateway router."""
    app = FastAPI()
    app.include_router(gateway_router)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)

@pytest.fixture
def setup_gateways():
    """Setup test gateways and cleanup after tests."""
    GatewayRegistry.clear()
    GatewayRegistry.register("working", lambda: TestGateway(auth_valid=True))
    GatewayRegistry.register("failing", lambda: TestGateway(auth_valid=False))
    GatewayRegistry.register("error", lambda: TestGateway(status_error=True))
    yield
    GatewayRegistry.clear()

def test_discovery_endpoint(client, setup_gateways):
    """Test the gateway discovery endpoint."""
    response = client.get("/gateway/discovery")
    assert response.status_code == 200
    
    data = response.json()
    assert "gateways" in data
    assert "supported_types" in data
    
    # Check working gateway
    assert "working" in data["gateways"]
    assert data["gateways"]["working"]["status"] == "available"
    
    # Check error gateway
    assert "error" in data["gateways"]
    assert data["gateways"]["error"]["status"] == "unavailable"

@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
def test_gateway_methods(client, setup_gateways, method):
    """Test different HTTP methods through gateway."""
    headers = {"Authorization": "test-token"}
    data = {"test": "data"}
    
    response = client.request(
        method=method,
        url="/gateway/working/test",
        headers=headers,
        json=data
    )
    assert response.status_code == 200

def test_gateway_auth_validation(client, setup_gateways):
    """Test authentication validation scenarios."""
    # Test missing auth header
    response = client.post("/gateway/working/test", json={"test": "data"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authentication credentials"
    
    # Test invalid auth
    response = client.post(
        "/gateway/failing/test",
        headers={"Authorization": "invalid-token"},
        json={"test": "data"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"
    
    # Test valid auth
    response = client.post(
        "/gateway/working/test",
        headers={"Authorization": "valid-token"},
        json={"test": "data"}
    )
    assert response.status_code == 200

def test_gateway_not_found(client, setup_gateways):
    """Test handling of non-existent gateways."""
    response = client.post(
        "/gateway/nonexistent/test",
        headers={"Authorization": "test-token"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_gateway_error_handling(client, setup_gateways):
    """Test error handling in gateway operations."""
    # Test gateway that raises error during status check
    response = client.get("/gateway/discovery")
    assert response.status_code == 200
    data = response.json()
    assert data["gateways"]["error"]["status"] == "unavailable"
    
    # Test malformed request body
    response = client.post(
        "/gateway/working/test",
        headers={"Authorization": "test-token"},
        content="invalid json"
    )
    assert response.status_code == 422  # FastAPI's validation error

def test_path_parameters(client, setup_gateways):
    """Test handling of path parameters in gateway routes."""
    response = client.post(
        "/gateway/working/models/test-model/generate",
        headers={"Authorization": "test-token"},
        json={"prompt": "test"}
    )
    assert response.status_code == 200
    
    # Verify path is preserved in transformed request
    assert "/models/test-model/generate" in str(response.content)
