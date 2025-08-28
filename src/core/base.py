"""Base classes and utilities.

This module provides base classes and common utilities used throughout
the application.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar

import structlog

T = TypeVar("T")
logger = structlog.get_logger(__name__)


class BaseService(ABC):
    """Base service class.
    
    All service classes should inherit from this base class to ensure
    consistent behavior and logging.
    """
    
    def __init__(self, name: Optional[str] = None) -> None:
        """Initialize the service.
        
        Args:
            name: Service name for logging.
        """
        self.name = name or self.__class__.__name__
        self.logger = structlog.get_logger(self.name)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.startup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
    
    async def startup(self) -> None:
        """Service startup hook.
        
        Override this method to perform service initialization.
        """
        self.logger.info(f"{self.name} service starting up")
    
    async def shutdown(self) -> None:
        """Service shutdown hook.
        
        Override this method to perform service cleanup.
        """
        self.logger.info(f"{self.name} service shutting down")


class BaseRepository(ABC, Generic[T]):
    """Base repository class.
    
    Provides common CRUD operations interface that can be implemented
    by concrete repository classes.
    """
    
    def __init__(self, entity_name: str) -> None:
        """Initialize the repository.
        
        Args:
            entity_name: Name of the entity for logging.
        """
        self.entity_name = entity_name
        self.logger = structlog.get_logger(f"{entity_name}Repository")
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity.
        
        Args:
            entity: Entity to create.
            
        Returns:
            T: Created entity.
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID.
        
        Args:
            entity_id: Entity ID.
            
        Returns:
            Optional[T]: Entity if found, None otherwise.
        """
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> Optional[T]:
        """Update an entity.
        
        Args:
            entity_id: Entity ID.
            updates: Fields to update.
            
        Returns:
            Optional[T]: Updated entity if found, None otherwise.
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity.
        
        Args:
            entity_id: Entity ID.
            
        Returns:
            bool: True if deleted, False if not found.
        """
        pass
    
    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List entities with pagination.
        
        Args:
            limit: Maximum number of entities to return.
            offset: Number of entities to skip.
            
        Returns:
            list[T]: List of entities.
        """
        pass


class BaseClient(ABC):
    """Base HTTP client class.
    
    Provides common functionality for HTTP clients with error handling,
    retries, and monitoring.
    """
    
    def __init__(self, name: str, base_url: str, timeout: int = 30) -> None:
        """Initialize the client.
        
        Args:
            name: Client name for logging.
            base_url: Base URL for the service.
            timeout: Request timeout in seconds.
        """
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = structlog.get_logger(f"{name}Client")
    
    def _build_url(self, path: str) -> str:
        """Build full URL from path.
        
        Args:
            path: URL path.
            
        Returns:
            str: Full URL.
        """
        path = path.lstrip("/")
        return f"{self.base_url}/{path}"
    
    def _log_request(self, method: str, url: str, **kwargs) -> None:
        """Log outgoing request.
        
        Args:
            method: HTTP method.
            url: Request URL.
            **kwargs: Additional request parameters.
        """
        self.logger.info(
            "Outgoing request",
            method=method,
            url=url,
            timeout=self.timeout,
        )
    
    def _log_response(self, method: str, url: str, status_code: int, duration: float) -> None:
        """Log response.
        
        Args:
            method: HTTP method.
            url: Request URL.
            status_code: Response status code.
            duration: Request duration in seconds.
        """
        self.logger.info(
            "Response received",
            method=method,
            url=url,
            status_code=status_code,
            duration=f"{duration:.4f}s",
        )


class SingletonMeta(type):
    """Singleton metaclass.
    
    Ensures only one instance of a class is created.
    """
    
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        """Create or return existing instance."""
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class ConfigurableService(BaseService):
    """Base class for configurable services.
    
    Provides configuration injection and validation.
    """
    
    def __init__(self, config: Dict[str, Any], name: Optional[str] = None) -> None:
        """Initialize the service with configuration.
        
        Args:
            config: Service configuration.
            name: Service name for logging.
        """
        super().__init__(name)
        self.config = config
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate service configuration.
        
        Override this method to implement configuration validation.
        """
        required_keys = self.get_required_config_keys()
        missing_keys = [key for key in required_keys if key not in self.config]
        
        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {missing_keys}")
    
    def get_required_config_keys(self) -> list[str]:
        """Get list of required configuration keys.
        
        Override this method to specify required configuration keys.
        
        Returns:
            list[str]: List of required configuration keys.
        """
        return []
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key.
            default: Default value if key not found.
            
        Returns:
            Any: Configuration value.
        """
        return self.config.get(key, default)


class Factory(ABC, Generic[T]):
    """Base factory class.
    
    Implements the Factory pattern for creating objects.
    """
    
    @abstractmethod
    def create(self, **kwargs) -> T:
        """Create an instance.
        
        Args:
            **kwargs: Creation parameters.
            
        Returns:
            T: Created instance.
        """
        pass


class AsyncContextManager(ABC):
    """Base async context manager."""
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass