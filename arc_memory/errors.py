"""Error classes for Arc Memory."""

from typing import Any, Dict, Optional


class ArcError(Exception):
    """Base class for all Arc Memory errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the error.

        Args:
            message: The error message.
            details: Additional details about the error.
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class GitHubAuthError(ArcError):
    """Error raised when GitHub authentication fails."""

    pass


class GraphBuildError(ArcError):
    """Error raised when building the graph fails."""

    pass


class GraphQueryError(ArcError):
    """Error raised when querying the graph fails."""

    pass


class ConfigError(ArcError):
    """Error raised when there's an issue with configuration."""

    pass


class IngestError(ArcError):
    """Error raised during data ingestion."""

    pass


class ADRParseError(IngestError):
    """Error raised when parsing ADRs fails."""

    pass


class GitError(IngestError):
    """Error raised when interacting with Git fails."""

    pass
