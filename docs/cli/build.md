# Build Commands

The Arc Memory CLI provides commands for building the knowledge graph from Git commits, GitHub PRs and issues, and ADRs.

**Related Documentation:**
- [Authentication Commands](./auth.md) - Authenticate before building to include GitHub data
- [Doctor Commands](./doctor.md) - Verify your build status and graph statistics
- [Trace Commands](./trace.md) - Trace history after building your graph
- [Building Graphs Examples](../examples/building-graphs.md) - Detailed examples of building graphs

## Overview

The build process discovers and executes plugins to ingest data from various sources, creates nodes and edges in the knowledge graph, and saves the result to a SQLite database. It supports both full and incremental builds, allowing for efficient updates to the graph.

## Commands

### `arc build`

Build the knowledge graph from Git, GitHub, and ADRs.

```bash
arc build [OPTIONS]
```

This is the main command for building the knowledge graph. It processes data from all available plugins and creates a SQLite database containing the knowledge graph.

#### Options

- `--repo`, `-r TEXT`: Path to the Git repository (default: current directory).
- `--output`, `-o TEXT`: Path to the output database file (default: ~/.arc/graph.db).
- `--max-commits INTEGER`: Maximum number of commits to process (default: 5000).
- `--days INTEGER`: Maximum age of commits to process in days (default: 365).
- `--incremental`: Only process new data since last build (default: False).
- `--pull`: Pull the latest CI-built graph (not implemented yet).
- `--token TEXT`: GitHub token to use for API calls.
- `--debug`: Enable debug logging.

#### Examples

```bash
# Build the knowledge graph for the current repository
arc build

# Build incrementally (only process new data)
arc build --incremental

# Build with a specific GitHub token
arc build --token ghp_1234567890abcdef

# Build with custom limits
arc build --max-commits 1000 --days 30

# Build for a specific repository
arc build --repo /path/to/repo

# Build with a custom output path
arc build --output /path/to/output.db
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

To run an incremental build:

```bash
arc build --incremental
```

## Performance Considerations

### Build Times

The time required to build a knowledge graph depends on several factors:

| Repository Size | Commits | PRs/Issues | Estimated Full Build Time | Incremental Build Time |
|----------------|---------|------------|--------------------------|------------------------|
| Small          | &lt;500    | &lt;100       | 10-30 seconds            | &lt;1 second             |
| Medium         | 500-5000| 100-1000   | 1-5 minutes              | 1-3 seconds           |
| Large          | 5000+   | 1000+      | 5-15 minutes             | 3-10 seconds          |
| Very Large     | 10000+  | 5000+      | 15-60 minutes            | 10-30 seconds         |

These estimates assume:
- A modern computer (quad-core CPU, 8GB+ RAM)
- Good network connection for GitHub API calls
- GitHub API rate limits not being hit

### Resource Requirements

- **CPU**: The build process is multi-threaded and benefits from multiple cores
  - Minimum: Dual-core CPU
  - Recommended: Quad-core CPU or better

- **Memory**:
  - Minimum: 4GB RAM
  - Recommended: 8GB RAM
  - Large repositories (10000+ commits): 16GB RAM

- **Disk Space**:
  - Small repositories: ~10-50MB
  - Medium repositories: ~50-200MB
  - Large repositories: ~200MB-1GB
  - Very large repositories: 1GB+

- **Network**:
  - GitHub API calls require internet connectivity
  - Bandwidth requirements are modest, but latency can affect build times

### Optimizing Build Performance

1. **Use Incremental Builds**: After the initial build, always use `--incremental` for faster updates
2. **Limit Scope**: Use `--max-commits` and `--days` to limit the data processed
3. **GitHub Token**: Ensure you're authenticated to avoid rate limits
4. **Local Network**: Build on a fast, low-latency network connection
5. **SSD Storage**: Using SSD rather than HDD can significantly improve performance

## Troubleshooting

If you encounter issues during the build process:

1. **GitHub Rate Limiting**: If you hit GitHub API rate limits, provide a token with higher limits or wait and try again.
2. **Large Repositories**: For very large repositories, use the `--max-commits` and `--days` options to limit the amount of data processed.
3. **Debug Mode**: Run with `--debug` flag to see detailed logs: `arc build --debug`
4. **Database Corruption**: If the database becomes corrupted, delete it and run a full build again.
5. **Plugin Errors**: If a specific plugin fails, check its error message and ensure it has the necessary permissions and configuration.
