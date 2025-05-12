"""Base protocol for framework adapters.

This module defines the protocol for framework adapters, which convert Arc Memory's
return types to framework-specific formats.
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar

from arc_memory.sdk.models import EntityDetails, GraphStatistics, QueryResult

# Type variable for the FrameworkAdapter protocol
T = TypeVar("T", bound="FrameworkAdapter")


class FrameworkAdapter(Protocol):
    """Protocol defining the interface for framework adapters.

    Framework adapters convert Arc Memory's return types to framework-specific formats,
    allowing seamless integration with various agent frameworks.
    """

    def get_name(self) -> str:
        """Return a unique name for this adapter.

        Returns:
            A string identifier for this adapter, e.g., "langchain", "openai".
        """
        ...

    def get_version(self) -> str:
        """Return the version of this adapter.

        Returns:
            The version string, e.g., "0.1.0".
        """
        ...

    def get_framework_name(self) -> str:
        """Return the name of the framework this adapter supports.

        Returns:
            The name of the framework, e.g., "LangChain", "OpenAI".
        """
        ...

    def get_framework_version(self) -> str:
        """Return the version of the framework this adapter supports.

        Returns:
            The version string, e.g., "0.1.0".
        """
        ...

    def convert_query_result(self, result: QueryResult) -> Any:
        """Convert a QueryResult to a framework-specific format.

        Args:
            result: The QueryResult to convert.

        Returns:
            The converted result in a framework-specific format.
        """
        ...

    def convert_entity_details(self, details: EntityDetails) -> Any:
        """Convert EntityDetails to a framework-specific format.

        Args:
            details: The EntityDetails to convert.

        Returns:
            The converted details in a framework-specific format.
        """
        ...

    def convert_graph_statistics(self, stats: GraphStatistics) -> Any:
        """Convert GraphStatistics to a framework-specific format.

        Args:
            stats: The GraphStatistics to convert.

        Returns:
            The converted statistics in a framework-specific format.
        """
        ...

    def create_tool(self, func: Callable, **kwargs) -> Any:
        """Create a framework-specific tool from an Arc Memory function.

        Args:
            func: The Arc Memory function to wrap.
            **kwargs: Additional arguments for tool creation.

        Returns:
            A framework-specific tool that wraps the Arc Memory function.
        """
        ...
