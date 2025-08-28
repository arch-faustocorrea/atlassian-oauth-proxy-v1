"""Proxy module.

This module provides request proxying functionality to forward
authenticated requests to MCP servers.
"""

from .service import ProxyService
from .client import MCPClient
from .router import router

__all__ = [
    "ProxyService",
    "MCPClient",
    "router",
]