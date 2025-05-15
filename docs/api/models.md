# Data Models API

The Data Models API defines the core data structures used in Arc Memory, including nodes, edges, and build manifests.

## Overview

Arc Memory uses a graph-based data model, where nodes represent entities (commits, files, PRs, issues, ADRs) and edges represent relationships between them. The data models are implemented using Pydantic, which provides validation, serialization, and documentation.

## Node Types

### `NodeType` Enum

```python
class NodeType(str, Enum):
    # Core types
    COMMIT = "commit"
    FILE = "file"
    PR = "pr"
    ISSUE = "issue"
    ADR = "adr"

    # Repository identity
    REPOSITORY = "repository"

    # Architecture components
    SYSTEM = "system"
    SERVICE = "service"
    COMPONENT = "component"
    INTERFACE = "interface"

    # Other types...
```

This enum defines the types of nodes in the knowledge graph:

- `COMMIT`: A Git commit
- `FILE`: A file in the repository
- `PR`: A GitHub Pull Request
- `ISSUE`: A GitHub Issue
- `ADR`: An Architectural Decision Record
- `REPOSITORY`: A Git repository
- `SYSTEM`: A system in the architecture
- `SERVICE`: A service in the system
- `COMPONENT`: A component in the system
- `INTERFACE`: An interface exposed by a service or component

### `Node` Base Class

```python
class Node(BaseModel):
    id: str
    type: NodeType
    title: Optional[str] = None
    body: Optional[str] = None
    ts: Optional[datetime] = None
    repo_id: Optional[str] = None  # Reference to repository
    extra: Dict[str, Any] = Field(default_factory=dict)
```

This is the base class for all nodes in the knowledge graph:

- `id`: A unique identifier for the node
- `type`: The type of the node (from `NodeType` enum)
- `title`: The title or name of the node
- `body`: The body or content of the node
- `ts`: The timestamp of the node
- `repo_id`: Reference to the repository this node belongs to
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

#### `RepositoryNode`

```python
class RepositoryNode(Node):
    type: NodeType = NodeType.REPOSITORY
    name: str  # Repository name (e.g., "arc-memory")
    url: Optional[str] = None  # Repository URL
    local_path: str  # Local path where repository was cloned
    default_branch: str = "main"  # Default branch
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional metadata
```

Represents a Git repository:

- `name`: The name of the repository
- `url`: The URL of the repository (e.g., "https://github.com/Arc-Computer/arc-memory")
- `local_path`: The local path where the repository was cloned
- `default_branch`: The default branch of the repository
- `metadata`: Additional metadata about the repository

#### `SystemNode`

```python
class SystemNode(Node):
    type: NodeType = NodeType.SYSTEM
    name: str
    description: Optional[str] = None
```

Represents a system in the architecture:

- `name`: The name of the system
- `description`: A description of the system

#### `ServiceNode`

```python
class ServiceNode(Node):
    type: NodeType = NodeType.SERVICE
    name: str  # Service name
    description: Optional[str] = None
    system_id: Optional[str] = None  # Reference to parent system
    apis: List[Dict[str, Any]] = Field(default_factory=list)  # API endpoints
    dependencies: List[str] = Field(default_factory=list)  # External dependencies
```

Represents a service in the system architecture:

- `name`: The name of the service
- `description`: A description of the service
- `system_id`: Reference to the parent system
- `apis`: List of API endpoints provided by the service
- `dependencies`: List of external dependencies

#### `ComponentNode`

```python
class ComponentNode(Node):
    type: NodeType = NodeType.COMPONENT
    name: str  # Component name
    description: Optional[str] = None
    service_id: Optional[str] = None  # Reference to parent service
    files: List[str] = Field(default_factory=list)  # Files in this component
    responsibilities: List[str] = Field(default_factory=list)  # Component responsibilities
```

Represents a component in the system architecture:

- `name`: The name of the component
- `description`: A description of the component
- `service_id`: Reference to the parent service
- `files`: List of files in this component
- `responsibilities`: List of component responsibilities

#### `InterfaceNode`

```python
class InterfaceNode(Node):
    type: NodeType = NodeType.INTERFACE
    name: str
    description: Optional[str] = None
    service_id: Optional[str] = None  # Reference to parent service
    interface_type: str = "api"  # api, event, etc.
```

Represents an interface in the architecture:

- `name`: The name of the interface
- `description`: A description of the interface
- `service_id`: Reference to the parent service
- `interface_type`: The type of interface (api, event, etc.)

## Edge Types

### `EdgeRel` Enum

```python
class EdgeRel(str, Enum):
    # Core relationships
    MODIFIES = "MODIFIES"  # Commit modifies a file
    MERGES = "MERGES"      # PR merges a commit
    MENTIONS = "MENTIONS"  # PR/Issue mentions another entity
    DECIDES = "DECIDES"    # ADR decides on a file/commit
    DEPENDS_ON = "DEPENDS_ON"  # File/component depends on another file/component

    # Architecture relationships
    CONTAINS = "CONTAINS"      # System contains Service, Service contains Component
    EXPOSES = "EXPOSES"        # Service/Component exposes Interface
    CONSUMES = "CONSUMES"      # Service/Component consumes Interface
    COMMUNICATES_WITH = "COMMUNICATES_WITH"  # Service communicates with Service

    # Other relationships...
```

This enum defines the types of relationships between nodes:

- `MODIFIES`: A commit modifies a file
- `MERGES`: A PR merges a commit
- `MENTIONS`: A PR or issue mentions another entity
- `DECIDES`: An ADR makes a decision about a file or commit
- `DEPENDS_ON`: A file or component depends on another file or component
- `CONTAINS`: A system contains a service, or a service contains a component
- `EXPOSES`: A service or component exposes an interface
- `CONSUMES`: A service or component consumes an interface
- `COMMUNICATES_WITH`: A service communicates with another service

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
