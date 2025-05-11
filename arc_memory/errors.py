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

    def __str__(self) -> str:
        """Return a string representation of the error.

        Returns:
            A string with the error message and details if available.
        """
        if not self.details:
            return self.message

        details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
        return f"{self.message} ({details_str})"


class GitHubAuthError(ArcError):
    """Error raised when GitHub authentication fails."""

    pass


class LinearAuthError(ArcError):
    """Error raised when Linear authentication fails."""

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


class DependencyError(ArcError):
    """Error raised when a required dependency is missing."""

    pass


class DatabaseError(ArcError):
    """Error raised when there's an issue with the database."""

    pass


class DatabaseNotFoundError(DatabaseError):
    """Error raised when the database file is not found."""

    pass


class DatabaseInitializationError(DatabaseError):
    """Error raised when initializing the database fails."""

    pass


class ExportError(ArcError):
    """Error raised when exporting the graph fails."""

    pass


class AutoRefreshError(ArcError):
    """Error raised when auto-refresh operations fail."""

    pass
