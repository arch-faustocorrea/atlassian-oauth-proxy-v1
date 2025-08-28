"""Pydantic models for the application.

This module contains all data models used throughout the application
for request/response validation and serialization.
"""

from .auth import (
    AuthTokens,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenInfo,
    UserInfo,
)
from .proxy import ProxyRequest, ProxyResponse
from .common import BaseModel, ErrorResponse, HealthResponse

__all__ = [
    # Auth models
    "AuthTokens",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "TokenInfo",
    "UserInfo",
    # Proxy models
    "ProxyRequest",
    "ProxyResponse",
    # Common models
    "BaseModel",
    "ErrorResponse",
    "HealthResponse",
]