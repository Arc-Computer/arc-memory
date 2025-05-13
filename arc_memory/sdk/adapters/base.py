"""Base protocol for framework adapters.

This module defines the protocol for framework adapters, which adapt Arc Memory's
functions to specific agent frameworks (LangChain, OpenAI, etc.).
"""

from typing import Any, Callable, List, Protocol, TypeVar

# Type variable for the FrameworkAdapter protocol
T = TypeVar("T", bound="FrameworkAdapter")


class FrameworkAdapter(Protocol):
    """Protocol defining the interface for framework adapters.

    Framework adapters are responsible for adapting Arc Memory functions to
    specific agent frameworks (LangChain, OpenAI, etc.).
    """

    def get_name(self) -> str:
        """Return a unique name for this adapter.

        Returns:
            A string identifier for this adapter, e.g., "langchain", "openai".
        """
        ...

    def get_supported_versions(self) -> List[str]:
        """Return a list of supported framework versions.

        Returns:
            A list of version strings, e.g., ["0.1.0", "0.2.0"].
        """
        ...

    def adapt_functions(self, functions: List[Callable]) -> Any:
        """Adapt Arc Memory functions to the framework's format.

        Args:
            functions: List of functions to adapt.

        Returns:
            Framework-specific representation of the functions.
        """
        ...

    def create_agent(self, **kwargs) -> Any:
        """Create an agent using the framework.

        Args:
            **kwargs: Framework-specific parameters for creating an agent.

        Returns:
            A framework-specific agent instance.
        """
        ...
