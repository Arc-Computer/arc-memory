# Creating Custom Plugins

This guide provides examples of how to create custom plugins for Arc Memory to ingest data from additional sources beyond the built-in Git, GitHub, and ADR plugins.

**Related Documentation:**
- [Plugin Architecture](../plugin-architecture.md) - Technical details of the plugin system
- [Plugins API](../api/plugins.md) - API reference for plugin development
- [Build Commands](../cli/build.md) - Using plugins with the build command
- [Models](../api/models.md) - Data models used in plugins

## Plugin Architecture Overview

Arc Memory's plugin architecture allows you to extend the system to ingest data from any source. Plugins are Python classes that implement the `IngestorPlugin` protocol, which defines methods for:

1. Identifying the plugin
2. Specifying the types of nodes and edges it creates
3. Ingesting data from the source

## Basic Plugin Template

Here's a basic template for creating a custom plugin:

```python
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from datetime import datetime

from arc_memory.plugins import IngestorPlugin
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel

class MyCustomPlugin(IngestorPlugin):
    """Custom ingestor plugin for Arc Memory."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "my-custom-source"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return ["custom_node"]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.MENTIONS]

    def ingest(
        self,
        last_processed: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest data from the custom source."""
        nodes = []
        edges = []

        # Your implementation here
        # 1. Fetch data from your source
        # 2. Create nodes and edges
        # 3. Return them along with metadata

        # Example: Create a sample node
        node = Node(
            id="custom_node:1",
            type="custom_node",
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
            src="custom_node:1",
            dst="commit:abc123",  # This would be a real commit ID in practice
            rel=EdgeRel.MENTIONS
        )
        edges.append(edge)

        # Create metadata for incremental builds
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "count": len(nodes)
        }

        return nodes, edges, metadata
```

## Registering Your Plugin

To make your plugin available to Arc Memory, you need to register it using Python's entry point system:

### In setup.py

```python
from setuptools import setup

setup(
    name="arc-memory-myplugin",
    version="0.1.0",
    packages=["arc_memory_myplugin"],
    entry_points={
        "arc_memory.plugins": [
            "my-custom-source = arc_memory_myplugin.plugin:MyCustomPlugin",
        ],
    },
)
```

### In pyproject.toml

```toml
[project.entry-points."arc_memory.plugins"]
my-custom-source = "arc_memory_myplugin.plugin:MyCustomPlugin"
```

## Example: Notion Plugin

Here's an example of a plugin that ingests data from Notion:

```python
import os
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

from arc_memory.plugins import IngestorPlugin
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel

class NotionIngestor(IngestorPlugin):
    """Ingestor plugin for Notion pages and databases."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "notion"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return ["notion_page", "notion_database"]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.MENTIONS, "CONTAINS"]

    def ingest(
        self,
        last_processed: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest data from Notion."""
        nodes = []
        edges = []

        # Get Notion API token from environment or keyring
        notion_token = os.environ.get("NOTION_TOKEN")
        if not notion_token:
            try:
                import keyring
                notion_token = keyring.get_password("arc_memory", "notion_token")
            except:
                pass

        if not notion_token:
            print("Notion token not found. Skipping Notion ingestion.")
            return [], [], {"last_sync": None}

        # Initialize Notion client
        from notion_client import Client
        notion = Client(auth=notion_token)

        # Get last sync time for incremental ingestion
        last_sync = None
        if last_processed and "last_sync" in last_processed:
            last_sync = last_processed["last_sync"]

        # Fetch pages from Notion
        try:
            # Query for pages
            response = notion.search(
                filter={"property": "object", "value": "page"},
                sort={"direction": "descending", "timestamp": "last_edited_time"}
            )

            # Process pages
            for page in response["results"]:
                # Skip if this page was processed in a previous run
                if last_sync and page["last_edited_time"] <= last_sync:
                    continue

                # Create a node for this page
                page_id = page["id"].replace("-", "")
                node = Node(
                    id=f"notion_page:{page_id}",
                    type="notion_page",
                    title=self._get_page_title(page),
                    body=self._get_page_content(page),
                    ts=datetime.fromisoformat(page["last_edited_time"].replace("Z", "+00:00")),
                    extra={
                        "url": page["url"],
                        "created_time": page["created_time"],
                        "last_edited_time": page["last_edited_time"],
                        "notion_id": page["id"]
                    }
                )
                nodes.append(node)

                # Look for mentions of Git commits, PRs, or issues
                self._extract_mentions(node, edges)

            # Create metadata for incremental builds
            metadata = {
                "last_sync": datetime.now().isoformat()
            }

            return nodes, edges, metadata

        except Exception as e:
            print(f"Error ingesting Notion data: {e}")
            return [], [], {"last_sync": last_sync}

    def _get_page_title(self, page):
        """Extract the title from a Notion page."""
        # Implementation depends on Notion API structure
        # This is a simplified example
        if "properties" in page and "title" in page["properties"]:
            title_property = page["properties"]["title"]
            if "title" in title_property and title_property["title"]:
                return title_property["title"][0]["plain_text"]
        return "Untitled"

    def _get_page_content(self, page):
        """Extract the content from a Notion page."""
        # In a real implementation, you would use the Notion API to get blocks
        # This is a simplified example
        return f"Notion page content for {page['id']}"

    def _extract_mentions(self, node, edges):
        """Extract mentions of Git commits, PRs, or issues from page content."""
        # In a real implementation, you would parse the content for patterns like:
        # - Commit: abc123
        # - PR #42
        # - Issue #123
        # This is a simplified example

        # Example: If we find a mention of a commit
        edges.append(Edge(
            src=node.id,
            dst="commit:abc123",
            rel=EdgeRel.MENTIONS
        ))
```

## Example: Jira Plugin

Here's an example of a plugin that ingests data from Jira:

```python
import os
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import re

from arc_memory.plugins import IngestorPlugin
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel

class JiraIngestor(IngestorPlugin):
    """Ingestor plugin for Jira issues."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "jira"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return ["jira_issue"]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.MENTIONS, "IMPLEMENTS"]

    def ingest(
        self,
        last_processed: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest data from Jira."""
        nodes = []
        edges = []

        # Get Jira credentials from environment
        jira_url = os.environ.get("JIRA_URL")
        jira_user = os.environ.get("JIRA_USER")
        jira_token = os.environ.get("JIRA_TOKEN")

        if not all([jira_url, jira_user, jira_token]):
            print("Jira credentials not found. Skipping Jira ingestion.")
            return [], [], {"last_updated": None}

        # Initialize Jira client
        from jira import JIRA
        jira = JIRA(server=jira_url, basic_auth=(jira_user, jira_token))

        # Get project key from config or environment
        project_key = os.environ.get("JIRA_PROJECT", "PROJ")

        # Get last updated time for incremental ingestion
        last_updated = None
        if last_processed and "last_updated" in last_processed:
            last_updated = last_processed["last_updated"]

        # Build JQL query
        jql = f"project = {project_key}"
        if last_updated:
            jql += f" AND updated >= '{last_updated}'"

        # Fetch issues from Jira
        try:
            issues = jira.search_issues(jql, maxResults=100)

            for issue in issues:
                # Create a node for this issue
                node = Node(
                    id=f"jira_issue:{issue.key}",
                    type="jira_issue",
                    title=issue.fields.summary,
                    body=issue.fields.description or "",
                    ts=datetime.fromisoformat(issue.fields.updated.replace("Z", "+00:00")),
                    extra={
                        "key": issue.key,
                        "status": issue.fields.status.name,
                        "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                        "reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
                        "created": issue.fields.created,
                        "updated": issue.fields.updated,
                        "url": f"{jira_url}/browse/{issue.key}"
                    }
                )
                nodes.append(node)

                # Extract commit mentions from comments
                for comment in jira.comments(issue.key):
                    # Look for commit mentions in the format "commit:abc123" or similar
                    commit_matches = re.findall(r'commit:([a-f0-9]+)', comment.body, re.IGNORECASE)
                    for commit_hash in commit_matches:
                        edges.append(Edge(
                            src=node.id,
                            dst=f"commit:{commit_hash}",
                            rel=EdgeRel.MENTIONS
                        ))

                    # Look for PR mentions in the format "PR #42" or similar
                    pr_matches = re.findall(r'PR #(\d+)', comment.body, re.IGNORECASE)
                    for pr_number in pr_matches:
                        edges.append(Edge(
                            src=node.id,
                            dst=f"pr:{pr_number}",
                            rel=EdgeRel.MENTIONS
                        ))

            # Create metadata for incremental builds
            metadata = {
                "last_updated": datetime.now().isoformat()
            }

            return nodes, edges, metadata

        except Exception as e:
            print(f"Error ingesting Jira data: {e}")
            return [], [], {"last_updated": last_updated}
```

## Best Practices for Plugin Development

### 1. Use Unique IDs

Ensure your node IDs are unique by prefixing them with your plugin name:

```python
node_id = f"{plugin_name}:{original_id}"  # e.g., "notion_page:123"
```

### 2. Handle Incremental Ingestion

Use the `last_processed` parameter to implement incremental ingestion:

```python
def ingest(self, last_processed: Optional[Dict[str, Any]] = None):
    # Get last sync time
    last_sync = None
    if last_processed and "last_sync" in last_processed:
        last_sync = last_processed["last_sync"]

    # Only process new data
    if last_sync:
        # Filter data based on last_sync
        pass
```

### 3. Error Handling

Implement robust error handling to prevent plugin failures from affecting the entire build process:

```python
try:
    # Your implementation
except Exception as e:
    print(f"Error in plugin: {e}")
    return [], [], {}  # Return empty results
```

### 4. Documentation

Document your plugin thoroughly, including:

- Node types and their attributes
- Edge types and their meanings
- Configuration requirements
- Dependencies

### 5. Testing

Write tests for your plugin to ensure it works correctly:

```python
def test_my_plugin():
    plugin = MyCustomPlugin()
    nodes, edges, metadata = plugin.ingest()

    assert len(nodes) > 0
    assert len(edges) > 0
    assert "timestamp" in metadata
```

## Plugin Development Workflow

Here's a step-by-step workflow for developing and testing custom plugins:

### 1. Set Up Development Environment

```bash
# Create a new directory for your plugin
mkdir arc-memory-myplugin
cd arc-memory-myplugin

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Unix/macOS
venv\Scripts\activate     # On Windows

# Install arc-memory in development mode
pip install -e /path/to/arc-memory

# Create basic project structure
mkdir -p src/arc_memory_myplugin
touch src/arc_memory_myplugin/__init__.py
touch src/arc_memory_myplugin/plugin.py
touch pyproject.toml
touch README.md
```

### 2. Implement Your Plugin

Create your plugin implementation in `src/arc_memory_myplugin/plugin.py`:

```python
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

from arc_memory.plugins import IngestorPlugin
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel

class MyPlugin(IngestorPlugin):
    """Custom ingestor plugin for Arc Memory."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "myplugin"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return ["custom_node"]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [EdgeRel.MENTIONS]

    def ingest(
        self,
        last_processed: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest data from the custom source."""
        nodes = []
        edges = []

        # Your implementation here
        # For testing, create a simple node
        node = Node(
            id="custom_node:1",
            type="custom_node",
            title="Test Node",
            body="This is a test node",
            ts=datetime.now(),
            extra={"source": "myplugin"}
        )
        nodes.append(node)

        # Create metadata for incremental builds
        metadata = {
            "timestamp": datetime.now().isoformat()
        }

        return nodes, edges, metadata
```

### 3. Configure Your Package

Set up your `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "arc-memory-myplugin"
version = "0.1.0"
description = "Custom plugin for Arc Memory"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
dependencies = [
    "arc-memory",
]

[project.entry-points."arc_memory.plugins"]
myplugin = "arc_memory_myplugin.plugin:MyPlugin"
```

### 4. Install Your Plugin in Development Mode

```bash
# Install your plugin in development mode
pip install -e .
```

### 5. Test Your Plugin

#### Manual Testing

```bash
# Enable debug logging to see detailed output
arc build --debug

# Check if your plugin was discovered
arc doctor
```

Look for output like:
```
Discovered plugins: ['git', 'github', 'adr', 'myplugin']
```

#### Unit Testing

Create a test file `tests/test_plugin.py`:

```python
import unittest
from arc_memory_myplugin.plugin import MyPlugin

class TestMyPlugin(unittest.TestCase):
    def test_plugin_basics(self):
        plugin = MyPlugin()
        self.assertEqual(plugin.get_name(), "myplugin")
        self.assertIn("custom_node", plugin.get_node_types())

    def test_ingest(self):
        plugin = MyPlugin()
        nodes, edges, metadata = plugin.ingest()
        self.assertGreaterEqual(len(nodes), 1)
        self.assertIn("timestamp", metadata)

if __name__ == "__main__":
    unittest.main()
```

Run the tests:
```bash
python -m unittest tests/test_plugin.py
```

### 6. Debugging Plugins

#### Debug Logging

To see detailed logs during plugin execution:

```bash
# Enable debug logging
arc build --debug
```

Look for log messages related to your plugin:
```
DEBUG:arc_memory.plugins:Registered plugin: myplugin
INFO:arc_memory.build:Ingesting myplugin data...
```

#### Common Issues and Solutions

1. **Plugin Not Discovered**:
   - Check your entry point configuration in `pyproject.toml`
   - Verify your plugin class implements all required methods
   - Make sure your package is installed (`pip list | grep myplugin`)

2. **Plugin Fails During Ingestion**:
   - Add try/except blocks with detailed logging in your `ingest` method
   - Check for API errors or rate limiting if your plugin uses external APIs
   - Verify your node and edge creation logic

3. **No Data in Graph**:
   - Verify your plugin is returning non-empty lists of nodes and edges
   - Check node IDs for proper formatting (e.g., "custom_node:1")
   - Ensure edge source and destination IDs refer to existing nodes

#### Interactive Debugging

For more complex issues, use Python's debugger:

```python
# Add this to your plugin code
import pdb

def ingest(self, last_processed=None):
    # ... your code ...
    pdb.set_trace()  # Debugger will stop here
    # ... more code ...
```

Then run:
```bash
arc build --debug
```

### 7. Packaging and Distribution

Once your plugin is working correctly:

```bash
# Build the package
python -m build

# Test the built package
pip install dist/arc_memory_myplugin-0.1.0-py3-none-any.whl

# Publish to PyPI (if desired)
twine upload dist/*
```

## Packaging and Distribution

To package your plugin for distribution:

1. Create a Python package with your plugin implementation
2. Register it using entry points as shown above
3. Publish it to PyPI:

```bash
python -m build
twine upload dist/*
```

Users can then install your plugin with:

```bash
pip install arc-memory-myplugin
```

And it will be automatically discovered and used by Arc Memory.
