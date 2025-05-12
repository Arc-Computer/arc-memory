"""Registry for framework adapters.

This module provides a registry for framework adapters, allowing discovery and
management of adapters for different agent frameworks.
"""

import importlib.metadata
from typing import Any, Dict, List, Optional, Type

from arc_memory.logging_conf import get_logger
from arc_memory.sdk.adapters.base import FrameworkAdapter
from arc_memory.sdk.errors import AdapterError

logger = get_logger(__name__)


class AdapterRegistry:
    """Registry for framework adapters.

    This class provides a registry for framework adapters, allowing discovery and
    management of adapters for different agent frameworks.
    """

    def __init__(self):
        """Initialize the adapter registry."""
        self.adapters: Dict[str, FrameworkAdapter] = {}

    def register(self, adapter: FrameworkAdapter) -> None:
        """Register a framework adapter.

        Args:
            adapter: The adapter to register.

        Raises:
            AdapterError: If an adapter with the same name is already registered.
        """
        name = adapter.get_name()
        if name in self.adapters:
            raise AdapterError(f"Adapter '{name}' is already registered")
        self.adapters[name] = adapter
        logger.debug(f"Registered adapter: {name}")

    def get(self, name: str) -> FrameworkAdapter:
        """Get a framework adapter by name.

        Args:
            name: The name of the adapter to get.

        Returns:
            The adapter instance.

        Raises:
            AdapterError: If the adapter is not found.
        """
        if name not in self.adapters:
            raise AdapterError(f"Adapter '{name}' not found")
        return self.adapters[name]

    def get_all(self) -> List[FrameworkAdapter]:
        """Get all registered adapters.

        Returns:
            A list of all registered adapter instances.
        """
        return list(self.adapters.values())

    def get_names(self) -> List[str]:
        """Get the names of all registered adapters.

        Returns:
            A list of adapter names.
        """
        return list(self.adapters.keys())


# Global registry instance
_registry = AdapterRegistry()


def register_adapter(adapter: FrameworkAdapter) -> None:
    """Register a framework adapter.

    Args:
        adapter: The adapter to register.

    Raises:
        AdapterError: If an adapter with the same name is already registered.
    """
    _registry.register(adapter)


def get_adapter(name: str) -> FrameworkAdapter:
    """Get a framework adapter by name.

    Args:
        name: The name of the adapter to get.

    Returns:
        The adapter instance.

    Raises:
        AdapterError: If the adapter is not found.
    """
    return _registry.get(name)


def get_all_adapters() -> List[FrameworkAdapter]:
    """Get all registered adapters.

    Returns:
        A list of all registered adapter instances.
    """
    return _registry.get_all()


def get_adapter_names() -> List[str]:
    """Get the names of all registered adapters.

    Returns:
        A list of adapter names.
    """
    return _registry.get_names()


def discover_adapters() -> List[FrameworkAdapter]:
    """Discover and register all available adapters.

    This function discovers adapters from entry points and registers them
    with the global registry.

    Returns:
        A list of discovered adapter instances.
    """
    # This will be implemented in a future PR
    # For now, return an empty list
    return []
