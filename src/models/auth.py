"""Authentication-related data models.

This module contains Pydantic models for authentication,
OAuth flows, and token management.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import Field, validator, EmailStr

from .common import BaseModel, TimestampedModel


class TokenType(str, Enum):
    """Token type enumeration."""
    
    ACCESS = "access"
    REFRESH = "refresh"
    ID = "id"


class AuthProvider(str, Enum):
    """Authentication provider enumeration."""
    
    ATLASSIAN = "atlassian"


class OAuthState(str, Enum):
    """OAuth flow state enumeration."""
    
    INITIATED = "initiated"
    AUTHORIZED = "authorized"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class AuthTokens(BaseModel):
    """Authentication tokens model."""
    
    access_token: str = Field(..., description="Access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    id_token: Optional[str] = Field(None, description="ID token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token expiration in seconds")
    scope: Optional[str] = Field(None, description="Token scope")
    expires_at: Optional[datetime] = Field(None, description="Token expiration timestamp")
    
    @validator("token_type")
    def validate_token_type(cls, v):
        """Validate token type."""
        return v.lower()


class TokenInfo(TimestampedModel):
    """Token information model."""
    
    token_id: str = Field(..., description="Unique token identifier")
    user_id: str = Field(..., description="User identifier")
    token_type: TokenType = Field(..., description="Token type")
    provider: AuthProvider = Field(..., description="Authentication provider")
    scope: List[str] = Field(default_factory=list, description="Token scopes")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    revoked: bool = Field(default=False, description="Whether token is revoked")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    client_info: Optional[Dict[str, str]] = Field(None, description="Client information")
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return not self.revoked and not self.is_expired


class UserInfo(TimestampedModel):
    """User information model."""
    
    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User full name")
    display_name: Optional[str] = Field(None, description="User display name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    locale: Optional[str] = Field(None, description="User locale")
    timezone: Optional[str] = Field(None, description="User timezone")
    provider: AuthProvider = Field(..., description="Authentication provider")
    provider_id: str = Field(..., description="Provider-specific user ID")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Additional user metadata")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    is_active: bool = Field(default=True, description="Whether user is active")


class LoginRequest(BaseModel):
    """Login request model."""
    
    provider: AuthProvider = Field(default=AuthProvider.ATLASSIAN, description="Authentication provider")
    redirect_uri: Optional[str] = Field(None, description="Custom redirect URI")
    state: Optional[str] = Field(None, description="OAuth state parameter")
    scopes: Optional[List[str]] = Field(None, description="Requested scopes")


class LoginResponse(BaseModel):
    """Login response model."""
    
    auth_url: str = Field(..., description="Authorization URL to redirect to")
    state: str = Field(..., description="OAuth state parameter")
    expires_in: int = Field(default=600, description="State expiration in seconds")


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request model."""
    
    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="OAuth state parameter")
    error: Optional[str] = Field(None, description="OAuth error code")
    error_description: Optional[str] = Field(None, description="OAuth error description")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    
    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Logout request model."""
    
    revoke_all: bool = Field(default=False, description="Revoke all user tokens")


class OAuthSession(TimestampedModel):
    """OAuth session model for tracking flows."""
    
    session_id: str = Field(..., description="Unique session identifier")
    state: str = Field(..., description="OAuth state parameter")
    provider: AuthProvider = Field(..., description="Authentication provider")
    status: OAuthState = Field(default=OAuthState.INITIATED, description="Session status")
    redirect_uri: str = Field(..., description="Redirect URI")
    requested_scopes: List[str] = Field(default_factory=list, description="Requested scopes")
    granted_scopes: Optional[List[str]] = Field(None, description="Granted scopes")
    user_id: Optional[str] = Field(None, description="User ID after successful auth")
    client_info: Optional[Dict[str, str]] = Field(None, description="Client information")
    expires_at: datetime = Field(..., description="Session expiration timestamp")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_description: Optional[str] = Field(None, description="Error description if failed")
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return (
            self.status in [OAuthState.INITIATED, OAuthState.AUTHORIZED]
            and not self.is_expired
        )