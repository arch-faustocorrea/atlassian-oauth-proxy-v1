"""Authentication router.

This module provides FastAPI routes for OAuth authentication,
token management, and user operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
import structlog

from core.monitoring import track_request
from models.auth import (
    AuthTokens,
    LoginRequest,
    LoginResponse,
    OAuthCallbackRequest,
    RefreshTokenRequest,
    TokenInfo,
    UserInfo,
)
from models.common import StatusResponse

from .dependencies import get_auth_service, get_current_user, require_auth, require_token
from .service import AuthService

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/login", response_model=LoginResponse, summary="Initiate OAuth login")
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Initiate OAuth login flow.
    
    This endpoint starts the OAuth 2.0 authorization flow with Atlassian.
    The client should redirect the user to the returned authorization URL.
    
    Args:
        request: Login request parameters.
        auth_service: Authentication service.
        
    Returns:
        LoginResponse: Authorization URL and state parameter.
    """
    try:
        response = await auth_service.initiate_login(request)
        
        logger.info(
            "OAuth login initiated",
            provider=request.provider.value,
            state=response.state,
        )
        
        return response
        
    except Exception as e:
        logger.error("Failed to initiate login", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate login",
        )


@router.get("/callback", summary="OAuth callback endpoint")
async def oauth_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Handle OAuth callback from Atlassian.
    
    This endpoint receives the authorization code from Atlassian's OAuth service
    and exchanges it for access and refresh tokens. On success, it redirects
    to the configured success URL with tokens. On error, it redirects to the
    error URL with error information.
    
    Args:
        code: Authorization code from OAuth provider.
        state: OAuth state parameter.
        error: OAuth error code.
        error_description: OAuth error description.
        auth_service: Authentication service.
        
    Returns:
        RedirectResponse: Redirect to success or error URL.
    """
    try:
        callback_request = OAuthCallbackRequest(
            code=code or "",
            state=state or "",
            error=error,
            error_description=error_description,
        )
        
        if error:
            logger.warning(
                "OAuth callback received error",
                error=error,
                error_description=error_description,
                state=state,
            )
            # In production, redirect to an error page with appropriate message
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth error: {error}",
            )
        
        if not code or not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters: code and state",
            )
        
        tokens = await auth_service.handle_callback(callback_request)
        
        logger.info(
            "OAuth callback processed successfully",
            state=state,
            has_refresh_token=bool(tokens.refresh_token),
        )
        
        # In a real application, you might want to:
        # 1. Set secure HTTP-only cookies with tokens
        # 2. Redirect to a success page in your frontend
        # 3. Pass tokens as secure query parameters
        
        # For now, return tokens as JSON response
        return {
            "success": True,
            "tokens": tokens.dict(),
            "message": "Authentication successful",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to handle OAuth callback", error=str(e), state=state)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process OAuth callback",
        )


@router.post("/refresh", response_model=AuthTokens, summary="Refresh access token")
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokens:
    """Refresh access token using refresh token.
    
    Args:
        request: Refresh token request.
        auth_service: Authentication service.
        
    Returns:
        AuthTokens: New access and refresh tokens.
    """
    try:
        tokens = await auth_service.refresh_token(request)
        
        logger.info("Token refreshed successfully")
        
        return tokens
        
    except Exception as e:
        logger.error("Failed to refresh token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token",
        )


@router.post("/logout", response_model=StatusResponse, summary="Logout user")
async def logout(
    revoke_all: bool = False,
    user_info: UserInfo = Depends(require_auth),
    token_info: TokenInfo = Depends(require_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> StatusResponse:
    """Logout user and revoke tokens.
    
    Args:
        revoke_all: Whether to revoke all user tokens.
        user_info: Current user information.
        token_info: Current token information.
        auth_service: Authentication service.
        
    Returns:
        StatusResponse: Logout status.
    """
    try:
        if revoke_all:
            revoked_count = await auth_service.revoke_user_tokens(user_info.user_id)
            message = f"All tokens revoked ({revoked_count} tokens)"
        else:
            # Just revoke current token
            success = await auth_service.revoke_token(token_info.token_id)
            message = "Current token revoked" if success else "Token not found"
        
        logger.info(
            "User logged out",
            user_id=user_info.user_id,
            revoke_all=revoke_all,
        )
        
        return StatusResponse(
            success=True,
            message=message,
        )
        
    except Exception as e:
        logger.error(
            "Failed to logout user",
            user_id=user_info.user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout",
        )


@router.get("/me", response_model=UserInfo, summary="Get current user info")
async def get_me(
    user_info: UserInfo = Depends(require_auth),
) -> UserInfo:
    """Get current user information.
    
    Args:
        user_info: Current user information.
        
    Returns:
        UserInfo: Current user information.
    """
    return user_info


@router.get("/token-info", response_model=TokenInfo, summary="Get current token info")
async def get_token_info(
    token_info: TokenInfo = Depends(require_token),
) -> TokenInfo:
    """Get current token information.
    
    Args:
        token_info: Current token information.
        
    Returns:
        TokenInfo: Current token information.
    """
    return token_info