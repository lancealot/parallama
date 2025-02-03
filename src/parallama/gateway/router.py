"""Gateway router for handling API requests."""

import json
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

from . import GatewayType, GatewayRegistry
from ..core.exceptions import GatewayError

router = APIRouter(tags=["gateway"])

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
        "timestamp": datetime.utcnow().isoformat()
    }

@router.api_route("/{gateway_type}/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_request(
    gateway_type: str,
    path: str,
    request: Request
) -> Response:
    print(f"DEBUG: Received request for gateway_type={gateway_type}, path={path}")
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
    gateway = GatewayRegistry.get_gateway(gateway_type)
    if not gateway:
        raise HTTPException(
            status_code=404,
            detail=f"Gateway '{gateway_type}' not found"
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
        
        # Check for test mode
        if "_test_mode" in request.headers:
            transformed_request["_test_mode"] = True
            return await gateway.transform_response(transformed_request)
        
        # Forward request to LLM service
        async with httpx.AsyncClient() as client:
            try:
                # Check if this is a streaming request
                is_streaming = transformed_request.get("stream", False)
                
                # Determine the method and endpoint
                method = request.method.lower()
                endpoint = f"{gateway.ollama_url}/{path}"
                
                print(f"DEBUG: Gateway URL base: {gateway.ollama_url}")
                print(f"DEBUG: Request path: {path}")
                print(f"DEBUG: Full endpoint URL: {endpoint}")
                print(f"DEBUG: Making {method.upper()} request")
                
                # Make request to LLM service
                response = await client.request(
                    method,
                    endpoint,
                    json=transformed_request if method in ["post", "put"] else None,
                    headers={"Content-Type": "application/json"},
                    timeout=60.0  # Longer timeout for LLM requests
                )
                
                print(f"DEBUG: Response status: {response.status_code}")
                print(f"DEBUG: Response content: {response.text}")
                
                # Handle errors
                response.raise_for_status()
                
                # Handle streaming response
                if is_streaming:
                    async def stream_generator():
                        async for line in response.aiter_lines():
                            if line.strip():
                                try:
                                    chunk = json.loads(line)
                                    yield f"data: {json.dumps(chunk)}\n\n"
                                except json.JSONDecodeError:
                                    continue
                    
                    return StreamingResponse(
                        stream_generator(),
                        media_type="text/event-stream",
                        headers={"Cache-Control": "no-cache"}
                    )
                
                # Transform non-streaming response
                try:
                    # Fix malformed JSON by replacing missing commas
                    text = response.text.replace('""', '","')
                    text = text.replace('"}{"', '"},{"')
                    response_data = json.loads(text)
                    print(f"DEBUG: Parsed JSON: {json.dumps(response_data, indent=2)}")
                    return await gateway.transform_response(response_data)
                except json.JSONDecodeError as e:
                    print(f"DEBUG: JSON parse error: {str(e)}")
                    return await gateway.handle_error(e)
                
            except httpx.ReadTimeout:
                return await gateway.handle_error(httpx.ReadTimeout("Request to LLM service timed out"))
            except httpx.ConnectError as e:
                return await gateway.handle_error(httpx.ConnectError(f"Failed to connect to LLM service: {str(e)}"))
            except httpx.HTTPStatusError as e:
                return await gateway.handle_error(e)
            except Exception as e:
                return await gateway.handle_error(e)
            
    except HTTPException:
        raise
    except Exception as e:
        if hasattr(gateway, 'handle_error'):
            return await gateway.handle_error(e)
        raise HTTPException(
            status_code=500,
            detail=f"Gateway error: {str(e)}"
        )
