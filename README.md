# Arc Memory

Arc Memory embeds a local, bi-temporal knowledge graph (TKG) in every developer's workspace. It surfaces verifiable decision trails during code-review and exposes the same provenance to any LLM-powered agent through VS Code's Agent Mode.

## Features

- Build a local knowledge graph from Git commits, GitHub PRs, issues, and ADRs
- Fast API to trace history from file+line to related commits, PRs, issues, and ADRs
- Support for incremental builds to efficiently update the graph
- CI integration for team-wide graph updates

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
```

## Documentation

For full documentation, visit [arc.computer](https://www.arc.computer).

## Architecture

Arc Memory consists of three components:

1. **arc-memory** (this package) - Python library and CLI for graph building
2. **arc-memory-mcp** - Local daemon exposing API endpoints
3. **vscode-arc** - VS Code extension for displaying decision trails

See our [Architecture Decision Records](./docs/adr/) for more details on design decisions.

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
# Run tests
pytest

# Run tests with coverage
pytest --cov=arc_memory
```

## License

MIT
