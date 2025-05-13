# Arc Memory Documentation

Arc Memory is a memory layer for engineering teams that builds a local, bi-temporal knowledge graph from Git repositories, GitHub issues/PRs, and ADRs. It provides a framework-agnostic SDK for querying and modifying this knowledge graph, with adapters for popular agent frameworks like LangChain and OpenAI.

## Getting Started

- [Getting Started Guide](./getting_started.md) - Step-by-step guide to installing Arc Memory and building your first knowledge graph
- [SDK Documentation](./sdk/README.md) - Overview of the Arc Memory SDK
- [Example Agents](./examples/README.md) - Ready-to-use example agents that demonstrate Arc Memory's capabilities

## Core Concepts

- **Knowledge Graph**: Arc Memory builds a knowledge graph from various sources, including Git repositories, GitHub issues/PRs, and ADRs.
- **Bi-Temporal Data Model**: Arc Memory's bi-temporal data model tracks both when something happened in the real world and when it was recorded in the system.
- **Causal Relationships**: Arc Memory captures causal relationships between entities, enabling powerful reasoning about why code exists.
- **Framework Adapters**: Arc Memory provides adapters for popular agent frameworks, making it easy to integrate with your existing tools.

## SDK Reference

- [API Reference](./sdk/api_reference.md) - Detailed documentation of the Arc Memory SDK API
- [Framework Adapters](./sdk/adapters.md) - Documentation for the framework adapters

## Command Line Interface

Arc Memory also provides a command line interface for building and querying the knowledge graph:

```bash
# Build a knowledge graph
arc build

# Query the knowledge graph
arc query "Why was the authentication system refactored?"

# Get the decision trail for a specific line in a file
arc why src/auth/login.py:42

# Find entities related to a specific entity
arc relate commit:abc123
```

For more information on the CLI, see the [CLI Documentation](./cli/README.md).

## Architecture and Design

- [ADR-001: Incremental Builds](./adr/ADR-001-Incremental-Builds.md)
- [ADR-002: Data Model Refinements](./adr/ADR-002-Data-Model-Refinements.md)
- [ADR-003: Plugin Architecture](./adr/ADR-003-Plugin-Architecture.md)

## Guides

- [GitHub Integration](./guides/github_integration.md)
- [Troubleshooting](./guides/troubleshooting.md)
- [Dependencies](./guides/dependencies.md)
- [Test Environment](./guides/test_environment.md)
- [ADR Formatting](./guides/adr-formatting.md)
