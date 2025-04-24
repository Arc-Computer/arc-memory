# Arc Memory SDK Plugin Architecture

> **Status**: Draft
>
> **Date**: 2025-04-23
>
> **Author**: Arc Memory Team

## Overview

The Arc Memory SDK's plugin architecture enables extensible ingestion of data from various sources beyond the core Git, GitHub, and ADR integrations. This document describes the plugin system design, how to implement custom plugins, and the standard interfaces that all plugins must follow.

## Core Concepts

The plugin architecture is built around three key components:

1. **IngestorPlugin Protocol**: A standard interface that all data source plugins must implement
2. **IngestorRegistry**: A central registry that manages plugin discovery and access
3. **Plugin Discovery Mechanism**: A system for finding and loading plugins at runtime

## IngestorPlugin Protocol

All data source plugins must implement the `IngestorPlugin` protocol, which defines the following methods:

```python
class IngestorPlugin(Protocol):
    def get_name(self) -> str:
        """Return a unique name for this plugin."""
        ...

    def get_node_types(self) -> list[str]:
        """Return a list of node types this plugin can create."""
        ...

    def get_edge_types(self) -> list[str]:
        """Return a list of edge types this plugin can create."""
        ...

    def ingest(self, last_processed: Optional[dict] = None) -> tuple[list[Node], list[Edge], dict]:
        """
        Ingest data from the source and return nodes, edges, and metadata.

        Args:
            last_processed: Optional dictionary containing metadata from the previous run,
                            used for incremental ingestion.

        Returns:
            A tuple containing:
            - list[Node]: List of nodes created from the data source
            - list[Edge]: List of edges created from the data source
            - dict: Metadata about the ingestion process, used for incremental builds
        """
        ...
```

### Node and Edge Types

Plugins should use consistent naming conventions for node and edge types:

- Node types should be lowercase, with underscores for spaces (e.g., `commit`, `github_issue`, `jira_ticket`)
- Edge types should be UPPERCASE, with underscores for spaces (e.g., `MODIFIES`, `MENTIONS`, `DEPENDS_ON`)

### Incremental Ingestion

The `last_processed` parameter enables efficient incremental builds by providing metadata from the previous ingestion run. Plugins should:

1. Use this information to fetch only new or updated data
2. Return updated metadata that will be passed to the next run

Example metadata structure:

```json
{
  "timestamp": "2025-04-23T15:30:00Z",
  "last_id": "issue-123",
  "count": 42,
  "source_specific_data": {
    "api_version": "2.0",
    "cursor": "next_page_token"
  }
}
```

## IngestorRegistry

The `IngestorRegistry` manages plugin discovery and registration:

```python
class IngestorRegistry:
    def __init__(self):
        """Initialize an empty registry."""
        self.ingestors = {}

    def register(self, ingestor: IngestorPlugin) -> None:
        """
        Register a plugin with the registry.

        Args:
            ingestor: An instance of a class implementing the IngestorPlugin protocol
        """
        self.ingestors[ingestor.get_name()] = ingestor

    def get(self, name: str) -> Optional[IngestorPlugin]:
        """
        Get a plugin by name.

        Args:
            name: The name of the plugin to retrieve

        Returns:
            The plugin instance, or None if not found
        """
        return self.ingestors.get(name)

    def list_plugins(self) -> list[str]:
        """
        List all registered plugins.

        Returns:
            A list of plugin names
        """
        return list(self.ingestors.keys())

    def get_all(self) -> list[IngestorPlugin]:
        """
        Get all registered plugins.

        Returns:
            A list of plugin instances
        """
        return list(self.ingestors.values())
```

## Plugin Discovery

Arc Memory uses Python's entry point system to discover third-party plugins:

```python
def discover_plugins() -> IngestorRegistry:
    """
    Discover and register all available plugins.

    Returns:
        An IngestorRegistry containing all discovered plugins
    """
    registry = IngestorRegistry()

    # Register built-in plugins
    registry.register(GitIngestor())
    registry.register(GitHubIngestor())
    registry.register(ADRIngestor())

    # Discover and register third-party plugins
    for entry_point in pkg_resources.iter_entry_points('arc_memory.plugins'):
        try:
            plugin_class = entry_point.load()
            registry.register(plugin_class())
        except Exception as e:
            logger.warning(f"Failed to load plugin {entry_point.name}: {e}")

    return registry
```

## Implementing a Custom Plugin

To create a custom plugin for the Arc Memory SDK:

1. Create a class that implements the `IngestorPlugin` protocol
2. Register it using the entry point system in your package's `setup.py` or `pyproject.toml`

### Example: Notion Plugin

```python
from typing import List, Optional, Tuple, Dict, Any
from arc_memory.plugins import IngestorPlugin
from arc_memory.schema.models import Node, Edge, NodeType

class NotionIngestor(IngestorPlugin):
    def get_name(self) -> str:
        return "notion"

    def get_node_types(self) -> list[str]:
        return ["notion_page", "notion_database"]

    def get_edge_types(self) -> list[str]:
        return ["REFERENCES", "CONTAINS"]

    def ingest(self, last_processed: Optional[dict] = None) -> tuple[list[Node], list[Edge], dict]:
        # Initialize empty lists for nodes and edges
        nodes = []
        edges = []

        # Get the timestamp from last_processed, or use a default
        last_timestamp = None
        if last_processed and "timestamp" in last_processed:
            last_timestamp = last_processed["timestamp"]

        # Connect to Notion API and fetch data
        # This is a simplified example - real implementation would use the Notion API
        notion_client = self._get_notion_client()
        pages = notion_client.fetch_pages(updated_since=last_timestamp)
        databases = notion_client.fetch_databases(updated_since=last_timestamp)

        # Process pages
        for page in pages:
            # Create a node for the page
            page_node = Node(
                id=f"notion_page:{page.id}",
                type="notion_page",
                title=page.title,
                body=page.content,
                ts=page.last_edited_time,
                extra={
                    "url": page.url,
                    "created_by": page.created_by,
                    "last_edited_by": page.last_edited_by,
                    "parent_type": page.parent.type,
                    "parent_id": page.parent.id
                }
            )
            nodes.append(page_node)

            # Create edges for references to other pages
            for reference in page.references:
                edge = Edge(
                    src=f"notion_page:{page.id}",
                    dst=f"notion_page:{reference.id}",
                    rel="REFERENCES"
                )
                edges.append(edge)

        # Process databases
        for database in databases:
            # Create a node for the database
            db_node = Node(
                id=f"notion_database:{database.id}",
                type="notion_database",
                title=database.title,
                body=database.description,
                ts=database.last_edited_time,
                extra={
                    "url": database.url,
                    "created_by": database.created_by,
                    "last_edited_by": database.last_edited_by,
                    "schema": database.properties
                }
            )
            nodes.append(db_node)

            # Create edges for pages in this database
            for page_id in database.pages:
                edge = Edge(
                    src=f"notion_database:{database.id}",
                    dst=f"notion_page:{page_id}",
                    rel="CONTAINS"
                )
                edges.append(edge)

        # Create metadata for incremental builds
        metadata = {
            "timestamp": notion_client.current_time,
            "page_count": len(pages),
            "database_count": len(databases),
            "api_version": notion_client.api_version
        }

        return nodes, edges, metadata

    def _get_notion_client(self):
        # Implementation would initialize and return a Notion API client
        pass
```

### Package Registration

In your plugin package's `pyproject.toml`:

```toml
[project.entry-points."arc_memory.plugins"]
notion = "my_notion_plugin:NotionIngestor"
```

Or in `setup.py`:

```python
setup(
    name="arc-memory-notion",
    # ... other setup parameters ...
    entry_points={
        'arc_memory.plugins': [
            'notion=my_notion_plugin:NotionIngestor',
        ],
    },
)
```

## Built-in Plugins

The Arc Memory SDK includes several built-in plugins:

1. **GitIngestor**: Ingests commit history from Git repositories
2. **GitHubIngestor**: Ingests issues and pull requests from GitHub
3. **ADRIngestor**: Ingests Architectural Decision Records from Markdown files

These plugins follow the same interface as custom plugins and can serve as reference implementations.

## Plugin Configuration

Plugins may require configuration such as API keys or endpoint URLs. Arc Memory provides a standard way to configure plugins:

```python
# In ~/.arc/config.yaml
plugins:
  notion:
    api_key: "secret_..."
    workspace_id: "123456"
  jira:
    url: "https://mycompany.atlassian.net"
    username: "user@example.com"
    api_token: "..."
```

Plugins can access this configuration using the `arc_memory.config` module:

```python
from arc_memory.config import get_plugin_config

class MyPlugin(IngestorPlugin):
    def __init__(self):
        self.config = get_plugin_config(self.get_name())
        # self.config now contains the plugin's configuration
```

## Best Practices

When implementing plugins, follow these best practices:

1. **Error Handling**: Gracefully handle API errors and rate limits
2. **Incremental Processing**: Use `last_processed` to minimize API calls
3. **Consistent IDs**: Use prefixed IDs (e.g., `notion_page:123`) to avoid collisions
4. **Documentation**: Document node and edge types created by your plugin
5. **Testing**: Include tests that verify your plugin works with mock data
6. **Dependencies**: Minimize dependencies and document them clearly

## Future Extensions

The plugin architecture is designed to be extended in the future:

1. **Plugin Lifecycle Hooks**: Methods for initialization, cleanup, etc.
2. **Plugin Dependencies**: Allow plugins to depend on other plugins
3. **Plugin Versioning**: Version compatibility checking
4. **UI Integration**: Allow plugins to extend the VS Code UI

The Arc Memory SDK's plugin architecture provides a flexible and extensible way to ingest data from various sources. By implementing the `IngestorPlugin` protocol and registering your plugin, you can extend the Arc Memory SDK to support new data sources and integrate them seamlessly into the knowledge graph.
