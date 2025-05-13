"""Error classes for Arc Memory SDK.

This module provides error classes for the Arc Memory SDK, allowing for
consistent error handling and reporting. It follows a standardized approach
to error messages with the format:

[What happened] + [Why it happened] + [How to fix it]

This makes errors more actionable and helps users understand and resolve issues.
"""

import inspect
import os
from typing import Any, Dict, Optional, Type

from arc_memory.errors import ArcError


def format_error_message(
    what_happened: str,
    why_it_happened: str,
    how_to_fix_it: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Format an error message following the standard pattern.

    This helper function creates a consistent error message format that includes:
    1. What happened (the error description)
    2. Why it happened (the cause)
    3. How to fix it (the solution)

    It also adds context information about where the error occurred.

    Args:
        what_happened: A description of the error that occurred.
        why_it_happened: An explanation of why the error occurred.
        how_to_fix_it: Instructions on how to fix the error.
        context: Optional additional context information.

    Returns:
        A formatted error message string.
    """
    # Get caller information
    frame = inspect.currentframe().f_back
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno
    function = frame.f_code.co_name

    # Format the base message
    message = f"{what_happened}. {why_it_happened}. {how_to_fix_it}."

    # Add location context
    location = f"{os.path.basename(filename)}:{lineno} in {function}()"

    # Add any additional context
    context_str = ""
    if context:
        context_str = " | " + ", ".join(f"{k}={v}" for k, v in context.items())

    # Combine everything
    return f"{message} [Location: {location}{context_str}]"


class SDKError(ArcError):
    """Base class for all SDK errors.

    This class extends the base ArcError class to provide consistent error
    handling for the SDK. It follows the standard error message format:
    [What happened] + [Why it happened] + [How to fix it]

    All SDK errors should inherit from this class to ensure consistent
    error handling and reporting.
    """

    def __init__(
        self,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        what_happened: Optional[str] = None,
        why_it_happened: Optional[str] = None,
        how_to_fix_it: Optional[str] = None
    ) -> None:
        """Initialize the error.

        Args:
            message: The error message. If what_happened, why_it_happened, and
                how_to_fix_it are provided, this will be overridden with a
                formatted message. Default is an empty string.
            details: Additional details about the error.
            what_happened: A description of the error that occurred.
            why_it_happened: An explanation of why the error occurred.
            how_to_fix_it: Instructions on how to fix the error.
        """
        if all([what_happened, why_it_happened, how_to_fix_it]):
            message = format_error_message(
                what_happened=what_happened,
                why_it_happened=why_it_happened,
                how_to_fix_it=how_to_fix_it,
                context=details
            )

        super().__init__(message, details)

    @classmethod
    def from_exception(
        cls: Type["SDKError"],
        exception: Exception,
        what_happened: str,
        how_to_fix_it: str,
        details: Optional[Dict[str, Any]] = None
    ) -> "SDKError":
        """Create an SDKError from another exception.

        This helper method creates an SDKError (or subclass) from another exception,
        adding context about what happened and how to fix it.

        Args:
            exception: The original exception.
            what_happened: A description of the error that occurred.
            how_to_fix_it: Instructions on how to fix the error.
            details: Additional details about the error.

        Returns:
            A new SDKError instance.
        """
        why_it_happened = f"Caused by: {type(exception).__name__}: {str(exception)}"

        return cls(
            message="",  # Will be overridden by format_error_message
            details=details,
            what_happened=what_happened,
            why_it_happened=why_it_happened,
            how_to_fix_it=how_to_fix_it
        )


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


class ExportSDKError(SDKError):
    """Error raised when exporting the knowledge graph fails.

    This error is raised when exporting the knowledge graph fails, such as
    when writing to the output file fails or when signing the export fails.
    """

    pass
