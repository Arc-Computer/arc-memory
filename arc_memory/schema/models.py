"""Data models for Arc Memory."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    COMMIT = "commit"
    FILE = "file"
    PR = "pr"
    ISSUE = "issue"
    ADR = "adr"
    SIMULATION = "simulation"  # A simulation run
    METRIC = "metric"  # A metric collected during simulation


class EdgeRel(str, Enum):
    """Types of relationships between nodes."""

    MODIFIES = "MODIFIES"  # Commit modifies a file
    MERGES = "MERGES"      # PR merges a commit
    MENTIONS = "MENTIONS"  # PR/Issue mentions another entity
    DECIDES = "DECIDES"    # ADR decides on a file/commit
    SIMULATES = "SIMULATES"  # Simulation simulates a commit/PR
    AFFECTS = "AFFECTS"    # Simulation affects a service
    MEASURES = "MEASURES"  # Simulation measures a metric
    PREDICTS = "PREDICTS"  # Simulation predicts an impact


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


class SimulationNode(Node):
    """A simulation run node."""

    type: NodeType = NodeType.SIMULATION
    sim_id: str  # Unique identifier for the simulation
    rev_range: str  # Git rev-range used for the simulation
    scenario: str  # The fault scenario that was simulated
    severity: int  # The severity level of the simulation (0-100)
    risk_score: int  # Calculated risk score (0-100)
    manifest_hash: str  # Hash of the simulation manifest
    commit_target: str  # Target commit hash
    diff_hash: str  # Hash of the diff
    affected_services: List[str] = Field(default_factory=list)  # List of services affected by the changes
    timestamp: Optional[datetime] = None  # Explicit timestamp field for the simulation


class MetricNode(Node):
    """A metric collected during simulation."""

    type: NodeType = NodeType.METRIC
    name: str  # Name of the metric
    value: float  # Value of the metric
    unit: Optional[str] = None  # Unit of the metric
    timestamp: datetime  # When the metric was collected
    service: Optional[str] = None  # Service the metric is associated with


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
