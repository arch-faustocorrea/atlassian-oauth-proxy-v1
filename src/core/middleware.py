"""Custom middleware for the FastAPI application.

This module provides middleware for correlation ID tracking,
logging, rate limiting, and other cross-cutting concerns.
"""

import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
import structlog

from .exceptions import RateLimitError
from .config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)


class CorrelationIDMiddleware:
    """Middleware to add correlation ID to requests.
    
    This middleware generates a unique correlation ID for each request
    and makes it available throughout the request lifecycle.
    """
    
    def __init__(
        self,
        app: Callable[[Request], Awaitable[Response]],
        header_name: str = "X-Correlation-ID"
    ) -> None:
        """Initialize the middleware.
        
        Args:
            app: ASGI application.
            header_name: Header name for correlation ID.
        """
        self.app = app
        self.header_name = header_name
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID.
        
        Args:
            request: FastAPI request object.
            call_next: Next middleware/handler in chain.
            
        Returns:
            Response: FastAPI response object.
        """
        # Generate or extract correlation ID
        correlation_id = request.headers.get(
            self.header_name, str(uuid.uuid4())
        )
        
        # Bind correlation ID to structlog context
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        
        # Add to request state
        request.state.correlation_id = correlation_id
        
        try:
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id
            
            return response
        finally:
            # Clear context
            structlog.contextvars.clear_contextvars()


class LoggingMiddleware:
    """Middleware to log HTTP requests and responses.
    
    This middleware logs request and response information including
    timing, status codes, and other relevant details.
    """
    
    def __init__(self, app: Callable[[Request], Awaitable[Response]]) -> None:
        """Initialize the middleware.
        
        Args:
            app: ASGI application.
        """
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging.
        
        Args:
            request: FastAPI request object.
            call_next: Next middleware/handler in chain.
            
        Returns:
            Response: FastAPI response object.
        """
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None,
        )
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=f"{process_time:.4f}s",
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as exc:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log exception
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                process_time=f"{process_time:.4f}s",
                error=str(exc),
                exc_info=True,
            )
            
            raise


class RateLimitMiddleware:
    """Middleware to implement rate limiting.
    
    This is a simple in-memory rate limiter. For production use,
    consider using Redis or another distributed storage.
    """
    
    def __init__(
        self,
        app: Callable[[Request], Awaitable[Response]],
        calls: int = None,
        period: int = 60
    ) -> None:
        """Initialize the middleware.
        
        Args:
            app: ASGI application.
            calls: Number of calls allowed per period.
            period: Time period in seconds.
        """
        self.app = app
        self.calls = calls or settings.rate_limit_per_minute
        self.period = period
        self.clients = {}
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting.
        
        Args:
            request: FastAPI request object.
            call_next: Next middleware/handler in chain.
            
        Returns:
            Response: FastAPI response object.
        """
        # Skip rate limiting for health check
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Clean up old entries
        self._cleanup_old_entries(current_time)
        
        # Check rate limit
        if client_id not in self.clients:
            self.clients[client_id] = []
        
        client_calls = self.clients[client_id]
        
        # Remove old calls outside the time window
        client_calls[:] = [
            call_time for call_time in client_calls
            if current_time - call_time < self.period
        ]
        
        # Check if rate limit exceeded
        if len(client_calls) >= self.calls:
            retry_after = int(self.period - (current_time - client_calls[0])) + 1
            
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                calls=len(client_calls),
                limit=self.calls,
                period=self.period,
                retry_after=retry_after,
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        
        # Record this call
        client_calls.append(current_time)
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting.
        
        Args:
            request: FastAPI request object.
            
        Returns:
            str: Client identifier.
        """
        # Use X-Forwarded-For header if present (behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Use direct client IP
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old client entries.
        
        Args:
            current_time: Current timestamp.
        """
        # Remove clients with no recent calls
        clients_to_remove = []
        for client_id, calls in self.clients.items():
            # Remove old calls
            calls[:] = [
                call_time for call_time in calls
                if current_time - call_time < self.period
            ]
            # Mark client for removal if no recent calls
            if not calls:
                clients_to_remove.append(client_id)
        
        # Remove inactive clients
        for client_id in clients_to_remove:
            del self.clients[client_id]