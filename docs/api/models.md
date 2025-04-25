# Data Models API

The Data Models API defines the core data structures used in Arc Memory, including nodes, edges, and build manifests.

## Overview

Arc Memory uses a graph-based data model, where nodes represent entities (commits, files, PRs, issues, ADRs) and edges represent relationships between them. The data models are implemented using Pydantic, which provides validation, serialization, and documentation.

## Node Types

### `NodeType` Enum

```python
class NodeType(str, Enum):
    COMMIT = "commit"
    FILE = "file"
    PR = "pr"
    ISSUE = "issue"
    ADR = "adr"
```

This enum defines the types of nodes in the knowledge graph:

- `COMMIT`: A Git commit
- `FILE`: A file in the repository
- `PR`: A GitHub Pull Request
- `ISSUE`: A GitHub Issue
- `ADR`: An Architectural Decision Record

### `Node` Base Class

```python
class Node(BaseModel):
    id: str
    type: NodeType
    title: Optional[str] = None
    body: Optional[str] = None
    ts: Optional[datetime] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
```

This is the base class for all nodes in the knowledge graph:

- `id`: A unique identifier for the node
- `type`: The type of the node (from `NodeType` enum)
- `title`: The title or name of the node
- `body`: The body or content of the node
- `ts`: The timestamp of the node
- `extra`: Additional metadata for the node

### Specialized Node Classes

#### `FileNode`

```python
class FileNode(Node):
    type: NodeType = NodeType.FILE
    path: str
    language: Optional[str] = None
    last_modified: Optional[datetime] = None
```

Represents a file in the repository:

- `path`: The path to the file, relative to the repository root
- `language`: The programming language of the file
- `last_modified`: The last modification time of the file

#### `CommitNode`

```python
class CommitNode(Node):
    type: NodeType = NodeType.COMMIT
    author: str
    files: List[str]
    sha: str
```

Represents a Git commit:

- `author`: The author of the commit
- `files`: The files modified in the commit
- `sha`: The SHA hash of the commit

#### `PRNode`

```python
class PRNode(Node):
    type: NodeType = NodeType.PR
    number: int
    state: str
    merged_at: Optional[datetime] = None
    merged_by: Optional[str] = None
    merged_commit_sha: Optional[str] = None
    url: str
```

Represents a GitHub Pull Request:

- `number`: The PR number
- `state`: The state of the PR (open, closed, merged)
- `merged_at`: When the PR was merged
- `merged_by`: Who merged the PR
- `merged_commit_sha`: The SHA of the merge commit
- `url`: The URL of the PR

#### `IssueNode`

```python
class IssueNode(Node):
    type: NodeType = NodeType.ISSUE
    number: int
    state: str
    closed_at: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    url: str
```

Represents a GitHub Issue:

- `number`: The issue number
- `state`: The state of the issue (open, closed)
- `closed_at`: When the issue was closed
- `labels`: The labels on the issue
- `url`: The URL of the issue

#### `ADRNode`

```python
class ADRNode(Node):
    type: NodeType = NodeType.ADR
    status: str
    decision_makers: List[str] = Field(default_factory=list)
    path: str
```

Represents an Architectural Decision Record:

- `status`: The status of the ADR (proposed, accepted, rejected, etc.)
- `decision_makers`: The people who made the decision
- `path`: The path to the ADR file

## Edge Types

### `EdgeRel` Enum

```python
class EdgeRel(str, Enum):
    MODIFIES = "MODIFIES"  # Commit modifies a file
    MERGES = "MERGES"      # PR merges a commit
    MENTIONS = "MENTIONS"  # PR/Issue mentions another entity
    DECIDES = "DECIDES"    # ADR decides on a file/commit
```

This enum defines the types of relationships between nodes:

- `MODIFIES`: A commit modifies a file
- `MERGES`: A PR merges a commit
- `MENTIONS`: A PR or issue mentions another entity
- `DECIDES`: An ADR makes a decision about a file or commit

### `Edge` Class

```python
class Edge(BaseModel):
    src: str
    dst: str
    rel: EdgeRel
    properties: Dict[str, Any] = Field(default_factory=dict)
```

Represents an edge connecting two nodes in the knowledge graph:

- `src`: The ID of the source node
- `dst`: The ID of the destination node
- `rel`: The relationship type (from `EdgeRel` enum)
- `properties`: Additional properties of the edge

## Build Manifest

### `BuildManifest` Class

```python
class BuildManifest(BaseModel):
    schema_version: str
    build_time: datetime
    commit: Optional[str] = None
    node_count: int
    edge_count: int
    last_processed: Dict[str, Any] = Field(default_factory=dict)
```

Stores metadata about a graph build:

- `schema_version`: The schema version of the build manifest
- `build_time`: When the build was performed
- `commit`: The commit hash at the time of the build
- `node_count`: The number of nodes in the graph
- `edge_count`: The number of edges in the graph
- `last_processed`: Metadata from each plugin, used for incremental builds

## Search Result

### `SearchResult` Class

```python
class SearchResult(BaseModel):
    id: str
    type: NodeType
    title: str
    snippet: str
    score: float
```

Represents a search result from the knowledge graph:

- `id`: The ID of the node
- `type`: The type of the node
- `title`: The title of the node
- `snippet`: A snippet of the node's content
- `score`: The relevance score of the result

## Usage Examples

### Creating Nodes and Edges

```python
from datetime import datetime
from arc_memory.schema.models import CommitNode, FileNode, Edge, EdgeRel

# Create a commit node
commit = CommitNode(
    id="commit:abc123",
    title="Fix bug in login form",
    body="This commit fixes a bug in the login form",
    ts=datetime.now(),
    author="John Doe",
    files=["src/login.py"],
    sha="abc123"
)

# Create a file node
file = FileNode(
    id="file:src/login.py",
    title="Login Form",
    path="src/login.py",
    language="python",
    last_modified=datetime.now()
)

# Create an edge connecting the commit to the file
edge = Edge(
    src=commit.id,
    dst=file.id,
    rel=EdgeRel.MODIFIES,
    properties={"lines_added": 10, "lines_removed": 5}
)
```

### Using the Build Manifest

```python
from datetime import datetime
from arc_memory.schema.models import BuildManifest

# Create a build manifest
manifest = BuildManifest(
    schema_version="0.1.0",
    build_time=datetime.now(),
    commit="abc123",
    node_count=100,
    edge_count=150,
    last_processed={
        "git": {"last_commit_hash": "abc123"},
        "github": {"last_pr": 42, "last_issue": 24},
        "adr": {"last_modified": "2025-04-24T12:00:00Z"}
    }
)

# Serialize to JSON
json_data = manifest.model_dump_json()

# Deserialize from JSON
loaded_manifest = BuildManifest.model_validate_json(json_data)
```
