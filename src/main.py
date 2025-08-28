"""FastAPI application entry point.

This module sets up the FastAPI application with all necessary middleware,
routers, and configuration.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
import structlog

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from auth.router import router as auth_router
from core.config import get_settings
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
    ValidationError,
)
from core.logging import setup_logging
from core.middleware import (
    CorrelationIDMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
)
from core.monitoring import setup_monitoring
from proxy.router import router as proxy_router

# Initialize settings
settings = get_settings()

# Setup logging
setup_logging(settings)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Atlassian OAuth Proxy", version=settings.app_version)
    
    # Setup monitoring
    setup_monitoring()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Atlassian OAuth Proxy")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="A secure OAuth proxy service for Atlassian integrations",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )
    
    # Add security middleware
    if settings.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure appropriately for production
        )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Add custom middleware
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Add routers
    app.include_router(auth_router, prefix="/auth", tags=["authentication"])
    app.include_router(proxy_router, prefix="/proxy", tags=["proxy"])
    
    # Add exception handlers
    add_exception_handlers(app)
    
    # Add health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.app_version}
    
    # Add metrics endpoint if enabled
    if settings.metrics_enabled:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
    
    return app


def add_exception_handlers(app: FastAPI) -> None:
    """Add global exception handlers to the FastAPI app.
    
    Args:
        app: FastAPI application instance.
    """
    
    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        """Handle authentication errors."""
        logger.warning(
            "Authentication error",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc), "type": "authentication_error"},
        )
    
    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(
        request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        """Handle authorization errors."""
        logger.warning(
            "Authorization error",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "type": "authorization_error"},
        )
    
    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle validation errors."""
        logger.warning(
            "Validation error",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc), "type": "validation_error"},
        )
    
    @app.exception_handler(ExternalServiceError)
    async def external_service_error_handler(
        request: Request, exc: ExternalServiceError
    ) -> JSONResponse:
        """Handle external service errors."""
        logger.error(
            "External service error",
            error=str(exc),
            path=request.url.path,
            service=getattr(exc, 'service', 'unknown'),
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "External service error", "type": "external_service_error"},
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected errors."""
        logger.exception(
            "Unhandled exception",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "type": "internal_error"},
        )


# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=1 if settings.reload else settings.workers,
        log_level=settings.log_level.lower(),
    )