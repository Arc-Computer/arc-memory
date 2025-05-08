"""Data models for Arc Memory."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    # Existing types
    COMMIT = "commit"
    FILE = "file"
    PR = "pr"
    ISSUE = "issue"
    ADR = "adr"

    # New types for code entities
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    COMPONENT = "component"
    SERVICE = "service"

    # New types for documentation and concepts
    DOCUMENT = "document"
    CONCEPT = "concept"
    REQUIREMENT = "requirement"

    # New types for temporal analysis
    CHANGE_PATTERN = "change_pattern"
    REFACTORING = "refactoring"


class EdgeRel(str, Enum):
    """Types of relationships between nodes."""

    # Existing relationships
    MODIFIES = "MODIFIES"  # Commit modifies a file
    MERGES = "MERGES"      # PR merges a commit
    MENTIONS = "MENTIONS"  # PR/Issue mentions another entity
    DECIDES = "DECIDES"    # ADR decides on a file/commit
    DEPENDS_ON = "DEPENDS_ON"  # File/component depends on another file/component

    # New relationships for code structure
    CONTAINS = "CONTAINS"      # Module/Class contains a function/method
    CALLS = "CALLS"            # Function calls another function
    IMPORTS = "IMPORTS"        # Module imports another module
    INHERITS_FROM = "INHERITS_FROM"  # Class inherits from another class
    IMPLEMENTS = "IMPLEMENTS"  # Class implements an interface
    PART_OF = "PART_OF"        # Component is part of a service

    # New relationships for documentation
    DESCRIBES = "DESCRIBES"    # Document describes a code entity
    REFERENCES = "REFERENCES"  # Document references another document

    # New relationships for temporal analysis
    FOLLOWS = "FOLLOWS"        # Change pattern follows another
    PRECEDES = "PRECEDES"      # Change pattern precedes another
    CORRELATES_WITH = "CORRELATES_WITH"  # Changes correlate with each other


class Node(BaseModel):
    """Base class for all nodes in the knowledge graph."""

    id: str
    type: NodeType
    title: Optional[str] = None
    body: Optional[str] = None
    ts: Optional[datetime] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class FileNode(Node):
    """A file in the repository."""

    type: NodeType = NodeType.FILE
    path: str
    language: Optional[str] = None
    last_modified: Optional[datetime] = None


class CommitNode(Node):
    """A Git commit node."""

    type: NodeType = NodeType.COMMIT
    author: str
    files: List[str]
    sha: str


class PRNode(Node):
    """A GitHub Pull Request node."""

    type: NodeType = NodeType.PR
    number: int
    state: str
    merged_at: Optional[datetime] = None
    merged_by: Optional[str] = None
    merged_commit_sha: Optional[str] = None
    url: str


class IssueNode(Node):
    """A GitHub Issue node."""

    type: NodeType = NodeType.ISSUE
    number: int
    state: str
    closed_at: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    url: str


class ADRNode(Node):
    """An Architectural Decision Record node."""

    type: NodeType = NodeType.ADR
    status: str
    decision_makers: List[str] = Field(default_factory=list)
    path: str


class Edge(BaseModel):
    """An edge connecting two nodes in the knowledge graph."""

    src: str
    dst: str
    rel: EdgeRel
    properties: Dict[str, Any] = Field(default_factory=dict)


class BuildManifest(BaseModel):
    """Metadata about a graph build."""

    schema_version: str
    build_time: datetime
    commit: Optional[str] = None
    node_count: int
    edge_count: int
    # Additional fields for incremental builds
    last_processed: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """A search result from the knowledge graph."""

    id: str
    type: NodeType
    title: str
    snippet: str
    score: float


class FunctionNode(Node):
    """A function or method in the codebase."""

    type: NodeType = NodeType.FUNCTION
    path: str  # File path containing the function
    name: str  # Function name
    signature: str  # Function signature
    docstring: Optional[str] = None
    start_line: int  # Starting line in the file
    end_line: int  # Ending line in the file
    complexity: Optional[float] = None  # Cyclomatic complexity
    parameters: List[Dict[str, str]] = Field(default_factory=list)  # Parameter names and types
    return_type: Optional[str] = None  # Return type
    embedding: Optional[List[float]] = None  # Code embedding vector


class ClassNode(Node):
    """A class in the codebase."""

    type: NodeType = NodeType.CLASS
    path: str  # File path containing the class
    name: str  # Class name
    docstring: Optional[str] = None
    start_line: int  # Starting line in the file
    end_line: int  # Ending line in the file
    methods: List[str] = Field(default_factory=list)  # Method names
    attributes: List[Dict[str, str]] = Field(default_factory=list)  # Attribute names and types
    embedding: Optional[List[float]] = None  # Code embedding vector


class ModuleNode(Node):
    """A module in the codebase."""

    type: NodeType = NodeType.MODULE
    path: str  # File path of the module
    name: str  # Module name
    docstring: Optional[str] = None
    imports: List[str] = Field(default_factory=list)  # Imported modules
    exports: List[str] = Field(default_factory=list)  # Exported symbols
    embedding: Optional[List[float]] = None  # Code embedding vector


class ComponentNode(Node):
    """A component in the system architecture."""

    type: NodeType = NodeType.COMPONENT
    name: str  # Component name
    description: Optional[str] = None
    files: List[str] = Field(default_factory=list)  # Files in this component
    responsibilities: List[str] = Field(default_factory=list)  # Component responsibilities


class ServiceNode(Node):
    """A service in the system architecture."""

    type: NodeType = NodeType.SERVICE
    name: str  # Service name
    description: Optional[str] = None
    components: List[str] = Field(default_factory=list)  # Components in this service
    apis: List[Dict[str, Any]] = Field(default_factory=list)  # API endpoints
    dependencies: List[str] = Field(default_factory=list)  # External dependencies


class DocumentNode(Node):
    """A documentation file."""

    type: NodeType = NodeType.DOCUMENT
    path: str  # File path
    format: str  # Document format (markdown, rst, etc.)
    topics: List[str] = Field(default_factory=list)  # Topics covered
    references: List[str] = Field(default_factory=list)  # Referenced documents


class ConceptNode(Node):
    """A concept or domain term."""

    type: NodeType = NodeType.CONCEPT
    name: str  # Concept name
    definition: str  # Definition of the concept
    related_terms: List[str] = Field(default_factory=list)  # Related concepts


class ChangePatternNode(Node):
    """A pattern of changes over time."""

    type: NodeType = NodeType.CHANGE_PATTERN
    pattern_type: str  # Type of pattern (refactoring, feature addition, etc.)
    files: List[str] = Field(default_factory=list)  # Files involved
    frequency: float  # How often this pattern occurs
    impact: Dict[str, Any] = Field(default_factory=dict)  # Impact metrics
