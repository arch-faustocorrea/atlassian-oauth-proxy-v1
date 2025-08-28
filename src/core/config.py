"""Application configuration management.

This module provides configuration management using Pydantic settings
with environment variable support.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.
    
    All settings can be overridden using environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application settings
    app_name: str = Field(default="Atlassian OAuth Proxy", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    workers: int = Field(default=4, description="Number of worker processes")
    reload: bool = Field(default=False, description="Enable auto-reload")
    
    # Security settings
    secret_key: str = Field(..., description="Secret key for JWT signing")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration in days")
    
    # Atlassian OAuth settings
    atlassian_client_id: str = Field(..., description="Atlassian OAuth client ID")
    atlassian_client_secret: str = Field(..., description="Atlassian OAuth client secret")
    atlassian_redirect_uri: str = Field(..., description="OAuth redirect URI")
    atlassian_scopes: str = Field(
        default="read:jira-work,read:jira-user,read:confluence-content.all",
        description="OAuth scopes"
    )
    atlassian_auth_url: str = Field(
        default="https://auth.atlassian.com/authorize",
        description="Atlassian authorization URL"
    )
    atlassian_token_url: str = Field(
        default="https://auth.atlassian.com/oauth/token",
        description="Atlassian token URL"
    )
    atlassian_api_url: str = Field(
        default="https://api.atlassian.com",
        description="Atlassian API base URL"
    )
    
    # MCP server settings
    mcp_server_url: str = Field(..., description="MCP server URL")
    mcp_server_timeout: int = Field(default=30, description="MCP server request timeout in seconds")
    mcp_server_max_retries: int = Field(default=3, description="Maximum retries for MCP server requests")
    
    # Database settings
    database_url: str = Field(
        default="sqlite:///./oauth_proxy.db",
        description="Database connection URL"
    )
    database_echo: bool = Field(default=False, description="Enable SQLAlchemy echo")
    
    # Redis settings (optional)
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_max_size: str = Field(default="10MB", description="Maximum log file size")
    log_backup_count: int = Field(default=5, description="Number of backup log files")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed CORS methods"
    )
    cors_allow_headers: List[str] = Field(default=["*"], description="Allowed CORS headers")
    
    # Rate limiting settings
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")
    rate_limit_burst: int = Field(default=10, description="Rate limit burst")
    
    # Monitoring settings
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    health_check_enabled: bool = Field(default=True, description="Enable health check endpoint")
    prometheus_port: int = Field(default=8001, description="Prometheus metrics port")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("cors_allow_methods", pre=True)
    def parse_cors_methods(cls, v):
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v
    
    @validator("cors_allow_headers", pre=True)
    def parse_cors_headers(cls, v):
        """Parse CORS headers from string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()
    
    @validator("log_format")
    def validate_log_format(cls, v):
        """Validate log format."""
        allowed = ["json", "text"]
        if v not in allowed:
            raise ValueError(f"Log format must be one of {allowed}")
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    @property
    def atlassian_scopes_list(self) -> List[str]:
        """Get Atlassian scopes as a list."""
        return [scope.strip() for scope in self.atlassian_scopes.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings.
    
    Returns:
        Settings: Application settings instance.
    """
    return Settings()