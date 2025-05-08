"""Plugin architecture for Arc Memory.

This module provides the plugin interface and registry for extending Arc Memory
with additional data sources beyond Git, GitHub, and ADRs.
"""

import importlib.metadata
from typing import Any, Dict, List, Optional, Protocol, TypeVar
from pathlib import Path

from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import Edge, Node

logger = get_logger(__name__)

# Type variable for the IngestorPlugin protocol
T = TypeVar("T", bound="IngestorPlugin")


class IngestorPlugin(Protocol):
    """Protocol defining the interface for ingestor plugins.

    Ingestor plugins are responsible for ingesting data from a specific source
    (e.g., Git, GitHub, ADRs) and converting it into nodes and edges in the
    knowledge graph.
    """

    def get_name(self) -> str:
        """Return a unique name for this plugin.

        Returns:
            A string identifier for this plugin, e.g., "git", "github", "adr".
        """
        ...

    def get_node_types(self) -> List[str]:
        """Return a list of node types this plugin can create.

        Returns:
            A list of node type identifiers, e.g., ["commit", "file"].
        """
        ...

    def get_edge_types(self) -> List[str]:
        """Return a list of edge types this plugin can create.

        Returns:
            A list of edge type identifiers, e.g., ["MODIFIES", "MERGES"].
        """
        ...

    def ingest(self, last_processed: Optional[Dict[str, Any]] = None) -> tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest data from the source and return nodes, edges, and metadata.

        Args:
            last_processed: Optional dictionary containing metadata from the previous run,
                            used for incremental ingestion.

        Returns:
            A tuple containing:
            - List[Node]: List of nodes created from the data source
            - List[Edge]: List of edges created from the data source
            - Dict[str, Any]: Metadata about the ingestion process, used for incremental builds
        """
        ...


class IngestorRegistry:
    """Registry for ingestor plugins.

    The registry manages the discovery and registration of plugins, and provides
    methods for retrieving plugins by name or type.
    """

    def __init__(self):
        """Initialize an empty registry."""
        self.ingestors: Dict[str, IngestorPlugin] = {}

    def register(self, ingestor: IngestorPlugin) -> None:
        """Register a plugin with the registry.

        Args:
            ingestor: An instance of a class implementing the IngestorPlugin protocol.
        """
        name = ingestor.get_name()
        if name in self.ingestors:
            logger.warning(f"Overwriting existing plugin with name '{name}'")
        self.ingestors[name] = ingestor
        logger.debug(f"Registered plugin: {name}")

    def get(self, name: str) -> Optional[IngestorPlugin]:
        """Get a plugin by name.

        Args:
            name: The name of the plugin to retrieve.

        Returns:
            The plugin instance, or None if not found.
        """
        return self.ingestors.get(name)

    def list_plugins(self) -> List[str]:
        """List all registered plugins.

        Returns:
            A list of plugin names.
        """
        return list(self.ingestors.keys())

    def get_all(self) -> List[IngestorPlugin]:
        """Get all registered plugins.

        Returns:
            A list of plugin instances.
        """
        return list(self.ingestors.values())

    def get_by_node_type(self, node_type: str) -> List[IngestorPlugin]:
        """Get plugins that can create a specific node type.

        Args:
            node_type: The node type to look for.

        Returns:
            A list of plugin instances that can create the specified node type.
        """
        return [p for p in self.ingestors.values() if node_type in p.get_node_types()]

    def get_by_edge_type(self, edge_type: str) -> List[IngestorPlugin]:
        """Get plugins that can create a specific edge type.

        Args:
            edge_type: The edge type to look for.

        Returns:
            A list of plugin instances that can create the specified edge type.
        """
        return [p for p in self.ingestors.values() if edge_type in p.get_edge_types()]

    def remove_plugin(self, name: str) -> bool:
        """Remove a plugin from the registry.

        Args:
            name: The name of the plugin to remove.

        Returns:
            True if the plugin was removed, False if it wasn't found.
        """
        if name in self.ingestors:
            del self.ingestors[name]
            logger.debug(f"Removed plugin: {name}")
            return True
        return False


def discover_plugins() -> IngestorRegistry:
    """Discover and register all available plugins.

    This function discovers plugins from two sources:
    1. Built-in plugins (Git, GitHub, ADR)
    2. Third-party plugins registered via entry points

    Returns:
        An IngestorRegistry containing all discovered plugins.
    """
    registry = IngestorRegistry()

    # Register built-in plugins
    try:
        from arc_memory.ingest.git import GitIngestor
        registry.register(GitIngestor())
        logger.debug("Registered built-in plugin: git")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to load built-in plugin 'git': {e}")

    try:
        from arc_memory.ingest.github import GitHubIngestor
        registry.register(GitHubIngestor())
        logger.debug("Registered built-in plugin: github")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to load built-in plugin 'github': {e}")

    try:
        from arc_memory.ingest.adr import ADRIngestor
        registry.register(ADRIngestor())
        logger.debug("Registered built-in plugin: adr")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to load built-in plugin 'adr': {e}")

    try:
        from arc_memory.ingest.linear import LinearIngestor
        registry.register(LinearIngestor())
        logger.debug("Registered built-in plugin: linear")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to load built-in plugin 'linear': {e}")

    try:
        from arc_memory.ingest.code_analysis import CodeAnalysisIngestor
        registry.register(CodeAnalysisIngestor())
        logger.debug("Registered built-in plugin: code_analysis")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to load built-in plugin 'code_analysis': {e}")

    try:
        from arc_memory.ingest.change_patterns import ChangePatternIngestor
        registry.register(ChangePatternIngestor())
        logger.debug("Registered built-in plugin: change_patterns")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to load built-in plugin 'change_patterns': {e}")

    # Discover and register third-party plugins
    try:
        for entry_point in importlib.metadata.entry_points(group='arc_memory.plugins'):
            try:
                plugin_class = entry_point.load()
                plugin_instance = plugin_class()
                registry.register(plugin_instance)
                logger.info(f"Registered third-party plugin: {entry_point.name}")
            except Exception as e:
                logger.warning(f"Failed to load plugin {entry_point.name}: {e}")
    except Exception as e:
        logger.warning(f"Failed to discover third-party plugins: {e}")

    return registry


def get_plugin_config(plugin_name: str) -> Dict[str, Any]:
    """Get configuration for a specific plugin.

    Args:
        plugin_name: The name of the plugin.

    Returns:
        A dictionary containing the plugin's configuration.
    """
    # This is a placeholder for future implementation
    # In a real implementation, this would load configuration from a file
    # or environment variables
    return {}


def get_ingestor_plugins(repo_path: Optional[Path] = None) -> List[IngestorPlugin]:
    """Get ingestor plugins with repo_path configured.
    
    Args:
        repo_path: The path to the repository to analyze.
        
    Returns:
        A list of configured ingestor plugin instances.
    """
    # Use the discover_plugins function to get the registry
    registry = discover_plugins()
    
    # Filter out already directly instantiated plugins (git, github, adr, linear, etc.)
    # as these are added separately in the build command
    built_in_plugins = ["git", "github", "adr", "linear", "code_analysis", "change_patterns"]
    
    # Return only third-party plugins
    return [p for p in registry.get_all() if p.get_name() not in built_in_plugins]
