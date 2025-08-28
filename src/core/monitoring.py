"""Monitoring and metrics collection.

This module provides Prometheus metrics collection and monitoring
functionality for the application.
"""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from prometheus_client import Counter, Histogram, Info, Summary
import structlog

logger = structlog.get_logger(__name__)

# Prometheus metrics
request_count = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"]
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

auth_attempts = Counter(
    "auth_attempts_total",
    "Total number of authentication attempts",
    ["type", "status"]
)

proxy_requests = Counter(
    "proxy_requests_total",
    "Total number of proxy requests",
    ["target", "status"]
)

proxy_duration = Histogram(
    "proxy_request_duration_seconds",
    "Proxy request duration in seconds",
    ["target"]
)

oauth_flows = Counter(
    "oauth_flows_total",
    "Total number of OAuth flows",
    ["provider", "status"]
)

external_service_requests = Counter(
    "external_service_requests_total",
    "Total requests to external services",
    ["service", "status_code"]
)

external_service_duration = Histogram(
    "external_service_request_duration_seconds",
    "External service request duration in seconds",
    ["service"]
)

active_tokens = Counter(
    "active_tokens_total",
    "Total number of active tokens",
    ["type"]
)

error_count = Counter(
    "errors_total",
    "Total number of errors",
    ["type", "component"]
)

# Application info
app_info = Info(
    "app_info",
    "Application information"
)


def setup_monitoring() -> None:
    """Setup monitoring and metrics collection."""
    logger.info("Setting up monitoring")
    
    # Set application info
    app_info.info({
        "version": "1.0.0",
        "name": "atlassian-oauth-proxy",
    })


def track_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """Track HTTP request metrics.
    
    Args:
        method: HTTP method.
        endpoint: Request endpoint.
        status_code: Response status code.
        duration: Request duration in seconds.
    """
    request_count.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code
    ).inc()
    
    request_duration.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


def track_auth_attempt(auth_type: str, status: str) -> None:
    """Track authentication attempt.
    
    Args:
        auth_type: Type of authentication (oauth, token, etc.).
        status: Status (success, failure, error).
    """
    auth_attempts.labels(type=auth_type, status=status).inc()


def track_proxy_request(target: str, status: str, duration: Optional[float] = None) -> None:
    """Track proxy request metrics.
    
    Args:
        target: Proxy target.
        status: Request status.
        duration: Request duration in seconds.
    """
    proxy_requests.labels(target=target, status=status).inc()
    
    if duration is not None:
        proxy_duration.labels(target=target).observe(duration)


def track_oauth_flow(provider: str, status: str) -> None:
    """Track OAuth flow metrics.
    
    Args:
        provider: OAuth provider (atlassian, etc.).
        status: Flow status (started, completed, failed).
    """
    oauth_flows.labels(provider=provider, status=status).inc()


def track_external_service(service: str, status_code: int, duration: float) -> None:
    """Track external service request metrics.
    
    Args:
        service: Service name.
        status_code: HTTP status code.
        duration: Request duration in seconds.
    """
    external_service_requests.labels(
        service=service,
        status_code=status_code
    ).inc()
    
    external_service_duration.labels(service=service).observe(duration)


def track_active_token(token_type: str, increment: bool = True) -> None:
    """Track active token count.
    
    Args:
        token_type: Type of token (access, refresh).
        increment: Whether to increment or decrement.
    """
    if increment:
        active_tokens.labels(type=token_type).inc()
    else:
        # Note: Counter doesn't have dec(), so we'd need a Gauge for this
        # For now, we'll just track increments
        pass


def track_error(error_type: str, component: str) -> None:
    """Track error occurrence.
    
    Args:
        error_type: Type of error.
        component: Component where error occurred.
    """
    error_count.labels(type=error_type, component=component).inc()


def monitor_function(component: str):
    """Decorator to monitor function execution.
    
    Args:
        component: Component name for metrics.
        
    Returns:
        Callable: Decorated function.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                track_error(type(e).__name__, component)
                raise
            finally:
                duration = time.time() - start_time
                logger.debug(
                    "Function execution completed",
                    function=func.__name__,
                    component=component,
                    duration=f"{duration:.4f}s"
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                track_error(type(e).__name__, component)
                raise
            finally:
                duration = time.time() - start_time
                logger.debug(
                    "Function execution completed",
                    function=func.__name__,
                    component=component,
                    duration=f"{duration:.4f}s"
                )
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class MetricsCollector:
    """Metrics collection context manager."""
    
    def __init__(self, operation: str, component: str):
        """Initialize metrics collector.
        
        Args:
            operation: Operation name.
            component: Component name.
        """
        self.operation = operation
        self.component = component
        self.start_time = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and record metrics."""
        if self.start_time:
            duration = time.time() - self.start_time
            
            if exc_type:
                track_error(exc_type.__name__, self.component)
                logger.error(
                    "Operation failed",
                    operation=self.operation,
                    component=self.component,
                    duration=f"{duration:.4f}s",
                    error=str(exc_val),
                )
            else:
                logger.debug(
                    "Operation completed",
                    operation=self.operation,
                    component=self.component,
                    duration=f"{duration:.4f}s",
                )