# Arc Memory Documentation

Arc Memory is a memory layer for engineering teams that builds a local, bi-temporal knowledge graph from Git repositories, GitHub issues/PRs, and ADRs. It provides a framework-agnostic SDK for querying and modifying this knowledge graph, with adapters for popular agent frameworks like LangChain and OpenAI.

## Why Arc Memory?

Ever stared at a piece of code wondering "what were they thinking?" We've all been there. Maintenance becomes difficult, bugs reappear, and onboarding new developers takes months.

Arc connects the dots between code, decisions, and context that typically gets lost in Slack threads, PR comments, and the minds of developers who've since moved on.

### The "Why" Behind Code

Code tells you what it does, but not why it exists. Arc Memory preserves the reasoning, trade-offs, and decisions that shaped your codebase. Instead of archeology, you get answers:

```bash
> arc query "Why does the auth system use JWT instead of session cookies?"

The JWT implementation was chosen in PR #142 (March 2023) because:
1. It simplified the microservice architecture by removing shared session state
2. It addressed performance issues with Redis session store (Issue #98)
3. The team accepted the trade-off of slightly larger request headers
```

### Predict Change Impact

Making changes without understanding dependencies is like performing surgery blindfolded. Arc Memory shows you what might break before you commit:

```bash
> arc analyze-impact src/api/payment.js

High-risk dependencies:
- src/services/stripe.js (Impact score: 0.92)
- src/models/subscription.js (Impact score: 0.87)
- 3 tests likely to fail
```

### Break Knowledge Silos

Stop waiting for the one developer who understands the payment system to come back from vacation. Arc Memory democratizes access to system knowledge through natural language:

```bash
> arc why src/billing/invoice.py:42

This code handles pro-rating for mid-month plan changes.
It was implemented by @alex in response to Issue #234.
The complex calculation addresses edge cases discovered
during the 2022 pricing change (see ADR-012).
```

### Shared Memory for Humans and Agents

As teams deploy more AI agents, Arc Memory provides the shared context layer they need to work together effectively, reducing duplicate work and conflicting changes.

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
# Authenticate with GitHub (needed for issues/PRs)
arc auth github

# Authenticate with Linear (needed for tickets)
arc auth linear

# Build a knowledge graph
arc build

# Build with GitHub and Linear data
arc build --github --linear

# Build with LLM enhancement
arc build --github --linear --llm-enhancement

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
