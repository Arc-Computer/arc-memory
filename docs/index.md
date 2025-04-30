# Arc Memory CLI Documentation

Welcome to the Arc Memory CLI documentation. This guide will help you get started with Arc Memory, a comprehensive command-line tool that provides a local bi-temporal knowledge graph for software engineering.

## Getting Started

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Documentation Overview](#documentation-overview)

## Installation

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

## Documentation Overview

### Guides

- [Dependencies Guide](./guides/dependencies.md) - Complete list of dependencies
- [Test Environment Setup](./guides/test-environment.md) - Setting up a test environment
- [Troubleshooting](./guides/troubleshooting.md) - Common issues and solutions

### CLI Commands

#### Building & Setup
- [Authentication](./cli/auth.md) - GitHub authentication commands
  - `arc auth gh` - Authenticate with GitHub
  - `arc auth gh-app` - Authenticate with a GitHub App

- [Build](./cli/build.md) - Building the knowledge graph
  - `arc build` - Build the knowledge graph from Git, GitHub, and ADRs

- [Doctor](./cli/doctor.md) - Checking graph status and diagnostics
  - `arc doctor` - Check the status of the Arc Memory database

#### Querying & Exploration
- [Why](./cli/why.md) - Show decision trail for a file line
  - `arc why file` - Show the decision trail for a specific line in a file

- [Relate](./cli/relate.md) - Show related nodes for an entity
  - `arc relate node` - Show nodes related to a specific entity

- [Trace](./cli/trace.md) - Legacy tracing history for files and lines
  - `arc trace file` - Trace the history of a specific line in a file

#### Integration & Serving
- [Serve](./cli/serve.md) - Serve the knowledge graph via MCP
  - `arc serve start` - Start the MCP server
  - `arc serve status` - Check the status of the MCP server

### Usage Examples

- [Building Graphs](./examples/building-graphs.md) - Examples of building knowledge graphs
  - Basic graph building
  - Incremental builds
  - Limiting the build scope
  - Custom output location
  - CI/CD integration

- [Tracing History](./examples/tracing-history.md) - Examples of tracing history
  - Basic history tracing
  - Adjusting search depth and results
  - Finding the decision behind a feature
  - Programmatic tracing

- [SDK Usage](./examples/sdk-usage.md) - Using the SDK
  - Basic SDK operations
  - CI/CD pipelines

- [Custom Plugins](./examples/custom-plugins.md) - Creating custom data source plugins
  - Basic plugin template
  - Notion plugin example
  - Jira plugin example
  - Best practices

### API Documentation

- [Build API](./api/build.md) - Build process API
  - Building the knowledge graph
  - Incremental builds
  - Plugin integration

- [Trace API](./api/trace.md) - Trace history API
  - Tracing history for a file line
  - Graph traversal
  - Performance considerations

- [Models](./api/models.md) - Data models
  - Node types
  - Edge types
  - Build manifest

- [Plugins](./api/plugins.md) - Plugin architecture API
  - Plugin interface
  - Plugin registry
  - Plugin discovery

### Architecture

- [Plugin Architecture](./plugin-architecture.md) - Technical details of the plugin system
- [Performance Benchmarks](./performance-benchmarks.md) - Performance metrics and benchmarks

### Architecture Decision Records (ADRs)

- [ADR-001: Knowledge Graph Schema](./adr/001-knowledge-graph-schema.md)
- [ADR-002: Data Model Refinements](./adr/002-data-model-refinements.md)
- [ADR-003: Plugin Architecture](./adr/003-plugin-architecture.md)

## Common Tasks

### Building a Knowledge Graph

To build a knowledge graph for your repository:

```bash
# Navigate to your repository
cd /path/to/your/repo

# Authenticate with GitHub (if needed)
arc auth gh

# Build the knowledge graph
arc build
```

For more details, see [Building Graphs](./examples/building-graphs.md).

### Understanding Decision Trails

To show the decision trail for a specific line in a file:

```bash
arc why file path/to/file.py 42
```

For more details, see [Tracing History](./examples/tracing-history.md).

### Exploring Relationships

To show nodes related to a specific entity:

```bash
arc relate node commit:abc123
```

For more details, see [Tracing History](./examples/tracing-history.md).

### Creating a Custom Plugin

To create a custom plugin for Arc Memory:

1. Create a class that implements the `IngestorPlugin` protocol
2. Register your plugin using entry points
3. Package and distribute your plugin

For more details, see [Custom Plugins](./examples/custom-plugins.md).

## Troubleshooting

If you encounter issues with Arc Memory:

1. Check the [Troubleshooting Guide](./guides/troubleshooting.md) for common issues and solutions
2. Use the [Doctor](./cli/doctor.md) command for diagnostics
3. Look for specific troubleshooting sections in each command's documentation
4. Enable debug logging with the `--debug` flag
5. Check the [Dependencies Guide](./guides/dependencies.md) to ensure all requirements are met

## Getting Help

If you need additional help:

- Visit [arc.computer](https://www.arc.computer) for more resources
- Open an issue on [GitHub](https://github.com/Arc-Computer/arc-memory/issues)
- Check the [FAQ](https://www.arc.computer/faq) for common questions
