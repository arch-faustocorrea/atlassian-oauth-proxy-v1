"""Authentication module.

This module provides OAuth 2.0 authentication with Atlassian,
token management, and user session handling.
"""

from .service import AuthService
from .client import AtlassianOAuthClient
from .dependencies import get_current_user, get_auth_service, require_auth
from .router import router

__all__ = [
    "AuthService",
    "AtlassianOAuthClient", 
    "get_current_user",
    "get_auth_service",
    "require_auth",
    "router",
]