# How to Create a Custom Data Ingestor

## 1. Introduction

Arc Memory's data ingestion capabilities can be extended by creating custom ingestor plugins. This allows you to connect Arc Memory to new data sources, whether they are internal company tools, third-party APIs not yet supported, or custom data formats.

The plugin architecture is based on Python's [Protocol classes](https://docs.python.org/3/library/typing.html#typing.Protocol) for defining the interface and [entry points](https://packaging.python.org/en/latest/specifications/entry-points/) for discovery and registration. This makes it straightforward to develop and integrate your own ingestors.

## 2. The `IngestorPlugin` Protocol

To create a custom ingestor, you need to implement the `IngestorPlugin` protocol defined in `arc_memory.plugins`. This protocol specifies the methods your ingestor class must provide.

Here is the Python definition of the `IngestorPlugin` protocol:

```python
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable
from pathlib import Path
from arc_memory.schema.models import Node, Edge

@runtime_checkable
class IngestorPlugin(Protocol):
    """
    Protocol for data ingestion plugins.
    Plugins implementing this protocol can be discovered and used by Arc Memory.
    """

    def get_name(self) -> str:
        """
        Return a unique name for this plugin (e.g., "my_custom_source").
        This name will be used for configuration and identification.
        """
        ...

    def get_node_types(self) -> List[str]:
        """
        Return a list of node type strings that this plugin can create.
        These should correspond to types defined in arc_memory.schema.models.NodeType
        or custom types if necessary.
        Example: return [NodeType.ISSUE.value, "my_custom_node_type"]
        """
        ...

    def get_edge_types(self) -> List[str]:
        """
        Return a list of edge relation strings that this plugin can create.
        These should correspond to types defined in arc_memory.schema.models.EdgeRel
        or custom relation types.
        Example: return [EdgeRel.MENTIONS.value, "my_custom_relationship"]
        """
        ...

    def ingest(
        self,
        last_processed: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """
        Ingest data from the source and return nodes, edges, and metadata.

        Args:
            last_processed: A dictionary containing metadata from the previous
                            successful run of this ingestor. Use this for
                            incremental data fetching (e.g., using a timestamp
                            or last processed ID). Defaults to None if it's the
                            first run or the previous run failed to return metadata.
            **kwargs:      Additional keyword arguments.
                           - repo_path (Optional[Path]): Path to the repository,
                             if the ingestor is repository-specific and the core
                             system provides it.
                           - Plugin-specific configurations: Any configurations
                             passed via the `source_configs` parameter of
                             `Arc.build()` or `Arc.build_repository()`. The key
                             for this plugin's specific config in `source_configs`
                             will match the plugin's name from `get_name()`.
                             For example, if get_name() returns "my_data_source",
                             and source_configs={"my_data_source": {"api_key": "xyz"}},
                             then kwargs will contain {"api_key": "xyz"}.

        Returns:
            A tuple containing:
            - List[Node]: A list of Node objects created from the data source.
            - List[Edge]: A list of Edge objects representing relationships.
            - Dict[str, Any]: Metadata to be stored for the next incremental run.
                              This dictionary will be passed as `last_processed`
                              in the next invocation.
                              Example: {"timestamp": "2023-10-26T10:00:00Z", "last_item_id": "item_123"}
        """
        ...
```

### Method Details:

*   **`get_name(self) -> str`**:
    *   **Purpose**: This method must return a unique string name for your plugin (e.g., `"my_company_wiki"`, `"custom_jira_instance"`).
    *   This name is crucial as it's used:
        *   To identify the plugin in logs and summaries.
        *   As the key in the `source_configs` dictionary when users provide configuration to your plugin.
        *   As the name for the entry point when registering the plugin.

*   **`get_node_types(self) -> List[str]`**:
    *   **Purpose**: Should return a list of strings representing the types of nodes your plugin can generate.
    *   It's recommended to use values from the `arc_memory.schema.models.NodeType` enum (e.g., `NodeType.DOCUMENT.value`, `NodeType.ISSUE.value`) for standard types.
    *   You can also define custom node types if necessary (e.g., `"my_custom_object_type"`).

*   **`get_edge_types(self) -> List[str]`**:
    *   **Purpose**: Should return a list of strings representing the types of relationships (edges) your plugin can create between nodes.
    *   It's recommended to use values from the `arc_memory.schema.models.EdgeRel` enum (e.g., `EdgeRel.MENTIONS.value`, `EdgeRel.CONTAINS.value`).
    *   Custom relationship types are also permitted.

*   **`ingest(self, last_processed: Optional[Dict[str, Any]] = None, **kwargs: Any) -> tuple[List[Node], List[Edge], Dict[str, Any]]`**:
    *   This is the core method where data fetching and processing occur.
    *   **`last_processed: Optional[Dict[str, Any]]`**:
        *   A dictionary containing metadata from the *previous successful run* of this specific ingestor.
        *   On the first run, or if the previous run didn't return metadata (e.g., it failed), this will be `None`.
        *   Use this to fetch data incrementally. For example, if your previous run stored `{"last_fetch_timestamp": "2023-01-01T00:00:00Z"}`, you can now fetch items created or updated after this time.
    *   **`**kwargs: Any`**:
        *   This dictionary captures all other keyword arguments passed to the ingestor.
        *   **`repo_path: Path`**: If your ingestor operates on a specific code repository (like the built-in Git or ADR ingestors), the Arc Memory system may pass the `repo_path` as a `pathlib.Path` object in `kwargs`. Your plugin should check for its presence if it needs it.
        *   **Plugin-specific configurations**: Users can provide configurations to your plugin via the `source_configs` argument of `Arc.build()` or `Arc.build_repository()`. The configuration for your plugin will be available in `kwargs` directly. For example, if `get_name()` returns `"my_custom_source"` and the user calls `arc.build(source_configs={"my_custom_source": {"api_key": "xyz123", "limit": 100}})`, then within your `ingest` method, `kwargs` will contain `{"api_key": "xyz123", "limit": 100}` (potentially alongside `repo_path`).
    *   **Return Tuple (`Tuple[List[Node], List[Edge], Dict[str, Any]]`)**:
        *   `List[Node]`: A list of `arc_memory.schema.models.Node` objects created from the data source.
        *   `List[Edge]`: A list of `arc_memory.schema.models.Edge` objects representing relationships between nodes (or between these nodes and existing nodes in the graph).
        *   `Dict[str, Any]`: A metadata dictionary that will be saved by Arc Memory and passed back to your plugin as the `last_processed` argument in its next run. This is essential for incremental ingestion. Store information like the timestamp of the latest processed item, a pagination cursor, or the ID of the last item fetched. Example: `{"timestamp": datetime.now().isoformat(), "last_item_id": "some_id"}`.

## 3. Example Implementation

Here's a skeleton for a custom ingestor. This example demonstrates how to structure the class, access configurations, and outlines where to place your data fetching logic.

```python
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from arc_memory.plugins import IngestorPlugin # Assuming this is where the protocol is defined
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel # Import necessary schema items
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

class MyCustomIngestor:
    """
    An example custom ingestor for a hypothetical data source.
    """

    def get_name(self) -> str:
        return "my_custom_source"

    def get_node_types(self) -> List[str]:
        return [NodeType.DOCUMENT.value, "my_custom_entity_type"]

    def get_edge_types(self) -> List[str]:
        return [EdgeRel.CONTAINS.value]

    def ingest(
        self,
        last_processed: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        nodes: List[Node] = []
        edges: List[Edge] = []
        
        # Access configurations
        api_key = kwargs.get("api_key")
        target_id = kwargs.get("target_id")
        repo_path: Optional[Path] = kwargs.get("repo_path")

        if not api_key:
            api_key = os.environ.get("MYCUSTOMSOURCE_API_KEY")
            if not api_key:
                logger.warning("API key for MyCustomIngestor not found in config or environment. Skipping.")
                return [], [], {} # Return empty data and no metadata to save

        logger.info(f"Starting ingestion for {self.get_name()} with target_id: {target_id}")
        if repo_path:
            logger.info(f"Repository path provided: {repo_path}")

        # Incremental processing logic
        since_timestamp_str = None
        if last_processed:
            since_timestamp_str = last_processed.get("latest_item_timestamp")
            logger.info(f"Incremental run: fetching items since {since_timestamp_str}")

        # --- Placeholder for your data fetching logic ---
        # Example:
        # try:
        #     raw_items = self._fetch_data_from_source(api_key, target_id, since_timestamp_str)
        # except Exception as e:
        #     logger.error(f"Failed to fetch data from source: {e}")
        #     # Depending on severity, you might return [], [], last_processed to retry with same state,
        #     # or raise an exception to mark the ingestor as failed for this run.
        #     raise IngestorError(f"API request failed: {e}") from e # Custom IngestorError
        raw_items = [] # Replace with actual data fetching

        latest_processed_item_timestamp = None

        for item_data in raw_items:
            # --- Placeholder for transforming raw_item into Node and Edge objects ---
            item_id = item_data.get("id")
            item_title = item_data.get("title", f"Item {item_id}")
            item_content = item_data.get("content", "")
            item_created_at_str = item_data.get("created_at") # Assuming ISO format string
            
            item_created_at = None
            if item_created_at_str:
                try:
                    item_created_at = datetime.fromisoformat(item_created_at_str.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Could not parse timestamp: {item_created_at_str} for item {item_id}")

            node = Node(
                id=f"{self.get_name()}:{item_id}",
                type=NodeType.DOCUMENT.value, # Or your custom type
                title=item_title,
                body=item_content,
                ts=item_created_at, # Timestamp of the item
                metadata={
                    "source_plugin": self.get_name(),
                    "original_id": item_id,
                    # Add other relevant metadata
                }
            )
            nodes.append(node)

            # Example of updating the latest timestamp for incremental processing
            if item_created_at:
                if latest_processed_item_timestamp is None or item_created_at > latest_processed_item_timestamp:
                    latest_processed_item_timestamp = item_created_at
            
            # Create edges if applicable
            # parent_id = item_data.get("parent_id")
            # if parent_id:
            #     edge = Edge(
            #         src=f"{self.get_name()}:{parent_id}", # Assuming parent is also from this source
            #         dst=node.id,
            #         rel=EdgeRel.CONTAINS.value
            #     )
            #     edges.append(edge)

        # --- End of placeholder ---

        new_metadata: Dict[str, Any] = {}
        if latest_processed_item_timestamp:
            new_metadata["latest_item_timestamp"] = latest_processed_item_timestamp.isoformat()
        else:
            # If no new items were processed, carry over the old timestamp if it exists
            if since_timestamp_str:
                 new_metadata["latest_item_timestamp"] = since_timestamp_str


        logger.info(f"Ingested {len(nodes)} nodes and {len(edges)} edges for {self.get_name()}.")
        return nodes, edges, new_metadata

# Make sure your class implements the protocol
assert isinstance(MyCustomIngestor(), IngestorPlugin)
```

## 4. Handling Authentication

Securely managing credentials for your data source is important. Here are common approaches:

*   **Environment Variables**: For API keys or simple tokens, environment variables are a good practice.
    ```python
    api_key = os.environ.get("MYPLUGIN_API_KEY")
    if not api_key:
        logger.error("MYPLUGIN_API_KEY environment variable not set.")
        # Handle missing key, perhaps by returning no data
    ```
*   **Configuration via `source_configs`**: Non-sensitive configurations, or even API keys if the user prefers, can be passed at runtime using the `source_configs` argument of `Arc.build()`. Your plugin will receive these in the `**kwargs` of the `ingest` method.
    ```python
    # In your ingest method:
    api_key = kwargs.get("api_key")
    # ...
    ```
*   **OAuth or Complex Flows**: For services requiring OAuth 2.0 or more complex authentication:
    *   Your plugin might need to implement the necessary steps of the OAuth flow (e.g., redirecting the user, handling callbacks if it's a local application, or using a device flow).
    *   Consider using a library like `requests-oauthlib`.
    *   Securely store tokens. The `keyring` library (used by Arc Memory's built-in auth modules like `arc_memory.auth.github`) is a good option for storing tokens in the system's keychain. You would need to manage token fetching, storage, and refresh logic within your plugin.

## 5. Providing Configuration to Your Plugin

Users of your custom ingestor can provide configurations specific to it when building the knowledge graph. This is done using the `source_configs` argument in `Arc.build()` or `Arc.build_repository()`.

The `source_configs` argument is a dictionary where keys are ingestor names (as returned by `get_name()`) and values are dictionaries of configurations for that ingestor.

**Example**:

Assume your `MyCustomIngestor` has `get_name()` returning `"my_custom_source"`, and it expects `api_key` and `target_id` as configurations. A user would call:

```python
from arc_memory.sdk import Arc

# Initialize Arc SDK (repo_path might be optional depending on your setup)
arc_instance = Arc(repo_path=".")

# Configurations for your custom ingestor
custom_source_config = {
    "api_key": "your_secure_api_key_here",
    "target_id": "some_specific_id_for_the_source",
    "another_param": "value"
}

# Build the graph, passing configurations
arc_instance.build(
    source_configs={
        "my_custom_source": custom_source_config,
        # ... other ingestor configs if needed
    }
)
```

Inside your `MyCustomIngestor.ingest(**kwargs)` method, `kwargs` would then contain:
`{'api_key': 'your_secure_api_key_here', 'target_id': 'some_specific_id_for_the_source', 'another_param': 'value'}`
(potentially along with `repo_path` if provided by the core system).

## 6. Packaging and Registration

For Arc Memory to discover and use your custom ingestor, it must be packaged as a Python library and registered using an entry point.

**Using `pyproject.toml` (Recommended)**:

If your plugin is packaged in a project named `my-arc-plugin-package` and your `MyCustomIngestor` class is in `my_plugin_package/module.py`, you would add the following to your plugin's `pyproject.toml` file:

```toml
[project.entry-points."arc_memory.plugins"]
my_custom_source = "my_plugin_package.module:MyCustomIngestor"
```

*   `arc_memory.plugins`: This is the entry point group Arc Memory uses to find ingestor plugins.
*   `my_custom_source`: This is the name of your entry point. It's **crucial** that this name matches the string returned by your ingestor's `get_name()` method.
*   `my_plugin_package.module:MyCustomIngestor`: This is the fully qualified path to your ingestor class (`package.module:ClassName`).

After installing your plugin package (e.g., via `pip install .` in your plugin's directory), Arc Memory will automatically discover and load it when `get_ingestor_plugins()` is called.

**Using `setup.py` (for older packaging systems)**:

If you are using an older `setup.py`-based packaging system, the equivalent declaration would be:

```python
# In setup.py
from setuptools import setup

setup(
    # ... other setup arguments
    entry_points={
        "arc_memory.plugins": [
            "my_custom_source = my_plugin_package.module:MyCustomIngestor",
        ]
    },
)
```

## 7. Best Practices

*   **Logging**:
    *   Use Arc Memory's logging configuration for consistent output.
    *   Import and use the logger: `from arc_memory.logging_conf import get_logger; logger = get_logger(__name__)`.
    *   Log important events, warnings, and errors within your plugin.

*   **Error Handling**:
    *   Catch specific exceptions that your data source's API client might raise (e.g., `requests.exceptions.HTTPError`, custom API client exceptions).
    *   If an error is recoverable for a single item (e.g., one malformed record), log the error and skip that item, allowing the rest of the ingestion to proceed.
    *   If a critical error occurs that prevents the entire ingestion (e.g., authentication failure, API endpoint down), your plugin can raise an exception. This exception will be caught by Arc Memory's main build loop, and the failure of your ingestor (along with the error message) will be recorded in the `ingestor_summary` part of the build results. Consider defining custom exceptions for your plugin for clarity.

*   **Schema Adherence**:
    *   Ensure that the `Node` and `Edge` objects you create conform to the schema defined in `arc_memory.schema.models`.
    *   Use the `NodeType` and `EdgeRel` enums for standard types to maintain consistency with the rest of the knowledge graph.
    *   Populate relevant fields like `id`, `type`, `title`, `body`, and `ts` (timestamp). Store additional source-specific information in the `metadata` dictionary of nodes and the `properties` dictionary of edges.

*   **Incremental Ingestion**:
    *   If your data source supports fetching data incrementally (e.g., based on update timestamps, creation dates, or pagination cursors), implement this logic using the `last_processed` dictionary.
    *   In the metadata dictionary returned by your `ingest` method, store the necessary information (like the latest timestamp of processed items, the next page cursor, or the ID of the last item fetched) to allow the next run to pick up where the current one left off. This significantly improves efficiency for subsequent builds.

*   **Dependencies**:
    *   If your plugin requires external Python libraries (e.g., an API client for the data source, data processing libraries), declare them as dependencies in your plugin's `pyproject.toml` (under `[project.dependencies]`). This ensures they are installed when a user installs your plugin.
```
