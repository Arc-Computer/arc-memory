# Creating Plugins for Arc Memory

This guide walks you through the process of creating a custom plugin for Arc Memory to ingest data from additional sources.

## Prerequisites

- Python 3.12 or higher
- Arc Memory installed (`pip install arc-memory`)
- Basic understanding of Python package development

## Quick Start

1. Create a new Python package for your plugin
2. Implement the `IngestorPlugin` protocol
3. Register your plugin using entry points
4. Install your package

## Step 1: Create a Package Structure

Create a directory structure for your plugin package:

```
arc-memory-myplugin/
├── pyproject.toml
├── README.md
└── src/
    └── arc_memory_myplugin/
        ├── __init__.py
        └── plugin.py
```

## Step 2: Define Package Metadata

Create a `pyproject.toml` file:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "arc-memory-myplugin"
version = "0.1.0"
description = "My custom plugin for Arc Memory"
readme = "README.md"
requires-python = ">=3.12"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"},
]
dependencies = [
    "arc-memory>=0.1.0",
    # Add any other dependencies your plugin needs
]

[project.entry-points."arc_memory.plugins"]
myplugin = "arc_memory_myplugin.plugin:MyPlugin"
```

## Step 3: Implement the Plugin

In `src/arc_memory_myplugin/plugin.py`:

```python
from typing import List, Optional, Tuple, Dict, Any
from arc_memory.plugins import IngestorPlugin
from arc_memory.schema.models import Node, Edge

class MyPlugin(IngestorPlugin):
    def get_name(self) -> str:
        """Return a unique name for this plugin."""
        return "myplugin"
    
    def get_node_types(self) -> List[str]:
        """Return a list of node types this plugin can create."""
        return ["my_custom_node"]
    
    def get_edge_types(self) -> List[str]:
        """Return a list of edge types this plugin can create."""
        return ["RELATES_TO"]
    
    def ingest(self, last_processed: Optional[Dict[str, Any]] = None) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """
        Ingest data from your custom source.
        
        Args:
            last_processed: Optional dictionary containing metadata from the previous run,
                            used for incremental ingestion.
        
        Returns:
            A tuple containing:
            - List[Node]: List of nodes created from the data source
            - List[Edge]: List of edges created from the data source
            - Dict[str, Any]: Metadata about the ingestion process, used for incremental builds
        """
        # Initialize empty lists for nodes and edges
        nodes = []
        edges = []
        
        # Your custom ingestion logic here
        # This is where you would:
        # 1. Connect to your data source
        # 2. Fetch data (using last_processed for incremental updates)
        # 3. Convert data to Node and Edge objects
        # 4. Add them to the nodes and edges lists
        
        # Example: Create a sample node
        node = Node(
            id="my_custom_node:1",
            type="my_custom_node",
            title="My Custom Node",
            body="This is a custom node created by my plugin",
            ts=datetime.now(),
            extra={
                "custom_field": "custom_value",
                "source": "my_plugin"
            }
        )
        nodes.append(node)
        
        # Example: Create a sample edge connecting to a Git commit
        edge = Edge(
            src="my_custom_node:1",
            dst="commit:abc123",  # This would be a real commit ID in practice
            rel="RELATES_TO"
        )
        edges.append(edge)
        
        # Create metadata for incremental builds
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "count": len(nodes),
            "custom_field": "custom_value"
        }
        
        return nodes, edges, metadata
```

## Step 4: Install Your Plugin

Install your plugin in development mode:

```bash
cd arc-memory-myplugin
pip install -e .
```

## Step 5: Test Your Plugin

Create a test script to verify your plugin works:

```python
from arc_memory.plugins import discover_plugins

# Discover all plugins
registry = discover_plugins()

# Check if your plugin is discovered
print(f"Available plugins: {registry.list_plugins()}")

# Get your plugin
my_plugin = registry.get("myplugin")
if my_plugin:
    print(f"Found plugin: {my_plugin.get_name()}")
    print(f"Node types: {my_plugin.get_node_types()}")
    print(f"Edge types: {my_plugin.get_edge_types()}")
    
    # Test ingestion
    nodes, edges, metadata = my_plugin.ingest()
    print(f"Ingested {len(nodes)} nodes and {len(edges)} edges")
    print(f"Metadata: {metadata}")
else:
    print("Plugin not found!")
```

## Advanced Topics

### Configuration

If your plugin needs configuration (API keys, URLs, etc.), you can access it from the Arc Memory configuration:

```python
from arc_memory.config import get_plugin_config

class MyPlugin(IngestorPlugin):
    def __init__(self):
        self.config = get_plugin_config(self.get_name())
        # Access configuration values
        self.api_key = self.config.get("api_key")
        self.url = self.config.get("url")
```

Users can configure your plugin in `~/.arc/config.yaml`:

```yaml
plugins:
  myplugin:
    api_key: "your-api-key"
    url: "https://api.example.com"
```

### Authentication

If your plugin needs to authenticate with an external service, consider implementing a helper method:

```python
def _authenticate(self):
    """Authenticate with the external service."""
    # Your authentication logic here
    # This might use self.config to get credentials
    return client
```

### Incremental Updates

For efficient incremental updates, use the `last_processed` parameter:

```python
def ingest(self, last_processed: Optional[Dict[str, Any]] = None) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
    # Get the timestamp from last_processed, or use a default
    last_timestamp = None
    if last_processed and "timestamp" in last_processed:
        last_timestamp = last_processed["timestamp"]
    
    # Fetch only data updated since last_timestamp
    # ...
```

### Error Handling

Implement robust error handling to ensure your plugin doesn't crash the build process:

```python
def ingest(self, last_processed: Optional[Dict[str, Any]] = None) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
    nodes = []
    edges = []
    metadata = {"timestamp": datetime.now().isoformat()}
    
    try:
        # Your ingestion logic here
    except Exception as e:
        logger.error(f"Error in {self.get_name()} plugin: {e}")
        # Return what we have so far, or empty lists
    
    return nodes, edges, metadata
```

## Best Practices

1. **Unique IDs**: Prefix node IDs with your plugin name to avoid collisions (e.g., `jira_issue:123`)
2. **Consistent Types**: Follow the naming conventions for node and edge types
3. **Documentation**: Document the node and edge types your plugin creates
4. **Testing**: Include tests for your plugin
5. **Error Handling**: Gracefully handle API errors and rate limits
6. **Incremental Processing**: Use `last_processed` to minimize API calls
7. **Dependencies**: Minimize dependencies and document them clearly

## Example Plugins

For reference implementations, see the built-in plugins:

- `GitIngestor` in `arc_memory.ingest.git`
- `GitHubIngestor` in `arc_memory.ingest.github`
- `ADRIngestor` in `arc_memory.ingest.adr`

## Getting Help

If you encounter issues or have questions about plugin development:

- Check the [Arc Memory documentation](https://arc-memory.readthedocs.io/)
- Open an issue on the [GitHub repository](https://github.com/arc-memory/arc-memory)
- Join the [Discord community](https://discord.gg/arc-memory)
