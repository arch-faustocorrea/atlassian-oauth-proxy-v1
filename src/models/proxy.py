"""Proxy-related data models.

This module contains Pydantic models for proxy requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, validator

from .common import BaseModel, TimestampedModel


class HttpMethod(str, Enum):
    """HTTP method enumeration."""
    
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ProxyStatus(str, Enum):
    """Proxy request status enumeration."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ProxyRequest(BaseModel):
    """Proxy request model."""
    
    method: HttpMethod = Field(..., description="HTTP method")
    path: str = Field(..., description="Target path")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    query_params: Dict[str, Union[str, List[str]]] = Field(
        default_factory=dict, 
        description="Query parameters"
    )
    body: Optional[Union[str, bytes, Dict[str, Any]]] = Field(
        None, 
        description="Request body"
    )
    timeout: Optional[int] = Field(
        None, 
        ge=1, 
        le=300, 
        description="Request timeout in seconds"
    )
    retry_count: int = Field(
        default=0, 
        ge=0, 
        le=5, 
        description="Number of retry attempts"
    )
    follow_redirects: bool = Field(
        default=True, 
        description="Whether to follow redirects"
    )
    verify_ssl: bool = Field(
        default=True, 
        description="Whether to verify SSL certificates"
    )
    
    @validator("path")
    def validate_path(cls, v):
        """Validate request path."""
        if not v.startswith("/"):
            v = "/" + v
        return v
    
    @validator("headers")
    def normalize_headers(cls, v):
        """Normalize header names to lowercase."""
        return {key.lower(): value for key, value in v.items()}


class ProxyResponse(BaseModel):
    """Proxy response model."""
    
    status_code: int = Field(..., description="HTTP status code")
    headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    body: Optional[Union[str, bytes, Dict[str, Any]]] = Field(
        None, 
        description="Response body"
    )
    content_type: Optional[str] = Field(None, description="Content type")
    content_length: Optional[int] = Field(None, description="Content length")
    elapsed_time: float = Field(..., description="Request duration in seconds")
    retry_count: int = Field(default=0, description="Number of retries performed")
    
    @validator("headers")
    def normalize_headers(cls, v):
        """Normalize header names to lowercase."""
        return {key.lower(): value for key, value in v.items()}


class ProxyError(BaseModel):
    """Proxy error model."""
    
    error_type: str = Field(..., description="Error type")
    error_message: str = Field(..., description="Error message")
    status_code: Optional[int] = Field(None, description="HTTP status code if applicable")
    retry_count: int = Field(default=0, description="Number of retries performed")
    elapsed_time: float = Field(..., description="Time elapsed before error")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class ProxyMetrics(BaseModel):
    """Proxy request metrics model."""
    
    request_id: str = Field(..., description="Unique request identifier")
    target_url: str = Field(..., description="Target URL")
    method: HttpMethod = Field(..., description="HTTP method")
    status: ProxyStatus = Field(..., description="Request status")
    start_time: datetime = Field(..., description="Request start time")
    end_time: Optional[datetime] = Field(None, description="Request end time")
    duration: Optional[float] = Field(None, description="Request duration in seconds")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    request_size: Optional[int] = Field(None, description="Request size in bytes")
    response_size: Optional[int] = Field(None, description="Response size in bytes")
    retry_count: int = Field(default=0, description="Number of retries performed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    user_id: Optional[str] = Field(None, description="User who made the request")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    
    @property
    def is_completed(self) -> bool:
        """Check if request is completed."""
        return self.status in [ProxyStatus.COMPLETED, ProxyStatus.FAILED]
    
    @property
    def is_successful(self) -> bool:
        """Check if request was successful."""
        return (
            self.status == ProxyStatus.COMPLETED 
            and self.status_code 
            and 200 <= self.status_code < 400
        )


class ProxyConfiguration(BaseModel):
    """Proxy configuration model."""
    
    name: str = Field(..., description="Configuration name")
    target_base_url: str = Field(..., description="Target base URL")
    default_timeout: int = Field(default=30, description="Default timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    retry_backoff: float = Field(default=1.0, description="Retry backoff multiplier")
    allowed_methods: List[HttpMethod] = Field(
        default_factory=lambda: list(HttpMethod),
        description="Allowed HTTP methods"
    )
    blocked_paths: List[str] = Field(
        default_factory=list,
        description="Blocked path patterns"
    )
    required_headers: List[str] = Field(
        default_factory=list,
        description="Required headers for requests"
    )
    header_transformations: Dict[str, str] = Field(
        default_factory=dict,
        description="Header name transformations"
    )
    rate_limit: Optional[int] = Field(
        None,
        description="Rate limit per minute"
    )
    enable_caching: bool = Field(
        default=False,
        description="Whether to enable response caching"
    )
    cache_ttl: int = Field(
        default=300,
        description="Cache TTL in seconds"
    )
    
    @validator("target_base_url")
    def validate_target_url(cls, v):
        """Validate target base URL."""
        return v.rstrip("/")


class BatchProxyRequest(BaseModel):
    """Batch proxy request model."""
    
    requests: List[ProxyRequest] = Field(
        ..., 
        min_items=1, 
        max_items=10, 
        description="List of proxy requests"
    )
    parallel: bool = Field(
        default=True, 
        description="Whether to execute requests in parallel"
    )
    fail_fast: bool = Field(
        default=False, 
        description="Whether to stop on first failure"
    )
    timeout: Optional[int] = Field(
        None, 
        description="Overall timeout for batch request"
    )


class BatchProxyResponse(BaseModel):
    """Batch proxy response model."""
    
    responses: List[Union[ProxyResponse, ProxyError]] = Field(
        ..., 
        description="List of responses or errors"
    )
    successful_count: int = Field(..., description="Number of successful requests")
    failed_count: int = Field(..., description="Number of failed requests")
    total_duration: float = Field(..., description="Total batch duration in seconds")
    parallel_execution: bool = Field(..., description="Whether requests were executed in parallel")