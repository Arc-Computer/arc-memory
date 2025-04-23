# Arc Memory

<p align="center">
  <img src="public/arc_logo.png" alt="Arc Logo" width="200"/>
</p>

## Vision

Software will soon be written by fleets of autonomous agents collaborating with humans.
That future needs a shared, trusted memory—one that captures not just what changed, but why every decision was made.

**Arc builds that memory:**

- **Temporal Knowledge Graph, in your IDE** – embeds commit history, PR rationales, issues and ADRs directly in VS Code, so every line knows its past.
- **Agent-ready API** – any LLM or tool can query the graph (`/searchEntity`, `/traceHistory`, `/openFile`, `/runTests`) to plan safe, multi-step fixes.
- **Local-first & privacy-first** – graphs are built in CI and stay on the developer's machine; no code or IP leaves your repo.
- **Verification layer for AI code** – provenance and test execution ensure AI-generated patches don't reopen old bugs or violate arch decisions.
- **Foundation for distributed AI systems** – scalable to monorepos and multi-service graphs, aligning with long-context frontier models.

**Mission:** Bridge the gap between human decisions and machine understanding, becoming the temporal source-of-truth for every engineering team and their agents.

## Overview

Arc Memory embeds a local, bi-temporal knowledge graph (TKG) in every developer's workspace. It surfaces verifiable decision trails during code-review and exposes the same provenance to any LLM-powered agent through VS Code's Agent Mode.

## Features

- **Extensible Plugin Architecture** - Easily add new data sources beyond Git, GitHub, and ADRs
- **Comprehensive Knowledge Graph** - Build a local graph from Git commits, GitHub PRs, issues, and ADRs
- **Trace History Algorithm** - Fast BFS algorithm to trace history from file+line to related entities
- **High Performance** - Trace history queries complete in under 200ms (typically ~100μs)
- **Incremental Builds** - Efficiently update the graph with only new data
- **Rich CLI** - Command-line interface for building graphs and tracing history
- **Privacy-First** - All data stays on your machine; no code or IP leaves your repo
- **CI Integration** - Team-wide graph updates through CI workflows

## Installation

```bash
pip install arc-memory
```

## Quick Start

```bash
# Authenticate with GitHub
arc auth gh

# Build the full knowledge graph
arc build

# Or update incrementally
arc build --incremental

# Check the graph status
arc doctor

# Trace history for a specific file and line
arc trace file path/to/file.py 42

# Trace with more hops in the graph
arc trace file path/to/file.py 42 --max-hops 3
```

## Documentation

For full documentation, visit [arc.computer](https://www.arc.computer).

## Architecture

Arc Memory consists of three components:

1. **arc-memory** (this package) - Python library and CLI for graph building and querying
   - **Plugin Architecture** - Extensible system for adding new data sources
   - **Trace History Algorithm** - BFS-based algorithm for traversing the knowledge graph
   - **CLI Commands** - Interface for building graphs and tracing history

2. **arc-memory-mcp** - Local daemon exposing API endpoints (future milestone)
   - Will provide HTTP API for VS Code extension and other tools
   - Will be implemented as a static binary in Go

3. **vscode-arc-hover** - VS Code extension for displaying decision trails (future milestone)
   - Will integrate with the MCP server to display trace history
   - Will provide hover cards with decision trails

See our [Architecture Decision Records](./docs/adr/) for more details on design decisions, including:
- [ADR-001: Knowledge Graph Schema](./docs/adr/001-knowledge-graph-schema.md)
- [ADR-002: Data Model Refinements](./docs/adr/002-data-model-refinements.md)
- [ADR-003: Plugin Architecture](./docs/adr/003-plugin-architecture.md)

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/arc-computer/arc-memory.git
cd arc-memory

# Create a virtual environment with UV
uv venv

# Activate the environment
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows

# Install dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run unit tests
python -m unittest discover

# Run integration tests
python -m unittest discover tests/integration

# Run performance benchmarks
python tests/benchmark/benchmark.py --repo-size small
```

### Creating a Plugin

Arc Memory uses a plugin architecture to support additional data sources. To create a new plugin:

1. Create a class that implements the `IngestorPlugin` protocol:

```python
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from arc_memory.schema.models import Edge, Node, NodeType, EdgeRel

class MyCustomIngestor:
    """Custom ingestor plugin for Arc Memory."""

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "my-custom-source"

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
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest data from the custom source."""
        # Your implementation here
        return [], [], {}
```

2. Register your plugin using entry points in your `setup.py`:

```python
setup(
    # ...
    entry_points={
        "arc_memory.plugins": [
            "my-custom-source = my_package.my_module:MyCustomIngestor",
        ],
    },
)
```

### Performance

Arc Memory is designed for high performance, with trace history queries completing in under 200ms (typically ~100μs). See our [performance benchmarks](./docs/performance-benchmarks.md) for more details.

## Current Status

Arc Memory is currently in active development. The core Python package (`arc-memory`) is functional and includes:

- ✅ Plugin Architecture - Extensible system for adding new data sources
- ✅ Knowledge Graph - Build a local graph from Git commits, GitHub PRs, issues, and ADRs
- ✅ Trace History Algorithm - BFS-based algorithm for traversing the knowledge graph
- ✅ CLI Commands - Interface for building graphs and tracing history

Upcoming milestones:

- 🔄 MCP Edge Server (`arc-memory-mcp`) - Local daemon exposing API endpoints
- 🔄 VS Code Extension (`vscode-arc-hover`) - Extension for displaying decision trails

See our [Week 2 Implementation Plan](./docs/week2.md) for more details on upcoming features.

## License

MIT
