# Trace History API

The Trace History API allows you to trace the history of a specific line in a file, following the decision trail through commits, PRs, issues, and ADRs.

## Overview

The trace history algorithm uses a breadth-first search (BFS) to traverse the knowledge graph, starting from the commit that last modified a specific line in a file. It follows edges to related entities such as PRs, issues, and ADRs, providing a comprehensive view of the decision trail.

## Key Functions

### `trace_history_for_file_line`

```python
def trace_history_for_file_line(
    db_path: Path,
    file_path: str,
    line_number: int,
    max_results: int = 3,
    max_hops: int = 2
) -> List[Dict[str, Any]]
```

This is the main entry point for tracing the history of a specific line in a file.

#### Parameters

- `db_path`: Path to the SQLite database
- `file_path`: Path to the file, relative to the repository root
- `line_number`: Line number to check (1-based)
- `max_results`: Maximum number of results to return (default: 3)
- `max_hops`: Maximum number of hops in the graph traversal (default: 2)

#### Returns

A list of dictionaries representing the history trail, sorted by timestamp (newest first). Each dictionary contains:

- `type`: The type of the node (commit, pr, issue, adr, file)
- `id`: The unique identifier of the node
- `title`: The title of the node
- `timestamp`: The timestamp of the node (ISO format)

Additional fields are included based on the node type:

- **Commit**: `author`, `sha`
- **PR**: `number`, `state`, `url`
- **Issue**: `number`, `state`, `url`
- **ADR**: `status`, `decision_makers`, `path`

#### Example

```python
from pathlib import Path
from arc_memory.trace import trace_history_for_file_line

# Trace the history of line 10 in a file
results = trace_history_for_file_line(
    db_path=Path("~/.arc/graph.db"),
    file_path="src/main.py",
    line_number=10,
    max_results=5,
    max_hops=3
)

# Print the results
for result in results:
    print(f"{result['type']}: {result['title']} ({result['timestamp']})")
```

### `trace_history`

```python
def trace_history(
    conn: sqlite3.Connection,
    file_path: str,
    line_number: int,
    max_nodes: int = 3,
    max_hops: int = 2
) -> List[Dict[str, Any]]
```

This is the core function that implements the trace history algorithm.

#### Parameters

- `conn`: SQLite connection
- `file_path`: Path to the file, relative to the repository root
- `line_number`: Line number to check (1-based)
- `max_nodes`: Maximum number of nodes to return (default: 3)
- `max_hops`: Maximum number of hops in the graph traversal (default: 2)

#### Returns

Same as `trace_history_for_file_line`.

### `get_commit_for_line`

```python
@lru_cache(maxsize=BLAME_CACHE_SIZE)
def get_commit_for_line(repo_path: Path, file_path: str, line_number: int) -> Optional[str]
```

Uses git blame to find the commit that last modified a specific line.

#### Parameters

- `repo_path`: Path to the Git repository
- `file_path`: Path to the file, relative to the repository root
- `line_number`: Line number to check (1-based)

#### Returns

The commit hash, or None if not found.

## Graph Traversal

The trace history algorithm traverses the knowledge graph using the following rules:

1. Start from the commit that last modified the specified line
2. Follow edges to related entities:
   - Commit → PR via MERGES
   - Commit → File via MODIFIES
   - PR → Issue via MENTIONS
   - PR → Commit via MERGES (inbound)
   - Issue → ADR via DECIDES (inbound)
   - Issue → PR via MENTIONS (inbound)
   - ADR → Issue via DECIDES
   - ADR → File via DECIDES
   - File → Commit via MODIFIES (inbound)
   - File → ADR via DECIDES (inbound)

The algorithm uses a breadth-first search to ensure that the most relevant entities are returned first.

## CLI Integration

The trace history API is integrated with the Arc Memory CLI through the `arc trace file` command. This command now supports both human-readable text output and machine-readable JSON output via the `--format` option:

```bash
# Output in human-readable text format (default)
arc trace file src/main.py 42 --format text

# Output in machine-readable JSON format
arc trace file src/main.py 42 --format json
```

The JSON output format is particularly useful for programmatic consumption, such as by the VS Code extension. It returns the exact same data structure as the `trace_history_for_file_line` function, serialized as JSON.

See the [CLI documentation](../cli/trace.md) for more details.

## Performance

The trace history algorithm is designed for high performance, with queries typically completing in under 200 microseconds. This ensures a responsive user experience in the VS Code extension.

## Error Handling

All functions in the trace history API include comprehensive error handling to ensure that they gracefully handle edge cases such as:

- File not found
- Line number out of range
- Git blame failures
- Database connection issues

Errors are logged using the Arc Memory logging system, and empty results are returned in case of errors.
