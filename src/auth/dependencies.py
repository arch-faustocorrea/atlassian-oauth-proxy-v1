"""Authentication dependencies for FastAPI.

This module provides dependency injection for authentication,
including user validation and service access.
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import structlog

from core.exceptions import AuthenticationError, TokenError
from models.auth import TokenInfo, UserInfo

from .service import AuthService

security = HTTPBearer(auto_error=False)
logger = structlog.get_logger(__name__)

# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the authentication service instance.
    
    Returns:
        AuthService: Authentication service instance.
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


async def get_current_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[TokenInfo]:
    """Get current token information from request.
    
    Args:
        request: FastAPI request object.
        credentials: Bearer token credentials.
        auth_service: Authentication service.
        
    Returns:
        Optional[TokenInfo]: Token information if valid, None otherwise.
    """
    if not credentials:
        return None
    
    try:
        token_info = await auth_service.validate_token(credentials.credentials)
        
        # Bind user context for logging
        structlog.contextvars.bind_contextvars(
            user_id=token_info.user_id,
            token_type=token_info.token_type.value,
        )
        
        return token_info
        
    except (AuthenticationError, TokenError) as e:
        logger.warning(
            "Token validation failed",
            error=str(e),
            path=request.url.path,
        )
        return None
    except Exception as e:
        logger.error(
            "Unexpected error during token validation",
            error=str(e),
            path=request.url.path,
        )
        return None


async def get_current_user(
    request: Request,
    token_info: Optional[TokenInfo] = Depends(get_current_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[UserInfo]:
    """Get current user information from request.
    
    Args:
        request: FastAPI request object.
        token_info: Token information.
        auth_service: Authentication service.
        
    Returns:
        Optional[UserInfo]: User information if authenticated, None otherwise.
    """
    if not token_info:
        return None
    
    try:
        user_info = await auth_service.get_user_info(token_info.user_id)
        
        if user_info and user_info.is_active:
            # Bind additional user context for logging
            structlog.contextvars.bind_contextvars(
                user_email=user_info.email,
                user_name=user_info.display_name or user_info.name,
            )
            return user_info
        
        return None
        
    except Exception as e:
        logger.error(
            "Failed to get user info",
            user_id=token_info.user_id,
            error=str(e),
            path=request.url.path,
        )
        return None


async def require_auth(
    request: Request,
    user_info: Optional[UserInfo] = Depends(get_current_user),
) -> UserInfo:
    """Require authentication for endpoint access.
    
    Args:
        request: FastAPI request object.
        user_info: User information from token.
        
    Returns:
        UserInfo: User information.
        
    Raises:
        HTTPException: If user is not authenticated.
    """
    if not user_info:
        logger.warning(
            "Unauthorized access attempt",
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info


async def require_token(
    request: Request,
    token_info: Optional[TokenInfo] = Depends(get_current_token),
) -> TokenInfo:
    """Require valid token for endpoint access.
    
    Args:
        request: FastAPI request object.
        token_info: Token information.
        
    Returns:
        TokenInfo: Token information.
        
    Raises:
        HTTPException: If token is not valid.
    """
    if not token_info:
        logger.warning(
            "Invalid or missing token",
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_info


def require_scopes(*required_scopes: str):
    """Create a dependency that requires specific OAuth scopes.
    
    Args:
        *required_scopes: Required OAuth scopes.
        
    Returns:
        Callable: Dependency function.
    """
    async def check_scopes(
        request: Request,
        token_info: TokenInfo = Depends(require_token),
    ) -> TokenInfo:
        """Check if token has required scopes.
        
        Args:
            request: FastAPI request object.
            token_info: Token information.
            
        Returns:
            TokenInfo: Token information.
            
        Raises:
            HTTPException: If required scopes are missing.
        """
        missing_scopes = set(required_scopes) - set(token_info.scope)
        
        if missing_scopes:
            logger.warning(
                "Insufficient scopes",
                user_id=token_info.user_id,
                required_scopes=list(required_scopes),
                token_scopes=token_info.scope,
                missing_scopes=list(missing_scopes),
                path=request.url.path,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient scopes. Missing: {', '.join(missing_scopes)}",
            )
        
        return token_info
    
    return check_scopes


async def optional_auth(
    request: Request,
    user_info: Optional[UserInfo] = Depends(get_current_user),
) -> Optional[UserInfo]:
    """Optional authentication dependency.
    
    Args:
        request: FastAPI request object.
        user_info: User information if authenticated.
        
    Returns:
        Optional[UserInfo]: User information if authenticated, None otherwise.
    """
    return user_info