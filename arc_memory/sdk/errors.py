"""Error classes for Arc Memory SDK.

This module provides error classes for the Arc Memory SDK, allowing for
consistent error handling and reporting.
"""

from typing import Any, Dict, Optional

from arc_memory.errors import ArcError


class SDKError(ArcError):
    """Base class for all SDK errors.

    This class extends the base ArcError class to provide consistent error
    handling for the SDK.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the error.

        Args:
            message: The error message.
            details: Additional details about the error.
        """
        super().__init__(message, details)


class AdapterError(SDKError):
    """Error raised when there's an issue with an adapter.

    This error is raised when there's an issue with a database or framework adapter,
    such as initialization failures or connection issues.
    """

    pass


class QueryError(SDKError):
    """Error raised when querying the knowledge graph fails.

    This error is raised when a query to the knowledge graph fails, such as
    when a node or edge cannot be found or when the query syntax is invalid.
    """

    pass


class BuildError(SDKError):
    """Error raised when building the knowledge graph fails.

    This error is raised when building or modifying the knowledge graph fails,
    such as when adding nodes or edges fails.
    """

    pass


class ConfigError(SDKError):
    """Error raised when there's an issue with configuration.

    This error is raised when there's an issue with the SDK configuration,
    such as invalid configuration values or missing required configuration.
    """

    pass


class FrameworkError(SDKError):
    """Error raised when there's an issue with a framework integration.

    This error is raised when there's an issue with a framework integration,
    such as incompatible framework versions or missing dependencies.
    """

    pass
