# Relate Command

The Arc Memory CLI provides the `relate` command for showing nodes related to a specific entity in the knowledge graph. This command helps you understand the relationships between different entities in your codebase.

**Related Documentation:**
- [Build Commands](./build.md) - Build your knowledge graph before using the relate command
- [Why Commands](./why.md) - Show decision trail for a file line
- [Trace Commands](./trace.md) - The underlying trace functionality

## Overview

The `relate` command shows nodes that are directly connected to a specified entity in the knowledge graph. It uses the same graph traversal functionality as the trace command, but focuses on a specific entity rather than a file line.

## Commands

### `arc relate node`

Show nodes related to a specific entity.

```bash
arc relate node ENTITY_ID [OPTIONS]
```

This command shows nodes that are directly connected to the specified entity in the knowledge graph.

#### Arguments

- `ENTITY_ID`: ID of the entity (e.g., commit:abc123, pr:42, issue:123, adr:001).

#### Options

- `--max-results`, `-m INTEGER`: Maximum number of results to return (default: 10).
- `--rel`, `-r TEXT`: Relationship type to filter by (e.g., MERGES, MENTIONS).
- `--format`, `-f [text|json]`: Output format (default: text).
- `--debug`: Enable debug logging.

#### Example

```bash
# Show nodes related to a commit
arc relate node commit:abc123

# Show nodes related to a PR
arc relate node pr:42

# Show nodes related to an issue with a specific relationship type
arc relate node issue:123 --rel MENTIONS

# Output in JSON format
arc relate node adr:001 --format json

# Limit the number of results
arc relate node commit:abc123 --max-results 5

# Enable debug logging
arc relate node pr:42 --debug
```

## Output Formats

### Text Format

The text format presents the results in a table with the following columns:

- **Type**: The type of the node (commit, pr, issue, adr, file)
- **ID**: The ID of the node
- **Title**: The title of the node
- **Timestamp**: The timestamp of the node
- **Details**: Type-specific details for the node

### JSON Format

The JSON format returns the raw data as a JSON array, which is useful for programmatic consumption. Each node in the array includes the following fields:

- `type`: The type of the node (commit, pr, issue, adr, file)
- `id`: The ID of the node
- `title`: The title of the node
- `timestamp`: The timestamp of the node (ISO format)

Additional fields are included based on the node type:

- **Commit**: `author`, `sha`
- **PR**: `number`, `state`, `url`
- **Issue**: `number`, `state`, `url`
- **ADR**: `status`, `decision_makers`, `path`

## Understanding Relationships

The relationships between nodes tell a story about how the code evolved:

1. **MODIFIES**: A commit modifies a file
   - Example: "Commit abc123 modifies src/main.py"

2. **MERGES**: A PR merges a commit
   - Example: "PR #42 merges commit abc123"

3. **MENTIONS**: A PR or issue mentions another entity
   - Example: "PR #42 mentions Issue #123"

4. **DECIDES**: An ADR decides on a file or issue
   - Example: "ADR-001 decides on Issue #123"

## Requirements

- A built knowledge graph (run `arc build` first)
- Git repository with commit history
- Optional: GitHub PRs and issues (requires GitHub authentication)
- Optional: ADRs in the repository
