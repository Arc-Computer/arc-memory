# Serve Command

The Arc Memory CLI provides the `serve` command for serving the knowledge graph via the Model Context Protocol (MCP). This command allows AI assistants to access the knowledge graph for contextual retrieval and reasoning.

**Related Documentation:**
- [Build Commands](./build.md) - Build your knowledge graph before serving it
- [Why Commands](./why.md) - Show decision trail for a file line
- [Relate Commands](./relate.md) - Show related nodes for an entity

## Overview

The `serve` command starts the MCP server, which provides access to the knowledge graph via the Model Context Protocol. This allows AI assistants like Claude to access the knowledge graph for contextual retrieval and reasoning.

## Commands

### `arc serve start`

Start the MCP server.

```bash
arc serve start [OPTIONS]
```

This command starts the MCP server, which provides access to the knowledge graph via the Model Context Protocol.

#### Options

- `--host TEXT`: Host to bind the server to (default: from config or 127.0.0.1).
- `--port`, `-p INTEGER`: Port to bind the server to (default: from config or 8000).
- `--stdio`: Use stdio mode instead of HTTP.
- `--debug`: Enable debug mode.
- `--save-config`: Save the host and port to the configuration.

#### Example

```bash
# Start the MCP server with default settings
arc serve start

# Start the MCP server on a specific host and port
arc serve start --host 0.0.0.0 --port 8080

# Start the MCP server in stdio mode (for direct integration with AI assistants)
arc serve start --stdio

# Start the MCP server and save the configuration
arc serve start --host 0.0.0.0 --port 8080 --save-config

# Start the MCP server in debug mode
arc serve start --debug
```

### `arc serve status`

Check the status of the MCP server.

```bash
arc serve status
```

This command checks if the MCP server is running and displays its configuration.

#### Example

```bash
# Check the status of the MCP server
arc serve status
```

## Model Context Protocol (MCP)

The Model Context Protocol is a standardized way for AI assistants to access external data sources. The Arc MCP Server implements this protocol to provide access to the knowledge graph, allowing AI assistants to:

1. **Trace History**: Follow the decision trail for a specific line in a file
2. **Get Entity Details**: Retrieve detailed information about a specific entity
3. **Search**: Find entities matching specific criteria
4. **Relate**: Find entities related to a specific entity

## Configuration

The MCP server configuration is stored in the Arc Memory configuration file (`~/.arc/config.json`) and can be updated using the `--save-config` option:

```json
{
  "mcp": {
    "host": "127.0.0.1",
    "port": 8000
  }
}
```

## Requirements

- A built knowledge graph (run `arc build` first)
- The `arc-mcp-server` package (installed automatically if not found)
- Optional: AI assistant that supports the Model Context Protocol
