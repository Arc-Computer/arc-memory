# Trace Commands

The Arc Memory CLI provides commands for tracing the history of specific lines in files, allowing you to follow the decision trail through commits, PRs, issues, and ADRs.

**Related Documentation:**
- [Build Commands](./build.md) - Build your knowledge graph before tracing
- [Doctor Commands](./doctor.md) - Verify your graph status
- [Tracing History Examples](../examples/tracing-history.md) - Detailed examples of tracing history
- [Trace API](../api/trace.md) - Programmatic access to trace functionality

## Overview

The trace command uses a breadth-first search (BFS) algorithm to traverse the knowledge graph, starting from the commit that last modified a specific line in a file. It follows edges to related entities, providing a comprehensive view of the decision trail.

## Commands

### `arc trace file`

Trace the history of a specific line in a file.

```bash
arc trace file FILE_PATH LINE_NUMBER [OPTIONS]
```

This command traces the history of a specific line in a file, showing the commit that last modified it and related entities such as PRs, issues, and ADRs.

#### Arguments

- `FILE_PATH`: Path to the file, relative to the repository root.
- `LINE_NUMBER`: Line number to trace (1-based).

#### Options

- `--max-results`, `-m INTEGER`: Maximum number of results to return (default: 3).
- `--max-hops`, `-h INTEGER`: Maximum number of hops in the graph traversal (default: 2).
- `--format`, `-f [text|json]`: Output format (default: text).
- `--debug`: Enable debug logging.

#### Example

```bash
# Trace the history of line 42 in a file (default text format)
arc trace file src/main.py 42

# Trace with more results and hops
arc trace file src/main.py 42 --max-results 5 --max-hops 3

# Output in JSON format
arc trace file src/main.py 42 --format json

# Short form for JSON format
arc trace file src/main.py 42 -f json

# Enable debug logging
arc trace file src/main.py 42 --debug
```

## Output Formats

The trace command supports two output formats: text (default) and JSON.

### Text Format

When using the default text format (`--format text`), the command outputs a table with the following columns:

- **Type**: The type of the node (commit, pr, issue, adr, file).
- **ID**: The unique identifier of the node.
- **Title**: The title or description of the node.
- **Timestamp**: When the node was created or last modified.
- **Details**: Additional details specific to the node type.

Example text output:

```
┌───────┬──────────────┬───────────────────────┬─────────────────────┬───────────────────────┐
│ Type  │ ID           │ Title                 │ Timestamp           │ Details               │
├───────┼──────────────┼───────────────────────┼─────────────────────┼───────────────────────┤
│ commit│ abc123       │ Fix bug in login form │ 2023-04-15T14:32:10 │ Author: John Doe      │
│       │              │                       │                     │ SHA: abc123def456     │
├───────┼──────────────┼───────────────────────┼─────────────────────┼───────────────────────┤
│ pr    │ 42           │ Fix login issues      │ 2023-04-16T09:15:22 │ PR #42                │
│       │              │                       │                     │ State: merged         │
│       │              │                       │                     │ URL: github.com/...   │
├───────┼──────────────┼───────────────────────┼─────────────────────┼───────────────────────┤
│ issue │ 123          │ Login form bug        │ 2023-04-10T11:20:05 │ Issue #123            │
│       │              │                       │                     │ State: closed         │
│       │              │                       │                     │ URL: github.com/...   │
└───────┴──────────────┴───────────────────────┴─────────────────────┴───────────────────────┘
```

### JSON Format

When using the JSON format (`--format json`), the command outputs a JSON array of objects, where each object represents a node in the history trail. This format is particularly useful for programmatic consumption, such as by the VS Code extension.

Example JSON output:

```json
[
  {
    "type": "pr",
    "id": "PR_kwDOK9Z4x85qXE9P",
    "title": "Fix login issues",
    "timestamp": "2023-04-16T09:15:22Z",
    "number": 42,
    "state": "MERGED",
    "url": "https://github.com/example/repo/pull/42"
  },
  {
    "type": "commit",
    "id": "commit:abc123",
    "title": "Fix bug in login form",
    "timestamp": "2023-04-15T14:32:10Z",
    "author": "John Doe",
    "sha": "abc123def456"
  },
  {
    "type": "issue",
    "id": "Issue_123",
    "title": "Login form bug",
    "timestamp": "2023-04-10T11:20:05Z",
    "number": 123,
    "state": "closed",
    "url": "https://github.com/example/repo/issues/123"
  }
]
```

Each object in the JSON array contains:

- Common fields for all node types:
  - `type`: The type of the node (commit, pr, issue, adr, file)
  - `id`: The unique identifier of the node
  - `title`: The title or description of the node
  - `timestamp`: When the node was created or last modified (ISO format)

- Type-specific fields:
  - For `commit`: `author`, `sha`
  - For `pr`: `number`, `state`, `url`
  - For `issue`: `number`, `state`, `url`
  - For `adr`: `status`, `decision_makers`, `path`

The JSON output is sorted chronologically, with the newest events first, matching the behavior of the text output.

## Interpreting Trace Results

### Understanding Node Types

The trace results include different types of nodes that represent different entities in the software development process:

1. **commit**: A Git commit that modified the file
   - This is typically the starting point of the trace
   - Shows who made the change and when

2. **pr**: A GitHub Pull Request
   - Shows how the commit was merged into the codebase
   - Links to discussions about the code changes

3. **issue**: A GitHub Issue
   - Represents the problem or feature that motivated the change
   - Often contains requirements or bug reports

4. **adr**: An Architectural Decision Record
   - Documents important design decisions
   - Explains the rationale behind architectural choices

5. **file**: A file in the repository
   - Represents a file that's related to the traced line
   - May be referenced by other nodes

### Understanding Relationships

The relationships between nodes tell a story about how the code evolved:

1. **commit → pr**: The PR that merged this commit
   - Example: "Commit abc123 was merged via PR #42"

2. **pr → issue**: The issue that the PR addresses
   - Example: "PR #42 fixes Issue #123"

3. **issue → adr**: The architectural decision related to the issue
   - Example: "Issue #123 implements the design described in ADR-001"

4. **commit → file**: The file modified by the commit
   - Example: "Commit abc123 modified src/login.py"

### Reading the Decision Trail

To understand the full decision trail, read the results from bottom to top (oldest to newest):

1. Start with the **issue** (if present)
   - This explains why the change was needed
   - Look at the issue title, state, and URL

2. Look at any **adr** nodes
   - These explain architectural decisions
   - Help understand the design rationale

3. Examine the **pr** nodes
   - These show how the change was reviewed and merged
   - The PR description often contains important context

4. Finally, look at the **commit** nodes
   - These show the actual code changes
   - The commit message often explains implementation details

### Example Interpretation

For the example output above, the decision trail reads:

1. Issue #123 "Login form bug" was opened (2023-04-10)
   - This identified a problem with the login form

2. Commit abc123 "Fix bug in login form" was created by John Doe (2023-04-15)
   - This implemented a fix for the bug

3. PR #42 "Fix login issues" was merged (2023-04-16)
   - This PR included the fix and was reviewed and approved

This tells us that the line we traced was modified to fix a bug in the login form, which was tracked as Issue #123 and merged through PR #42.

## How It Works

The trace algorithm works as follows:

1. Uses `git blame` to find the commit that last modified the specified line.
2. Starts a breadth-first search from that commit node in the knowledge graph.
3. Traverses edges to related entities (PRs, issues, ADRs) up to the specified maximum number of hops.
4. Returns the results sorted by timestamp (newest first).

## Requirements

- The knowledge graph must be built before tracing history. If the database doesn't exist, the command will prompt you to run `arc build`.
- Git must be installed and available in the PATH.
- The file must exist in the repository.

## Troubleshooting

If you encounter issues with the trace command:

1. **No Results**: If no history is found, ensure the file and line number are correct, and that the knowledge graph has been built with `arc build`.
2. **Database Not Found**: If the database doesn't exist, run `arc build` to create it.
3. **Git Blame Errors**: Ensure the file is tracked by Git and has commit history.
4. **Debug Mode**: Run with `--debug` flag to see detailed logs: `arc trace file path/to/file.py 42 --debug`
