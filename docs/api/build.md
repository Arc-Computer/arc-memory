# Build Process API

The Build Process API allows you to build a knowledge graph from Git commits, GitHub PRs and issues, and ADRs.

## Overview

The build process discovers and executes plugins to ingest data from various sources, creates nodes and edges in the knowledge graph, and saves the result to a SQLite database. It supports both full and incremental builds, allowing for efficient updates to the graph.

## Key Functions

### CLI Command: `arc build`

```bash
arc build [OPTIONS]
```

This is the main entry point for building the knowledge graph.

#### Options

- `--repo`, `-r`: Path to the Git repository (default: current directory)
- `--output`, `-o`: Path to the output database file (default: ~/.arc/graph.db)
- `--max-commits`: Maximum number of commits to process (default: 5000)
- `--days`: Maximum age of commits to process in days (default: 365)
- `--incremental`: Only process new data since last build (default: False)
- `--pull`: Pull the latest CI-built graph (not implemented yet)
- `--token`: GitHub token to use for API calls
- `--debug`: Enable debug logging

#### Example

```bash
# Build the knowledge graph for the current repository
arc build

# Build incrementally
arc build --incremental

# Build with a specific GitHub token
arc build --token ghp_1234567890abcdef

# Build with custom limits
arc build --max-commits 1000 --days 30
```

## Build Process Flow

The build process follows these steps:

1. **Initialization**:
   - Ensure the output directory exists
   - Check if the repository is a Git repository
   - Load existing manifest for incremental builds
   - Initialize the database

2. **Plugin Discovery**:
   - Discover and register plugins using the plugin registry
   - Plugins are discovered using entry points

3. **Data Ingestion**:
   - For each plugin:
     - Get last processed data (for incremental builds)
     - Call the plugin's `ingest` method with appropriate parameters
     - Collect nodes and edges from the plugin

4. **Database Operations**:
   - Write all nodes and edges to the database
   - Get node and edge counts
   - Compress the database

5. **Manifest Creation**:
   - Create a build manifest with metadata about the build
   - Save the manifest for future incremental builds

## Incremental Builds

Incremental builds only process new data since the last build, making them much faster than full builds. The process works as follows:

1. Load the existing build manifest
2. Pass the last processed data to each plugin
3. Plugins use this data to determine what's new
4. Only new nodes and edges are added to the database

## Plugin Integration

The build process integrates with plugins through the plugin registry. Each plugin must implement the `IngestorPlugin` protocol, which includes:

- `get_name()`: Returns the name of the plugin
- `get_node_types()`: Returns the node types the plugin can create
- `get_edge_types()`: Returns the edge types the plugin can create
- `ingest()`: Ingests data and returns nodes, edges, and metadata

Special handling is provided for certain plugins:

- **Git Plugin**: Receives `max_commits` and `days` parameters
- **GitHub Plugin**: Receives a `token` parameter

## Error Handling

The build process includes comprehensive error handling:

- Specific `GraphBuildError` for build-related errors
- Detailed error messages for common issues
- Graceful handling of plugin failures
- Debug logging for troubleshooting

## Performance

The build process is designed for performance:

- Incremental builds are very fast (typically < 0.5 seconds)
- Full builds scale linearly with repository size
- Database compression reduces storage requirements

## Build Manifest

The build manifest is a JSON file that stores metadata about the build:

```python
class BuildManifest(BaseModel):
    schema_version: str
    build_time: datetime
    commit: Optional[str]
    node_count: int
    edge_count: int
    last_processed: Dict[str, Dict[str, Any]]
```

This manifest is used for incremental builds and provides a record of the build process.
