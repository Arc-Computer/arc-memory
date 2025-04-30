# Why Command

The Arc Memory CLI provides the `why` command for showing the decision trail for a specific line in a file. This command helps you understand why a particular line of code exists and the decisions that led to it.

**Related Documentation:**
- [Build Commands](./build.md) - Build your knowledge graph before using the why command
- [Trace Commands](./trace.md) - The underlying trace functionality
- [Relate Commands](./relate.md) - Show related nodes for an entity

## Overview

The `why` command uses the same breadth-first search (BFS) algorithm as the trace command, but presents the results in a more user-friendly format. It starts from the commit that last modified a specific line in a file and follows edges to related entities, providing a comprehensive view of the decision trail.

## Commands

### `arc why file`

Show the decision trail for a specific line in a file.

```bash
arc why file FILE_PATH LINE_NUMBER [OPTIONS]
```

This command traces the history of a specific line in a file, showing the commit that last modified it and related entities such as PRs, issues, and ADRs.

#### Arguments

- `FILE_PATH`: Path to the file, relative to the repository root.
- `LINE_NUMBER`: Line number to trace (1-based).

#### Options

- `--max-results`, `-m INTEGER`: Maximum number of results to return (default: 5).
- `--max-hops`, `-h INTEGER`: Maximum number of hops in the graph traversal (default: 3).
- `--format`, `-f [text|json|markdown]`: Output format (default: text).
- `--debug`: Enable debug logging.

#### Example

```bash
# Show the decision trail for line 42 in a file (default text format)
arc why file src/main.py 42

# Show with more results and hops
arc why file src/main.py 42 --max-results 10 --max-hops 4

# Output in JSON format
arc why file src/main.py 42 --format json

# Output in Markdown format
arc why file src/main.py 42 --format markdown

# Enable debug logging
arc why file src/main.py 42 --debug
```

## Output Formats

### Text Format

The text format presents the results in a series of panels, with each panel representing a node in the decision trail. The panels are color-coded by node type:

- **Commit**: Cyan
- **PR**: Green
- **Issue**: Yellow
- **ADR**: Blue
- **File**: Magenta

Each panel includes the node's title, ID, timestamp, and type-specific details.

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

### Markdown Format

The Markdown format presents the results in a structured Markdown document, which is useful for documentation and sharing. The document includes a title, sections for each node, and type-specific details.

## Understanding the Decision Trail

The decision trail shows the history of a specific line in a file, including:

1. The commit that last modified the line
2. The PR that merged the commit
3. Any issues that were mentioned in the PR
4. Any ADRs that were related to the issues

This helps you understand not just what changed, but why it changed, who made the decision, and what the rationale was.

## Requirements

- A built knowledge graph (run `arc build` first)
- Git repository with commit history
- Optional: GitHub PRs and issues (requires GitHub authentication)
- Optional: ADRs in the repository
