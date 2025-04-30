# Arc Memory CLI

<p align="center">
  <img src="public/arc_logo.png" alt="Arc Logo" width="200"/>
</p>

<p align="center">
  <a href="https://www.arc.computer"><img src="https://img.shields.io/badge/website-arc.computer-blue" alt="Website"/></a>
  <a href="https://github.com/Arc-Computer/arc-memory/actions"><img src="https://img.shields.io/badge/tests-passing-brightgreen" alt="Tests"/></a>
  <a href="https://pypi.org/project/arc-memory/"><img src="https://img.shields.io/pypi/v/arc-memory" alt="PyPI"/></a>
  <a href="https://pypi.org/project/arc-memory/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue" alt="Python"/></a>
  <a href="https://github.com/Arc-Computer/arc-memory/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Arc-Computer/arc-memory" alt="License"/></a>
  <a href="https://docs.arc.computer"><img src="https://img.shields.io/badge/docs-mintlify-teal" alt="Documentation"/></a>
</p>

At Arc, we're building the foundational memory layer for modern software engineering. Our mission is simple but powerful: ensure engineering teams never lose the critical "why" behind their code. We bridge the gap between human decisions and machine understanding, becoming the temporal source-of-truth for every engineering team and their AI agents.

## Overview

Arc Memory is a comprehensive CLI tool that embeds a local, bi-temporal knowledge graph (TKG) in every developer's workspace. It surfaces verifiable decision trails during code-review and exposes the same provenance to any LLM-powered agent through VS Code's Agent Mode.

## Arc Memory Ecosystem

The Arc Memory CLI is part of a broader ecosystem that connects your team's collective history to AI assistants:

<div align="center">
  <img src="public/arc-vision-diagram.png" alt="Arc Memory Ecosystem Diagram" width="1200"/>
</div>

### How It Works

- **Data Sources** (G-Suite, Slack, Notion, GitHub, Jira) seamlessly feed into the **Arc Memory CLI**, which captures organizational decisions in a local-first Temporal Knowledge Graph (TKG).

- The **Arc MCP Server** provides persistent, cross-repository decision context, enabling memory-aware multi-step reasoning for integrated tooling.

- Through the **VS Code Extension**, developers interact directly with decision trails embedded into code reviews, and leverage verifiable citations and team-wide search across organizational decisions.

Together, these components form the foundation for **organizational intelligence**, empowering sophisticated reasoning and enabling AI agents to build robust world models from your team's collective history.

## Arc Memory Features

- **Comprehensive Knowledge Graph** - Build a local graph from Git commits, GitHub PRs, issues, and ADRs
- **Decision Trail Visualization** - Understand the "why" behind code with `arc why` command
- **Relationship Exploration** - Discover connections between entities with `arc relate` command
- **High Performance** - Queries complete in under 200ms (typically ~100μs)
- **Incremental Builds** - Efficiently update the graph with only new data
- **MCP Integration** - Connect to AI assistants via Anthropic's Model Context Protocol
- **Privacy-First** - All data stays on your machine; no code or IP leaves your repo
- **Extensible Plugin Architecture** - Easily add new data sources beyond Git, GitHub, and ADRs
- **CI Integration** - Team-wide graph updates through CI workflows

## Installation

Arc Memory requires Python 3.10 or higher and is compatible with Python 3.10, 3.11, and 3.12.

```bash
pip install arc-memory
```

Or using UV:

```bash
uv pip install arc-memory
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

# Show decision trail for a specific file and line
arc why file path/to/file.py 42

# Show related nodes for a specific entity
arc relate node commit:abc123

# Serve the knowledge graph via MCP
arc serve start
```

## Telemetry

Arc Memory includes optional, privacy-respecting telemetry to help us improve the product:

- **Anonymous**: No personally identifiable information is collected
- **Opt-in**: Disabled by default, enable with `arc config telemetry on`
- **Transparent**: All collected data is documented and visible
- **Focused**: Only collects command usage and session metrics for MTTR measurement

Telemetry is disabled by default. To enable it: `arc config telemetry on`
To disable telemetry: `arc config telemetry off`

## Documentation

### CLI Commands

#### Building & Setup
- [Authentication](./docs/cli/auth.md) - GitHub authentication commands (`arc auth`)
- [Build](./docs/cli/build.md) - Building the knowledge graph (`arc build`)
- [Doctor](./docs/cli/doctor.md) - Checking graph status and diagnostics (`arc doctor`)

#### Querying & Exploration
- [Why](./docs/cli/why.md) - Show decision trail for a file line (`arc why`)
- [Relate](./docs/cli/relate.md) - Show related nodes for an entity (`arc relate`)
- [Trace](./docs/cli/trace.md) - Legacy tracing history for files and lines (`arc trace`)

#### Integration & Serving
- [Serve](./docs/cli/serve.md) - Serve the knowledge graph via MCP (`arc serve`)

### Usage Examples
- [Building Graphs](./docs/examples/building-graphs.md) - Examples of building knowledge graphs
- [Tracing History](./docs/examples/tracing-history.md) - Examples of tracing history
- [Custom Plugins](./docs/examples/custom-plugins.md) - Creating custom data source plugins

### API Documentation
- [Build API](./docs/api/build.md) - Build process API
- [Trace API](./docs/api/trace.md) - Trace history API
- [Models](./docs/api/models.md) - Data models
- [Plugins](./docs/api/plugins.md) - Plugin architecture API

For additional documentation, visit [arc.computer](https://www.arc.computer).

## Architecture

Arc Memory consists of three components:

1. **arc-memory** (this CLI) - Command-line interface and underlying SDK for graph building and querying
   - **CLI Commands** - User-friendly interface for building graphs and exploring history
   - **Local SQLite Database** - Stores the knowledge graph with direct access for CLI commands
   - **Plugin Architecture** - Extensible system for adding new data sources
   - **Trace History Algorithm** - BFS-based algorithm for traversing the knowledge graph

2. **arc-mcp-server** - MCP server exposing the knowledge graph to AI assistants
   - Available at [github.com/Arc-Computer/arc-mcp-server](https://github.com/Arc-Computer/arc-mcp-server)
   - Implements Anthropic's Model Context Protocol (MCP) for standardized AI tool access
   - Provides tools like `arc_trace_history`, `arc_get_entity_details`, and more
   - Can be started directly from the CLI with `arc serve start`

3. **vscode-arc-hover** - VS Code extension for displaying decision trails (in development)
   - Will integrate with the MCP server to display trace history
   - Will provide hover cards with decision trails
   - Will be available as a separate extension

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
python -m pytest

# Run integration tests
python -m pytest tests/integration

# Run performance benchmarks
python tests/benchmark/benchmark.py --repo-size small
```

### CLI Development

The Arc Memory CLI is built using [Typer](https://typer.tiangolo.com/), a modern library for building command-line interfaces in Python. The CLI commands are organized in the `arc_memory/cli/` directory:

```
arc_memory/cli/
├── __init__.py     # Main CLI entry point
├── auth.py         # Authentication commands
├── build.py        # Build commands
├── doctor.py       # Diagnostic commands
├── relate.py       # Relationship exploration commands
├── serve.py        # MCP server commands
├── trace.py        # Legacy trace commands
└── why.py          # Decision trail commands
```

To add a new command, create a new file in the `arc_memory/cli/` directory and register it in `__init__.py`.

### Creating a Plugin

Arc Memory uses a plugin architecture to support additional data sources. To create a new plugin:

1. Create a class that implements the `IngestorPlugin` protocol
2. Register your plugin using entry points
3. Package and distribute your plugin

Basic example:

```python
from arc_memory.plugins import IngestorPlugin
from arc_memory.schema.models import Node, Edge, NodeType, EdgeRel

class MyCustomPlugin(IngestorPlugin):
    def get_name(self) -> str:
        return "my-custom-source"

    def get_node_types(self) -> List[str]:
        return ["custom_node"]

    def get_edge_types(self) -> List[str]:
        return [EdgeRel.MENTIONS]

    def ingest(self, last_processed=None):
        # Your implementation here
        return nodes, edges, metadata
```

Register in `pyproject.toml`:
```toml
[project.entry-points."arc_memory.plugins"]
my-custom-source = "my_package.my_module:MyCustomPlugin"
```

For detailed instructions and examples, see:
- [Custom Plugins Guide](./docs/examples/custom-plugins.md) - Step-by-step guide with examples
- [Plugin Architecture](./docs/api/plugins.md) - Technical details of the plugin system
- [Plugins API](./docs/api/plugins.md) - API reference for plugin development

### Performance

Arc Memory is designed for high performance, with trace history queries completing in under 200ms (typically ~100μs). See our [performance benchmarks](./docs/performance-benchmarks.md) for more details.

## License

MIT