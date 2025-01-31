from typing import Dict, Any, List
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from .registry import GatewayRegistry
from .config import GatewayType
from ..core.exceptions import GatewayError

router = APIRouter(prefix="/gateway", tags=["gateway"])

async def get_gateway_status(gateway_name: str) -> Dict[str, Any]:
    """Get status information for a specific gateway.
    
    Args:
        gateway_name: Name of the gateway to check
        
    Returns:
        Dict containing gateway status information
        
    Raises:
        GatewayError: If gateway is not found or status check fails
    """
    gateway = GatewayRegistry.get_gateway(gateway_name)
    if not gateway:
        raise GatewayError(f"Gateway '{gateway_name}' not found")
    
    try:
        return await gateway.get_status()
    except Exception as e:
        raise GatewayError(f"Failed to get status for gateway '{gateway_name}': {str(e)}")

@router.get("/discovery")
async def discover_gateways() -> Dict[str, Any]:
    """List all available gateways and their status.
    
    Returns:
        Dict containing:
        - List of registered gateways
        - Status information for each gateway
        - Supported features and capabilities
    """
    gateways = GatewayRegistry.list_gateways()
    
    gateway_info = {}
    for name, _ in gateways.items():
        try:
            status = await get_gateway_status(name)
            gateway_info[name] = {
                "status": "available",
                "info": status
            }
        except GatewayError:
            gateway_info[name] = {
                "status": "unavailable",
                "info": None
            }
    
    return {
        "gateways": gateway_info,
        "supported_types": [gt.value for gt in GatewayType],
        "timestamp": "utc_timestamp_here"  # TODO: Add actual timestamp
    }

@router.api_route("/{gateway_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_request(
    gateway_name: str,
    path: str,
    request: Request
) -> Response:
    """Route requests to appropriate gateway implementation.
    
    Args:
        gateway_name: Name of the target gateway
        path: Request path after gateway name
        request: Original FastAPI request
        
    Returns:
        Response from the gateway
        
    Raises:
        HTTPException: If gateway is not found or request fails
    """
    gateway = GatewayRegistry.get_gateway(gateway_name)
    if not gateway:
        raise HTTPException(
            status_code=404,
            detail=f"Gateway '{gateway_name}' not found"
        )
    
    try:
        # Validate authentication
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=401,
                detail="Missing authentication credentials"
            )
        
        is_valid = await gateway.validate_auth(auth_header)
        if not is_valid:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )
        
        # Transform and forward request
        transformed_request = await gateway.transform_request(request)
        
        # TODO: Make actual request to LLM service
        # For now, return mock response
        mock_response = {
            "status": "success",
            "gateway": gateway_name,
            "path": path,
            "request": transformed_request
        }
        
        # Transform response
        return await gateway.transform_response(mock_response)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gateway error: {str(e)}"
        )
