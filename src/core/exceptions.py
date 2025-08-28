"""Custom exception classes.

This module defines custom exceptions used throughout the application.
"""

from typing import Any, Dict, Optional


class BaseAppException(Exception):
    """Base exception class for the application.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Error message.
            details: Additional error details.
            cause: Underlying exception that caused this error.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
    
    def __str__(self) -> str:
        """String representation of the exception."""
        return self.message
    
    def __repr__(self) -> str:
        """Detailed representation of the exception."""
        return f"{self.__class__.__name__}('{self.message}', details={self.details})"


class ConfigurationError(BaseAppException):
    """Raised when there's a configuration error."""
    pass


class AuthenticationError(BaseAppException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(BaseAppException):
    """Raised when authorization fails."""
    pass


class ValidationError(BaseAppException):
    """Raised when data validation fails."""
    pass


class ExternalServiceError(BaseAppException):
    """Raised when external service call fails.
    
    Attributes:
        service: Name of the external service.
        status_code: HTTP status code if applicable.
    """
    
    def __init__(
        self,
        message: str,
        service: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Error message.
            service: Name of the external service.
            status_code: HTTP status code if applicable.
            details: Additional error details.
            cause: Underlying exception that caused this error.
        """
        super().__init__(message, details, cause)
        self.service = service
        self.status_code = status_code


class TokenError(AuthenticationError):
    """Raised when there's an issue with tokens.
    
    Attributes:
        token_type: Type of token (access, refresh, etc.).
    """
    
    def __init__(
        self,
        message: str,
        token_type: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Error message.
            token_type: Type of token.
            details: Additional error details.
            cause: Underlying exception that caused this error.
        """
        super().__init__(message, details, cause)
        self.token_type = token_type


class OAuthError(AuthenticationError):
    """Raised when OAuth flow fails.
    
    Attributes:
        error_code: OAuth error code.
        error_description: OAuth error description.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        error_description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Error message.
            error_code: OAuth error code.
            error_description: OAuth error description.
            details: Additional error details.
            cause: Underlying exception that caused this error.
        """
        super().__init__(message, details, cause)
        self.error_code = error_code
        self.error_description = error_description


class ProxyError(ExternalServiceError):
    """Raised when proxy request fails.
    
    Attributes:
        target_url: The target URL that failed.
        method: HTTP method used.
    """
    
    def __init__(
        self,
        message: str,
        target_url: str,
        method: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Error message.
            target_url: The target URL that failed.
            method: HTTP method used.
            status_code: HTTP status code if applicable.
            details: Additional error details.
            cause: Underlying exception that caused this error.
        """
        super().__init__(message, "proxy", status_code, details, cause)
        self.target_url = target_url
        self.method = method


class RateLimitError(BaseAppException):
    """Raised when rate limit is exceeded.
    
    Attributes:
        limit: Rate limit value.
        window: Rate limit window in seconds.
        retry_after: Seconds to wait before retrying.
    """
    
    def __init__(
        self,
        message: str,
        limit: int,
        window: int,
        retry_after: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Error message.
            limit: Rate limit value.
            window: Rate limit window in seconds.
            retry_after: Seconds to wait before retrying.
            details: Additional error details.
        """
        super().__init__(message, details)
        self.limit = limit
        self.window = window
        self.retry_after = retry_after