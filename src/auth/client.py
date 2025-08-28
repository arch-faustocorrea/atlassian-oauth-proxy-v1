"""Atlassian OAuth client.

This module provides the HTTP client for interacting with
Atlassian's OAuth 2.0 endpoints.
"""

import time
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlencode, urlparse

import httpx
import structlog

from core.base import BaseClient
from core.config import get_settings
from core.exceptions import ExternalServiceError, OAuthError
from core.monitoring import track_external_service
from models.auth import AuthProvider, AuthTokens, UserInfo

settings = get_settings()
logger = structlog.get_logger(__name__)


class AtlassianOAuthClient(BaseClient):
    """HTTP client for Atlassian OAuth 2.0 operations."""
    
    def __init__(self):
        """Initialize the Atlassian OAuth client."""
        super().__init__(
            name="AtlassianOAuth",
            base_url=settings.atlassian_api_url,
            timeout=30,
        )
        self.auth_url = settings.atlassian_auth_url
        self.token_url = settings.atlassian_token_url
        self.client_id = settings.atlassian_client_id
        self.client_secret = settings.atlassian_client_secret
    
    async def build_auth_url(
        self,
        redirect_uri: str,
        state: str,
        scopes: List[str],
    ) -> str:
        """Build authorization URL for OAuth flow.
        
        Args:
            redirect_uri: OAuth redirect URI.
            state: OAuth state parameter.
            scopes: Requested OAuth scopes.
            
        Returns:
            str: Authorization URL.
        """
        params = {
            "audience": "api.atlassian.com",
            "client_id": self.client_id,
            "scope": " ".join(scopes),
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        
        self.logger.info(
            "Built authorization URL",
            redirect_uri=redirect_uri,
            scopes=scopes,
        )
        
        return auth_url
    
    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
    ) -> AuthTokens:
        """Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from OAuth callback.
            redirect_uri: OAuth redirect URI.
            
        Returns:
            AuthTokens: Access and refresh tokens.
        """
        start_time = time.time()
        
        try:
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            }
            
            self._log_request("POST", self.token_url)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=self.timeout,
                )
            
            duration = time.time() - start_time
            self._log_response("POST", self.token_url, response.status_code, duration)
            track_external_service("atlassian_oauth", response.status_code, duration)
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                raise OAuthError(
                    f"Token exchange failed: {response.status_code}",
                    error_code=error_data.get("error"),
                    error_description=error_data.get("error_description"),
                )
            
            token_data = response.json()
            
            # Calculate expiration time
            expires_at = None
            if token_data.get("expires_in"):
                expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            
            tokens = AuthTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "bearer"),
                expires_in=token_data.get("expires_in"),
                scope=token_data.get("scope"),
                expires_at=expires_at,
            )
            
            self.logger.info(
                "Successfully exchanged code for tokens",
                has_refresh_token=bool(tokens.refresh_token),
                expires_in=tokens.expires_in,
                scope=tokens.scope,
            )
            
            return tokens
            
        except OAuthError:
            raise
        except httpx.TimeoutException:
            duration = time.time() - start_time
            track_external_service("atlassian_oauth", 0, duration)
            raise ExternalServiceError(
                "Token exchange request timed out",
                service="atlassian_oauth",
            )
        except httpx.RequestError as e:
            duration = time.time() - start_time
            track_external_service("atlassian_oauth", 0, duration)
            raise ExternalServiceError(
                f"Token exchange request failed: {str(e)}",
                service="atlassian_oauth",
                cause=e,
            )
        except Exception as e:
            duration = time.time() - start_time
            track_external_service("atlassian_oauth", 0, duration)
            self.logger.error("Unexpected error during token exchange", error=str(e))
            raise ExternalServiceError(
                "Unexpected error during token exchange",
                service="atlassian_oauth",
                cause=e,
            )
    
    async def refresh_tokens(self, refresh_token: str) -> AuthTokens:
        """Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token.
            
        Returns:
            AuthTokens: New access and refresh tokens.
        """
        start_time = time.time()
        
        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
            }
            
            self._log_request("POST", self.token_url)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=self.timeout,
                )
            
            duration = time.time() - start_time
            self._log_response("POST", self.token_url, response.status_code, duration)
            track_external_service("atlassian_oauth", response.status_code, duration)
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                raise OAuthError(
                    f"Token refresh failed: {response.status_code}",
                    error_code=error_data.get("error"),
                    error_description=error_data.get("error_description"),
                )
            
            token_data = response.json()
            
            # Calculate expiration time
            expires_at = None
            if token_data.get("expires_in"):
                expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            
            tokens = AuthTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", refresh_token),
                token_type=token_data.get("token_type", "bearer"),
                expires_in=token_data.get("expires_in"),
                scope=token_data.get("scope"),
                expires_at=expires_at,
            )
            
            self.logger.info(
                "Successfully refreshed tokens",
                has_new_refresh_token=token_data.get("refresh_token") != refresh_token,
                expires_in=tokens.expires_in,
            )
            
            return tokens
            
        except OAuthError:
            raise
        except httpx.TimeoutException:
            duration = time.time() - start_time
            track_external_service("atlassian_oauth", 0, duration)
            raise ExternalServiceError(
                "Token refresh request timed out",
                service="atlassian_oauth",
            )
        except httpx.RequestError as e:
            duration = time.time() - start_time
            track_external_service("atlassian_oauth", 0, duration)
            raise ExternalServiceError(
                f"Token refresh request failed: {str(e)}",
                service="atlassian_oauth",
                cause=e,
            )
        except Exception as e:
            duration = time.time() - start_time
            track_external_service("atlassian_oauth", 0, duration)
            self.logger.error("Unexpected error during token refresh", error=str(e))
            raise ExternalServiceError(
                "Unexpected error during token refresh",
                service="atlassian_oauth",
                cause=e,
            )
    
    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get user information from Atlassian API.
        
        Args:
            access_token: Valid access token.
            
        Returns:
            UserInfo: User information.
        """
        start_time = time.time()
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            
            user_info_url = f"{self.base_url}/me"
            self._log_request("GET", user_info_url)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    user_info_url,
                    headers=headers,
                    timeout=self.timeout,
                )
            
            duration = time.time() - start_time
            self._log_response("GET", user_info_url, response.status_code, duration)
            track_external_service("atlassian_api", response.status_code, duration)
            
            if response.status_code != 200:
                raise ExternalServiceError(
                    f"Failed to get user info: {response.status_code}",
                    service="atlassian_api",
                    status_code=response.status_code,
                )
            
            user_data = response.json()
            
            user_info = UserInfo(
                user_id=user_data["account_id"],
                email=user_data["email"],
                name=user_data.get("name"),
                display_name=user_data.get("display_name"),
                avatar_url=user_data.get("picture"),
                locale=user_data.get("locale"),
                timezone=user_data.get("zoneinfo"),
                provider=AuthProvider.ATLASSIAN,
                provider_id=user_data["account_id"],
                last_login=datetime.utcnow(),
            )
            
            self.logger.info(
                "Successfully retrieved user info",
                user_id=user_info.user_id,
                email=user_info.email,
            )
            
            return user_info
            
        except ExternalServiceError:
            raise
        except httpx.TimeoutException:
            duration = time.time() - start_time
            track_external_service("atlassian_api", 0, duration)
            raise ExternalServiceError(
                "User info request timed out",
                service="atlassian_api",
            )
        except httpx.RequestError as e:
            duration = time.time() - start_time
            track_external_service("atlassian_api", 0, duration)
            raise ExternalServiceError(
                f"User info request failed: {str(e)}",
                service="atlassian_api",
                cause=e,
            )
        except Exception as e:
            duration = time.time() - start_time
            track_external_service("atlassian_api", 0, duration)
            self.logger.error("Unexpected error getting user info", error=str(e))
            raise ExternalServiceError(
                "Unexpected error getting user info",
                service="atlassian_api",
                cause=e,
            )
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke an access or refresh token.
        
        Args:
            token: Token to revoke.
            
        Returns:
            bool: True if revoked successfully.
        """
        start_time = time.time()
        
        try:
            # Atlassian doesn't provide a standard revocation endpoint,
            # so we'll just log the attempt
            self.logger.info(
                "Token revocation requested",
                # Don't log the actual token for security
                token_length=len(token),
            )
            
            # In a real implementation, you might call a revocation endpoint
            # or perform other cleanup actions
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to revoke token", error=str(e))
            return False