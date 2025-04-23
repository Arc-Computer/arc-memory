---
status: Accepted
date: 2023-11-15
decision_makers: Jarrod Barnes
---

# ADR-003: Plugin Architecture for Extensibility

## Context

Arc Memory needs to support multiple data sources beyond the initial Git, GitHub, and ADR sources. As the project evolves, we anticipate the need to integrate with additional systems like Notion, Jira, Linear, G-Suite, and other data sources based on customer demand.

To support this extensibility, we need an architecture that allows for:
1. Easy addition of new data sources without modifying the core codebase
2. Consistent interface for all data sources
3. Discovery and registration of plugins
4. Configuration of plugins
5. Incremental builds with plugin-specific metadata

## Decision

We will implement a plugin architecture for Arc Memory that allows for extensible data ingestion. The architecture will consist of:

1. **Plugin Interface**: A protocol defining the methods that all ingestor plugins must implement
2. **Plugin Registry**: A registry for discovering and managing plugins
3. **Plugin Discovery**: A mechanism for discovering plugins using entry points
4. **Plugin Configuration**: A mechanism for configuring plugins

### Plugin Interface

The plugin interface will be defined as a Protocol with the following methods:

```python
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
    
    def ingest(self, last_processed: Optional[Dict[str, Any]] = None) -> tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest data from the source and return nodes, edges, and metadata."""
        ...
```

### Plugin Registry

The plugin registry will be responsible for:
1. Registering plugins
2. Retrieving plugins by name
3. Retrieving plugins by node type
4. Retrieving plugins by edge type
5. Listing all registered plugins

### Plugin Discovery

Plugins will be discovered using Python's entry points mechanism. This allows third-party packages to register plugins without modifying the core codebase.

Built-in plugins (Git, GitHub, ADR) will be registered automatically.

### Plugin Configuration

Plugins will be configured using a combination of:
1. Command-line arguments for common options
2. Plugin-specific configuration in a configuration file
3. Environment variables for sensitive information

## Consequences

### Positive

1. **Extensibility**: New data sources can be added without modifying the core codebase
2. **Consistency**: All data sources use the same interface
3. **Discoverability**: Plugins can be discovered and registered automatically
4. **Configuration**: Plugins can be configured independently
5. **Incremental Builds**: Each plugin can maintain its own metadata for incremental builds

### Negative

1. **Complexity**: The plugin architecture adds some complexity to the codebase
2. **Performance**: Dynamic discovery and loading of plugins may have a small performance impact
3. **Testing**: Testing with multiple plugins requires more complex test setup

### Mitigations

1. **Documentation**: Comprehensive documentation for plugin developers
2. **Examples**: Example plugins to demonstrate best practices
3. **Testing**: Comprehensive tests for the plugin architecture
4. **Performance Optimization**: Caching of plugin discovery results

## Implementation

The plugin architecture will be implemented in the following steps:

1. Define the `IngestorPlugin` protocol in `arc_memory/plugins.py`
2. Create the `IngestorRegistry` class in the same file
3. Implement plugin discovery using entry points
4. Refactor existing ingestors (Git, GitHub, ADR) to use the plugin interface
5. Update the build process to use the plugin registry
6. Add tests for the plugin architecture
7. Add documentation for plugin developers
