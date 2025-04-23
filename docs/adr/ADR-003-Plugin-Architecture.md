# ADR-003: Plugin Architecture for Data Ingestion

> Status: Proposed
>
> **Date:** 2025-04-23
> 
> **Decision makers:** Jarrod Barnes (Founder), Core Eng Team
> 
> **Context:** Arc Memory needs to support multiple data sources beyond Git, GitHub, and ADRs. This ADR outlines the plugin architecture that will enable extensible data ingestion.

## 1 · Problem Statement

Arc Memory currently has hardcoded ingestors for Git, GitHub, and ADRs. As we expand to support additional data sources like Notion, Jira, Linear, and G-Suite, we need a flexible architecture that:

1. Allows adding new data sources without modifying core code
2. Maintains a consistent interface for all data sources
3. Supports incremental builds for efficient updates
4. Enables third-party developers to create their own integrations
5. Preserves type safety and testability

## 2 · Proposed Solution

We will implement a plugin architecture based on Python's Protocol pattern and entry point discovery system.

### 2.1 IngestorPlugin Protocol

```python
from typing import Protocol, List, Tuple, Dict, Any, Optional
from arc_memory.schema.models import Node, Edge

class IngestorPlugin(Protocol):
    def get_name(self) -> str:
        """Return a unique name for this plugin."""
        ...
    
    def get_node_types(self) -> List[str]:
        """Return a list of node types this plugin can create."""
        ...
    
    def get_edge_types(self) -> List[str]:
        """Return a list of edge types this plugin can create."""
        ...
    
    def ingest(self, last_processed: Optional[Dict[str, Any]] = None) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """
        Ingest data from the source and return nodes, edges, and metadata.
        
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
```

### 2.2 IngestorRegistry

```python
class IngestorRegistry:
    def __init__(self):
        """Initialize an empty registry."""
        self.ingestors: Dict[str, IngestorPlugin] = {}
    
    def register(self, ingestor: IngestorPlugin) -> None:
        """Register a plugin with the registry."""
        self.ingestors[ingestor.get_name()] = ingestor
    
    def get(self, name: str) -> Optional[IngestorPlugin]:
        """Get a plugin by name."""
        return self.ingestors.get(name)
    
    def list_plugins(self) -> List[str]:
        """List all registered plugins."""
        return list(self.ingestors.keys())
    
    def get_all(self) -> List[IngestorPlugin]:
        """Get all registered plugins."""
        return list(self.ingestors.values())
```

### 2.3 Plugin Discovery

```python
import pkg_resources
import logging
from typing import Type

logger = logging.getLogger(__name__)

def discover_plugins() -> IngestorRegistry:
    """Discover and register all available plugins."""
    registry = IngestorRegistry()
    
    # Register built-in plugins
    from arc_memory.ingest.git import GitIngestor
    from arc_memory.ingest.github import GitHubIngestor
    from arc_memory.ingest.adr import ADRIngestor
    
    registry.register(GitIngestor())
    registry.register(GitHubIngestor())
    registry.register(ADRIngestor())
    
    # Discover and register third-party plugins
    for entry_point in pkg_resources.iter_entry_points('arc_memory.plugins'):
        try:
            plugin_class: Type[IngestorPlugin] = entry_point.load()
            registry.register(plugin_class())
            logger.info(f"Loaded plugin: {entry_point.name}")
        except Exception as e:
            logger.warning(f"Failed to load plugin {entry_point.name}: {e}")
    
    return registry
```

### 2.4 Integration with Build Process

```python
def build_graph(
    repo_path: Path,
    output_path: Path,
    incremental: bool = False,
    plugins: Optional[List[str]] = None
) -> None:
    """Build the knowledge graph using available plugins."""
    # Discover plugins
    registry = discover_plugins()
    
    # Filter plugins if specified
    active_plugins = registry.get_all()
    if plugins:
        active_plugins = [p for p in active_plugins if p.get_name() in plugins]
    
    # Load existing manifest for incremental builds
    manifest = None
    if incremental:
        manifest = load_build_manifest()
    
    # Initialize lists for all nodes and edges
    all_nodes = []
    all_edges = []
    
    # Process each plugin
    for plugin in active_plugins:
        plugin_name = plugin.get_name()
        logger.info(f"Processing plugin: {plugin_name}")
        
        # Get last processed data for this plugin
        last_processed = None
        if manifest and incremental:
            last_processed = manifest.last_processed.get(plugin_name, {})
        
        # Run the plugin
        nodes, edges, metadata = plugin.ingest(last_processed)
        
        # Add results to the combined lists
        all_nodes.extend(nodes)
        all_edges.extend(edges)
        
        # Update manifest
        if manifest:
            manifest.last_processed[plugin_name] = metadata
    
    # Write to database
    # ... (existing database write code)
    
    # Update and save manifest
    # ... (existing manifest update code)
```

## 3 · Alternatives Considered

### 3.1 Class Inheritance

We considered using a base class with abstract methods instead of a Protocol:

```python
class BaseIngestor(ABC):
    @abstractmethod
    def get_name(self) -> str: ...
    
    @abstractmethod
    def ingest(self, last_processed: Optional[Dict] = None) -> Tuple[List[Node], List[Edge], Dict]: ...
```

**Pros:**
- Enforces implementation of required methods at instantiation time
- Can provide default implementations for some methods

**Cons:**
- Less flexible than Protocol (requires inheritance)
- More difficult to adapt existing classes
- Doesn't work well with multiple inheritance

### 3.2 Function-Based Plugins

We considered a simpler approach using functions as plugins:

```python
def register_plugin(name: str):
    def decorator(func):
        PLUGINS[name] = func
        return func
    return decorator

@register_plugin("github")
def ingest_github(last_processed=None):
    # Implementation
    return nodes, edges, metadata
```

**Pros:**
- Simpler implementation
- Less boilerplate

**Cons:**
- Less structured
- Harder to maintain type safety
- Doesn't encapsulate related functionality

### 3.3 Plugin Configuration Files

We considered requiring plugins to be registered in a configuration file:

```yaml
# ~/.arc/plugins.yaml
plugins:
  - name: github
    enabled: true
    module: arc_memory.ingest.github
    class: GitHubIngestor
```

**Pros:**
- More explicit control over which plugins are loaded
- Can configure plugin parameters

**Cons:**
- More complex setup for users
- Requires additional configuration parsing
- Less discoverable

## 4 · Impact

### 4.1 Positive Impacts

- **Extensibility**: Easy addition of new data sources
- **Decoupling**: Data source implementations are isolated from core code
- **Consistency**: All data sources follow the same interface
- **Discoverability**: Third-party plugins can be discovered automatically
- **Type Safety**: Protocol ensures type safety with static type checkers

### 4.2 Negative Impacts

- **Complexity**: Slightly more complex than direct function calls
- **Performance**: Small overhead from plugin discovery and registry lookups
- **Learning Curve**: Developers need to understand the plugin system

## 5 · Decision

We will implement the plugin architecture as described in Section 2, using:

1. The `IngestorPlugin` Protocol for defining the plugin interface
2. The `IngestorRegistry` class for managing plugins
3. The entry point discovery mechanism for third-party plugins
4. Integration with the build process to use all available plugins

This approach provides the best balance of flexibility, type safety, and ease of use.

**Proposed** – 2025-04-23

— Jarrod Barnes

## 6 · Implementation Checklist

- [ ] Create `plugins.py` module with `IngestorPlugin` Protocol
- [ ] Implement `IngestorRegistry` class
- [ ] Add plugin discovery function
- [ ] Refactor existing ingestors to implement the Protocol:
  - [ ] Convert `ingest_git.py` to `GitIngestor` class
  - [ ] Convert `ingest_github.py` to `GitHubIngestor` class
  - [ ] Convert `ingest_adr.py` to `ADRIngestor` class
- [ ] Update build process to use the plugin registry
- [ ] Add tests for the plugin system
- [ ] Create documentation for plugin developers
- [ ] Create example plugin for reference
