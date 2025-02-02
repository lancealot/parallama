"""Rate limiting middleware for API gateways."""

from datetime import datetime
from typing import Callable, Optional
from uuid import UUID

import redis

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from starlette.datastructures import State, MutableHeaders

from ..core.database import get_db
from ..services.rate_limit import RateLimitService

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for enforcing rate limits on API requests."""

    def __init__(
        self,
        app: ASGIApp,
        get_user_id: Callable[[Request], Optional[UUID]],
        get_gateway_type: Callable[[Request], str]
    ):
        """Initialize the rate limit middleware.
        
        Args:
            app: The ASGI application
            get_user_id: Function to extract user ID from request
            get_gateway_type: Function to determine gateway type from request
        """
        super().__init__(app)
        self.get_user_id = get_user_id
        self.get_gateway_type = get_gateway_type

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and apply rate limiting.
        
        Args:
            request: The incoming request
            call_next: Function to call the next middleware/endpoint
            
        Returns:
            The response from the next middleware/endpoint
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        # Initialize request state
        request.state.start_time = datetime.utcnow().timestamp()
        request.state.tokens_used = None
        request.state.model_name = None
        request.state.error_message = None
        request.state.status_code = None
        request.state.gateway_type = None

        # Skip rate limiting for non-API routes
        if not request.url.path.startswith(("/ollama/", "/openai/")):
            return await call_next(request)

        user_id = self.get_user_id(request)
        if not user_id:
            return await call_next(request)

        gateway_type = self.get_gateway_type(request)
        request.state.gateway_type = gateway_type

        # Initialize rate limit service
        db = next(get_db())
        rate_limit_service = RateLimitService(db)

        try:
            # Check rate limits before processing
            try:
                await rate_limit_service.check_rate_limit(
                    user_id=user_id,
                    gateway_type=gateway_type,
                    tokens=request.state.tokens_used
                )
            except redis.ConnectionError:
                error_message = "Rate limiting service unavailable"
                await rate_limit_service.record_usage(
                    user_id=user_id,
                    gateway_type=gateway_type,
                    endpoint=request.url.path,
                    tokens=request.state.tokens_used,
                    model_name=request.state.model_name,
                    duration=0,
                    status_code=503,
                    error_message=error_message
                )
                return JSONResponse(
                    status_code=503,
                    content={"detail": error_message}
                )
            except HTTPException as e:
                await rate_limit_service.record_usage(
                    user_id=user_id,
                    gateway_type=gateway_type,
                    endpoint=request.url.path,
                    tokens=request.state.tokens_used,
                    model_name=request.state.model_name,
                    duration=0,
                    status_code=e.status_code,
                    error_message=str(e.detail)
                )
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )

            # Process the request
            try:
                response = await call_next(request)
                request.state.end_time = datetime.utcnow().timestamp()
                duration = int((request.state.end_time - request.state.start_time) * 1000)

                # If there's an error message, override the response
                if request.state.error_message:
                    status_code = request.state.status_code or 500
                    await rate_limit_service.record_usage(
                        user_id=user_id,
                        gateway_type=gateway_type,
                        endpoint=request.url.path,
                        tokens=request.state.tokens_used,
                        model_name=request.state.model_name,
                        duration=duration,
                        status_code=status_code,
                        error_message=request.state.error_message
                    )
                    return JSONResponse(
                        status_code=status_code,
                        content={"detail": request.state.error_message}
                    )

                # Record successful usage
                await rate_limit_service.record_usage(
                    user_id=user_id,
                    gateway_type=gateway_type,
                    endpoint=request.url.path,
                    tokens=request.state.tokens_used,
                    model_name=request.state.model_name,
                    duration=duration,
                    status_code=response.status_code,
                    error_message=request.state.error_message
                )

                return response

            except Exception as e:
                # Record error
                error_message = str(e)
                status_code = 500
                if isinstance(e, HTTPException):
                    status_code = e.status_code
                    error_message = e.detail

                await rate_limit_service.record_usage(
                    user_id=user_id,
                    gateway_type=gateway_type,
                    endpoint=request.url.path,
                    tokens=request.state.tokens_used,
                    model_name=request.state.model_name,
                    duration=int((datetime.utcnow().timestamp() - request.state.start_time) * 1000),
                    status_code=status_code,
                    error_message=error_message
                )

                return JSONResponse(
                    status_code=status_code,
                    content={"detail": error_message}
                )

        finally:
            try:
                rate_limit_service.close()
            except:
                pass
            db.close()

            # Clean up request state
            for attr in [
                'start_time', 'end_time', 'tokens_used',
                'model_name', 'error_message', 'status_code',
                'gateway_type'
            ]:
                if hasattr(request.state, attr):
                    delattr(request.state, attr)

    @staticmethod
    def get_gateway_type_from_path(request: Request) -> str:
        """Extract gateway type from request path.
        
        Args:
            request: The incoming request
            
        Returns:
            The gateway type (e.g., 'ollama' or 'openai')
        """
        if request.url.path.startswith("/ollama/"):
            return "ollama"
        elif request.url.path.startswith("/openai/"):
            return "openai"
        return "unknown"

    async def cleanup(self):
        """Cleanup resources when the application shuts down."""
        try:
            db = next(get_db())
            rate_limit_service = RateLimitService(db)
            await rate_limit_service.cleanup()
            rate_limit_service.close()
            db.close()
        except:
            pass
