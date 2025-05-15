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

    # Repository identity
    REPOSITORY = "repository"  # A Git repository

    # Architecture components
    SYSTEM = "system"  # A system in the architecture
    SERVICE = "service"  # A service in the system
    COMPONENT = "component"  # A component in the system
    INTERFACE = "interface"  # An interface exposed by a service or component

    # Code entities
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"

    # New types for documentation and concepts
    DOCUMENT = "document"
    CONCEPT = "concept"
    REQUIREMENT = "requirement"

    # New types for temporal analysis
    CHANGE_PATTERN = "change_pattern"
    REFACTORING = "refactoring"

    # New types for reasoning structures
    REASONING_QUESTION = "reasoning_question"
    REASONING_ALTERNATIVE = "reasoning_alternative"
    REASONING_CRITERION = "reasoning_criterion"
    REASONING_STEP = "reasoning_step"
    REASONING_IMPLICATION = "reasoning_implication"

    # New types for causal relationships
    DECISION = "decision"  # A decision made during development
    IMPLICATION = "implication"  # An implication of a decision
    CODE_CHANGE = "code_change"  # A specific code change resulting from a decision


class EdgeRel(str, Enum):
    """Types of relationships between nodes."""

    # Existing relationships
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

    # Code structure relationships
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
    CREATES = "CREATES"        # Entity creates another entity
    IMPROVES = "IMPROVES"      # Entity improves another entity
    AFFECTS = "AFFECTS"        # Entity affects another entity
    STARTS_WITH = "STARTS_WITH"  # Phase starts with a commit
    ENDS_WITH = "ENDS_WITH"    # Phase ends with a commit

    # New relationships for reasoning structures
    REASONS_ABOUT = "REASONS_ABOUT"  # Reasoning node reasons about an entity
    HAS_ALTERNATIVE = "HAS_ALTERNATIVE"  # Question has an alternative
    HAS_CRITERION = "HAS_CRITERION"  # Question has a criterion
    NEXT_STEP = "NEXT_STEP"  # Step leads to the next step
    HAS_IMPLICATION = "HAS_IMPLICATION"  # Decision has an implication

    # New relationships for causal edges
    LEADS_TO = "LEADS_TO"  # Decision leads to an implication
    RESULTS_IN = "RESULTS_IN"  # Implication results in a code change
    IMPLEMENTS_DECISION = "IMPLEMENTS_DECISION"  # Code change implements a decision
    CAUSED_BY = "CAUSED_BY"  # Entity is caused by another entity
    INFLUENCES = "INFLUENCES"  # Entity influences another entity
    ADDRESSES = "ADDRESSES"  # Entity addresses a problem or requirement


class Node(BaseModel):
    """Base class for all nodes in the knowledge graph."""

    id: str
    type: NodeType
    title: Optional[str] = None
    body: Optional[str] = None
    ts: Optional[datetime] = None
    repo_id: Optional[str] = None  # Reference to repository
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


class RepositoryNode(Node):
    """A repository in the knowledge graph."""

    type: NodeType = NodeType.REPOSITORY
    name: str  # Repository name (e.g., "arc-memory")
    url: Optional[str] = None  # Repository URL (e.g., "https://github.com/Arc-Computer/arc-memory")
    local_path: str  # Local path where repository was cloned
    default_branch: str = "main"  # Default branch
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional metadata


class SystemNode(Node):
    """A system in the architecture."""

    type: NodeType = NodeType.SYSTEM
    name: str
    description: Optional[str] = None


class ServiceNode(Node):
    """A service in the system architecture."""

    type: NodeType = NodeType.SERVICE
    name: str  # Service name
    description: Optional[str] = None
    system_id: Optional[str] = None  # Reference to parent system
    apis: List[Dict[str, Any]] = Field(default_factory=list)  # API endpoints
    dependencies: List[str] = Field(default_factory=list)  # External dependencies


class ComponentNode(Node):
    """A component in the system architecture."""

    type: NodeType = NodeType.COMPONENT
    name: str  # Component name
    description: Optional[str] = None
    service_id: Optional[str] = None  # Reference to parent service
    files: List[str] = Field(default_factory=list)  # Files in this component
    responsibilities: List[str] = Field(default_factory=list)  # Component responsibilities


class InterfaceNode(Node):
    """An interface in the architecture."""

    type: NodeType = NodeType.INTERFACE
    name: str
    description: Optional[str] = None
    service_id: Optional[str] = None  # Reference to parent service
    interface_type: str = "api"  # api, event, etc.


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


class DecisionNode(Node):
    """A decision made during development."""

    type: NodeType = NodeType.DECISION
    decision_type: str  # Type of decision (architectural, implementation, etc.)
    decision_makers: List[str] = Field(default_factory=list)  # People who made the decision
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)  # Alternatives considered
    criteria: List[Dict[str, Any]] = Field(default_factory=list)  # Criteria used for evaluation
    confidence: float = 1.0  # Confidence score (0.0-1.0)
    source: Optional[str] = None  # Source of the decision (commit, PR, ADR, etc.)


class ImplicationNode(Node):
    """An implication of a decision."""

    type: NodeType = NodeType.IMPLICATION
    implication_type: str  # Type of implication (technical, business, etc.)
    severity: str = "medium"  # Severity of the implication (low, medium, high)
    scope: List[str] = Field(default_factory=list)  # Scope of the implication (files, components, etc.)
    confidence: float = 1.0  # Confidence score (0.0-1.0)
    source: Optional[str] = None  # Source of the implication (commit, PR, ADR, etc.)


class CodeChangeNode(Node):
    """A specific code change resulting from a decision or implication."""

    type: NodeType = NodeType.CODE_CHANGE
    change_type: str  # Type of change (feature, bugfix, refactoring, etc.)
    files: List[str] = Field(default_factory=list)  # Files affected by the change
    description: str  # Description of the change
    author: Optional[str] = None  # Author of the change
    commit_sha: Optional[str] = None  # SHA of the commit that made the change
    confidence: float = 1.0  # Confidence score (0.0-1.0)


