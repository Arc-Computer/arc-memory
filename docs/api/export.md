# Export API

The Export API provides functions for exporting a relevant slice of the knowledge graph as a JSON file for use in GitHub App PR review workflows.

## Command-Line Interface

### `arc export`

Export a relevant slice of the knowledge graph for PR review.

**Usage:**
```bash
arc export <PR_SHA> --out <OUTPUT_FILE> [OPTIONS]
```

**Arguments:**
- `PR_SHA`: SHA of the PR head commit
- `--out`: Output file path for the JSON

**Options:**
- `--compress/--no-compress`: Compress the output file (default: True)
- `--sign/--no-sign`: Sign the output file with GPG (default: False)
- `--key TEXT`: GPG key ID to use for signing
- `--repo PATH`: Path to the Git repository (default: current directory)
- `--db PATH`: Path to the database file (default: ~/.arc/graph.db)
- `--base TEXT`: Base branch to compare against (default: main)
- `--debug`: Enable debug logging

**Examples:**
```bash
# Basic usage
arc export abc123 --out arc-graph.json

# With compression (default)
arc export abc123 --out arc-graph.json.gz --compress

# With GPG signing
arc export abc123 --out arc-graph.json --sign --key ABCD1234

# With custom repository and database paths
arc export abc123 --out arc-graph.json --repo /path/to/repo --db /path/to/graph.db

# With custom base branch
arc export abc123 --out arc-graph.json --base develop
```

## Programmatic API

### `export_graph(db_path, repo_path, pr_sha, output_path, compress=True, sign=False, key_id=None, base_branch="main")`

Export a relevant slice of the knowledge graph for a PR.

**Parameters:**
- `db_path`: Path to the database file
- `repo_path`: Path to the Git repository
- `pr_sha`: SHA of the PR head commit
- `output_path`: Path to save the export file
- `compress`: Whether to compress the output file (default: True)
- `sign`: Whether to sign the output file (default: False)
- `key_id`: GPG key ID to use for signing (default: None)
- `base_branch`: Base branch to compare against (default: "main")

**Returns:**
- Path to the exported file

**Raises:**
- `ExportError`: If there's an error exporting the graph

**Example:**
```python
from pathlib import Path
from arc_memory.export import export_graph

# Export the graph for a PR
output_path = export_graph(
    db_path=Path("~/.arc/graph.db"),
    repo_path=Path("/path/to/repo"),
    pr_sha="abc123",
    output_path=Path("arc-graph.json"),
    compress=True,
    sign=False
)

print(f"Exported graph to {output_path}")
```

### `get_pr_modified_files(repo_path, pr_sha, base_branch="main")`

Get the list of files modified in a PR.

**Parameters:**
- `repo_path`: Path to the Git repository
- `pr_sha`: SHA of the PR head commit
- `base_branch`: Base branch to compare against (default: "main")

**Returns:**
- List of file paths modified in the PR

**Raises:**
- `GitError`: If there's an error accessing the Git repository

**Example:**
```python
from pathlib import Path
from arc_memory.export import get_pr_modified_files

# Get files modified in a PR
modified_files = get_pr_modified_files(
    repo_path=Path("/path/to/repo"),
    pr_sha="abc123",
    base_branch="main"
)

print(f"Modified files: {modified_files}")
```

### `get_related_nodes(conn, node_ids, max_hops=1, include_adrs=True)`

Get nodes related to the specified nodes up to max_hops away.

**Parameters:**
- `conn`: Database connection
- `node_ids`: List of node IDs to start from
- `max_hops`: Maximum number of hops to traverse (default: 1)
- `include_adrs`: Whether to include all ADRs regardless of hop distance (default: True)

**Returns:**
- Tuple of (nodes, edges) where each is a list of dictionaries

**Example:**
```python
from arc_memory.export import get_related_nodes
from arc_memory.sql.db import get_connection

# Get a database connection
conn = get_connection()

# Get nodes related to a file
nodes, edges = get_related_nodes(
    conn=conn,
    node_ids=["file:src/main.py"],
    max_hops=1,
    include_adrs=True
)

print(f"Found {len(nodes)} related nodes and {len(edges)} edges")
```

## Export Format

The exported JSON follows this structure:

```json
{
  "schema_version": "0.2",
  "generated_at": "2023-05-08T14:23Z",
  "pr": {
    "sha": "abc123",
    "number": 123,
    "title": "Add payment processing",
    "author": "alice",
    "changed_files": ["src/payments/api.py", "src/payments/models.py"]
  },
  "nodes": [
    {
      "id": "file:src/payments/api.py",
      "type": "file",
      "path": "src/payments/api.py",
      "metadata": { "language": "python" }
    },
    {
      "id": "adr:001",
      "type": "adr",
      "title": "Payment Gateway Selection",
      "path": "docs/adrs/001-payment-gateway.md",
      "metadata": {
        "status": "accepted",
        "decision_makers": ["alice", "bob"]
      }
    }
  ],
  "edges": [
    {
      "src": "commit:def456",
      "dst": "file:src/payments/api.py",
      "type": "MODIFIES",
      "metadata": {
        "lines_added": 10,
        "lines_removed": 5
      }
    }
  ],
  "sign": {
    "gpg_fpr": "ABCD1234...",
    "sig_path": "arc-graph.json.gz.sig"
  }
}
```

## Graph Scoping Algorithm

The export command intelligently determines which parts of the graph to export:

1. Start with files modified in the PR (comparing PR head with base branch)
2. Include direct relationships (1-hop neighbors)
3. Always include linked ADRs regardless of hop distance
4. Include Linear tickets referenced in the PR or commits
5. Include recent changes to the modified files (last 3-5 commits)
6. Apply filtering to keep the export size manageable (target: ≤250KB)
