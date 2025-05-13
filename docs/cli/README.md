# Arc Memory CLI

The Arc Memory Command Line Interface (CLI) provides a convenient way to build and query the knowledge graph from the command line. While the [SDK](../sdk/README.md) is recommended for programmatic access and agent integration, the CLI is useful for quick queries and manual exploration.

## Installation

```bash
pip install arc-memory
```

## Basic Commands

### Building the Knowledge Graph

```bash
# Build a knowledge graph for the current repository
arc build

# Build with GitHub data
arc build --github

# Build with Linear data
arc build --linear
```

### Querying the Knowledge Graph

```bash
# Query the knowledge graph
arc query "Why was the authentication system refactored?"

# Get the decision trail for a specific line in a file
arc why src/auth/login.py:42

# Find entities related to a specific entity
arc relate commit:abc123

# Trace the history of a file
arc trace src/auth/login.py
```

### Authentication

```bash
# Authenticate with GitHub
arc auth github

# Authenticate with Linear
arc auth linear
```

### Serving the Knowledge Graph

```bash
# Start the web server
arc serve

# Start the web server on a specific port
arc serve --port 8080
```

## Relationship with the SDK

The CLI is built on top of the same core functionality as the SDK. In fact, most CLI commands are thin wrappers around SDK methods:

| CLI Command | SDK Equivalent |
|-------------|----------------|
| `arc query` | `arc.query()` |
| `arc why` | `arc.get_decision_trail()` |
| `arc relate` | `arc.get_related_entities()` |
| `arc trace` | `arc.get_entity_history()` |

For more advanced use cases, especially those involving agent integration, we recommend using the SDK directly. See the [SDK Documentation](../sdk/README.md) for more information.
