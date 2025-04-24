# Plugin Architecture API

The Plugin Architecture API allows you to extend Arc Memory with additional data sources beyond the built-in Git, GitHub, and ADR plugins.

## Overview

Arc Memory uses a plugin-based architecture to ingest data from various sources. Each plugin is responsible for ingesting data from a specific source and converting it into nodes and edges in the knowledge graph. The plugin architecture is designed to be extensible, allowing you to add support for new data sources without modifying the core codebase.

## Key Components

### `IngestorPlugin` Protocol

```python
class IngestorPlugin(Protocol):
    def get_name(self) -> str: ...
    def get_node_types(self) -> List[str]: ...
    def get_edge_types(self) -> List[str]: ...
    def ingest(self, last_processed: Optional[Dict[str, Any]] = None) -> tuple[List[Node], List[Edge], Dict[str, Any]]: ...
```

This protocol defines the interface that all ingestor plugins must implement:

- `get_name()`: Returns a unique name for the plugin (e.g., "git", "github", "adr")
- `get_node_types()`: Returns a list of node types the plugin can create
- `get_edge_types()`: Returns a list of edge types the plugin can create
- `ingest()`: Ingests data from the source and returns nodes, edges, and metadata

### `IngestorRegistry` Class

```python
class IngestorRegistry:
    def __init__(self): ...
    def register(self, ingestor: IngestorPlugin) -> None: ...
    def get(self, name: str) -> Optional[IngestorPlugin]: ...
    def list_plugins(self) -> List[str]: ...
    def get_all(self) -> List[IngestorPlugin]: ...
    def get_by_node_type(self, node_type: str) -> List[IngestorPlugin]: ...
    def get_by_edge_type(self, edge_type: str) -> List[IngestorPlugin]: ...
```

The registry manages the discovery and registration of plugins, and provides methods for retrieving plugins by name or type:

- `register()`: Registers a plugin with the registry
- `get()`: Gets a plugin by name
- `list_plugins()`: Lists all registered plugins
- `get_all()`: Gets all registered plugins
- `get_by_node_type()`: Gets plugins that can create a specific node type
- `get_by_edge_type()`: Gets plugins that can create a specific edge type

### `discover_plugins()` Function

```python
def discover_plugins() -> IngestorRegistry:
```

This function discovers and registers all available plugins from two sources:

1. Built-in plugins (Git, GitHub, ADR)
2. Third-party plugins registered via entry points

It returns an `IngestorRegistry` containing all discovered plugins.

## Creating a Custom Plugin

To create a custom plugin, you need to:

1. Create a class that implements the `IngestorPlugin` protocol
2. Register the plugin using entry points

### Example Plugin

```python
from typing import Any, Dict, List, Optional
from pathlib import Path

from arc_memory.schema.models import Edge, Node, NodeType, EdgeRel

class CustomIngestor:
    """Custom ingestor plugin for Arc Memory."""
    
    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "custom-source"
    
    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return [NodeType.COMMIT, NodeType.FILE]
    
    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.MODIFIES]
    
    def ingest(
        self,
        repo_path: Path,
        last_processed: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest data from the custom source."""
        # Your implementation here
        nodes = []
        edges = []
        metadata = {"last_processed": "2025-04-24T12:00:00Z"}
        return nodes, edges, metadata
```

### Registering the Plugin

To register your plugin, add an entry point to your `setup.py` or `pyproject.toml`:

```python
# setup.py
setup(
    # ...
    entry_points={
        "arc_memory.plugins": [
            "custom-source = my_package.my_module:CustomIngestor",
        ],
    },
)
```

```toml
# pyproject.toml
[project.entry-points."arc_memory.plugins"]
custom-source = "my_package.my_module:CustomIngestor"
```

## Built-in Plugins

Arc Memory includes three built-in plugins:

1. **Git Plugin**: Ingests data from Git commits and files
2. **GitHub Plugin**: Ingests data from GitHub PRs and issues
3. **ADR Plugin**: Ingests data from Architecture Decision Records

These plugins are automatically discovered and registered when you call `discover_plugins()`.

## Plugin Discovery Process

The plugin discovery process works as follows:

1. Create an empty `IngestorRegistry`
2. Register built-in plugins (Git, GitHub, ADR)
3. Discover and register third-party plugins from entry points
4. Return the registry

## Incremental Ingestion

Plugins support incremental ingestion, which allows them to only process new data since the last build. This is done by passing the `last_processed` parameter to the `ingest()` method, which contains metadata from the previous run.

For example, the Git plugin uses the last processed commit hash to determine which commits are new, while the GitHub plugin uses the last processed PR and issue numbers.

## Error Handling

The plugin architecture includes comprehensive error handling:

- Failed plugin loading doesn't prevent other plugins from being loaded
- Detailed error messages for common issues
- Graceful handling of plugin failures
- Debug logging for troubleshooting

## Performance

The plugin discovery process is designed for performance:

- Plugin discovery typically takes less than 100ms
- Plugins are only loaded when needed
- Incremental ingestion reduces processing time
