"""Logging configuration and utilities.

This module provides structured logging using structlog with support for
JSON and text formats.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict

import structlog
from structlog.types import FilteringBoundLogger, Processor

from .config import Settings


def setup_logging(settings: Settings) -> None:
    """Setup structured logging configuration.
    
    Args:
        settings: Application settings.
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )
    
    # Setup log file handler if specified
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Parse log max size
        max_bytes = _parse_size(settings.log_max_size)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, settings.log_level))
        
        # Add file handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]
    
    if settings.log_format == "json":
        processors.extend([
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ])
    else:
        processors.extend([
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.dev.ConsoleRenderer(),
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _parse_size(size_str: str) -> int:
    """Parse size string to bytes.
    
    Args:
        size_str: Size string like '10MB', '1GB', etc.
        
    Returns:
        int: Size in bytes.
    """
    size_str = size_str.upper().strip()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)


class CorrelationIDProcessor:
    """Processor to add correlation ID to log records."""
    
    def __init__(self, key: str = "correlation_id") -> None:
        """Initialize the processor.
        
        Args:
            key: Key name for the correlation ID.
        """
        self.key = key
    
    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add correlation ID to event dict.
        
        Args:
            logger: Logger instance.
            method_name: Log method name.
            event_dict: Event dictionary.
            
        Returns:
            Dict[str, Any]: Updated event dictionary.
        """
        # Try to get correlation ID from context variables
        correlation_id = structlog.contextvars.get_contextvars().get(self.key)
        if correlation_id:
            event_dict[self.key] = correlation_id
        return event_dict


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name.
        
    Returns:
        FilteringBoundLogger: Configured logger instance.
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to the current context.
    
    Args:
        **kwargs: Key-value pairs to bind.
    """
    for key, value in kwargs.items():
        structlog.contextvars.bind_contextvars(**{key: value})


def clear_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()


def with_correlation_id(correlation_id: str) -> None:
    """Bind correlation ID to the current context.
    
    Args:
        correlation_id: Correlation ID to bind.
    """
    bind_context(correlation_id=correlation_id)