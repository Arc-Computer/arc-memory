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

    def get(self, name: str) -> Optional[FrameworkAdapter]:
        """Get a framework adapter by name.

        Args:
            name: The name of the adapter to get.

        Returns:
            The adapter instance, or None if not found.
        """
        return self.adapters.get(name)

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

    @classmethod
    def discover(cls) -> "AdapterRegistry":
        """Discover and register all available adapters.

        Returns:
            A registry containing all discovered adapters.
        """
        registry = cls()

        # Discover adapters from entry points
        try:
            # Python 3.10+ syntax
            entry_points = importlib.metadata.entry_points(group="arc_memory.plugins.frameworks")
        except TypeError:
            # Python 3.8-3.9 fallback
            entry_points = importlib.metadata.entry_points().get("arc_memory.plugins.frameworks", [])

        for entry_point in entry_points:
            try:
                adapter_class = entry_point.load()
                adapter_instance = adapter_class()
                registry.register(adapter_instance)
                logger.info(f"Loaded framework adapter: {entry_point.name}")
            except Exception as e:
                logger.warning(f"Failed to load framework adapter {entry_point.name}: {e}")

        return registry


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
    adapter = _registry.get(name)
    if adapter is None:
        raise AdapterError(f"Adapter '{name}' not found")
    return adapter


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
    # Discover adapters using the AdapterRegistry.discover method
    discovered_registry = AdapterRegistry.discover()

    # Register all discovered adapters with the global registry
    for adapter in discovered_registry.get_all():
        try:
            _registry.register(adapter)
        except AdapterError:
            # Skip adapters that are already registered
            pass

    return _registry.get_all()
