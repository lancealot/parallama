from typing import Dict, Any, List
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
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
        
        # Transform request
        transformed_request = await gateway.transform_request(request)
        
        # In test mode, skip the actual HTTP request
        if hasattr(gateway, '_test_mode'):
            return await gateway.transform_response(transformed_request)
        
        # Forward request to LLM service
        async with httpx.AsyncClient() as client:
            try:
                # Check if this is a streaming request
                is_streaming = transformed_request.get("stream", False)
                
                # Make request to LLM service
                response = await client.post(
                    f"{gateway.base_url}/{path}",
                    json=transformed_request,
                    headers={"Content-Type": "application/json"},
                    timeout=60.0  # Longer timeout for LLM requests
                )
                
                # Handle errors
                if response.status_code >= 400:
                    error_data = await response.json()
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_data.get("error", "LLM service error")
                    )
                
                # Handle streaming response
                if is_streaming:
                    return StreamingResponse(
                        response.aiter_lines(),
                        media_type="text/event-stream",
                        headers={"Cache-Control": "no-cache"}
                    )
                
                # Transform non-streaming response
                response_data = await response.json()
                return await gateway.transform_response(response_data)
                
            except httpx.ReadTimeout:
                raise HTTPException(
                    status_code=504,
                    detail="Request to LLM service timed out"
                )
            except (httpx.ConnectError, httpx.RequestError) as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to connect to LLM service: {str(e)}"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gateway error: {str(e)}"
        )
