"""Rate limiting middleware for API gateways."""

from datetime import datetime
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from starlette.datastructures import State

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
        # Initialize request state if not present
        if not hasattr(request, "state"):
            request.state = State()

        # Skip rate limiting for non-API routes
        if not request.url.path.startswith(("/ollama/", "/openai/")):
            return await call_next(request)

        user_id = self.get_user_id(request)
        if not user_id:
            return await call_next(request)

        gateway_type = self.get_gateway_type(request)
        start_time = getattr(request.state, "start_time", datetime.utcnow().timestamp())
        request.state.start_time = start_time

        # Initialize rate limit service
        db = next(get_db())
        rate_limit_service = RateLimitService(db)

        try:
            # Check rate limits before processing
            tokens = getattr(request.state, "tokens_used", None)
            print(f"\nMiddleware Rate Limit Check:")
            print(f"User ID: {user_id}")
            print(f"Gateway Type: {gateway_type}")
            print(f"Tokens: {tokens}")
            print(f"Path: {request.url.path}")
            print(f"State attributes: {dir(request.state)}")
            try:
                await rate_limit_service.check_rate_limit(
                    user_id=user_id,
                    gateway_type=gateway_type,
                    tokens=tokens
                )
            except HTTPException as e:
                # Record the rate limit exceeded event
                await rate_limit_service.record_usage(
                    user_id=user_id,
                    gateway_type=gateway_type,
                    endpoint=request.url.path,
                    tokens=tokens,
                    status_code=e.status_code,
                    error_message=str(e.detail)
                )
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )

            try:
                # Process the request
                response = await call_next(request)

                # Record usage after processing
                end_time = getattr(request.state, "end_time", datetime.utcnow().timestamp())
                request.state.end_time = end_time
                duration = int((end_time - start_time) * 1000)  # Convert to milliseconds

                error_message = getattr(request.state, "error_message", None)
                status_code = response.status_code
                print(f"\nMiddleware Recording Usage:")
                print(f"Tokens: {tokens}")
                print(f"Status Code: {status_code}")
                print(f"Duration: {duration}ms")

                # If there's an error message, override the response
                if error_message:
                    status_code = getattr(request.state, "status_code", 500)
                    response = JSONResponse(
                        status_code=status_code,
                        content={"detail": error_message}
                    )

                # Record usage
                await rate_limit_service.record_usage(
                    user_id=user_id,
                    gateway_type=gateway_type,
                    endpoint=request.url.path,
                    tokens=tokens,
                    model_name=getattr(request.state, "model_name", None),
                    duration=duration,
                    status_code=status_code,
                    error_message=error_message
                )

                return response

            except Exception as e:
                # Record error and re-raise
                error_message = str(e)
                status_code = 500
                if isinstance(e, HTTPException):
                    status_code = e.status_code
                    error_message = e.detail

                await rate_limit_service.record_usage(
                    user_id=user_id,
                    gateway_type=gateway_type,
                    endpoint=request.url.path,
                    status_code=status_code,
                    error_message=error_message
                )

                # Re-raise as HTTPException if it's not already one
                if not isinstance(e, HTTPException):
                    raise HTTPException(
                        status_code=status_code,
                        detail=error_message
                    ) from e
                raise

        except Exception as e:
            # Handle any uncaught exceptions
            if isinstance(e, HTTPException):
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": str(e.detail)}
                )
            return JSONResponse(
                status_code=500,
                content={"detail": str(e)}
            )

        finally:
            try:
                rate_limit_service.close()
            except:
                pass
            db.close()

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
