"""Schema models for Arc Memory.

This module defines the data models used in the Arc Memory application.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Type of node in the knowledge graph."""
    
    FILE = "file"
    SERVICE = "service"
    COMMIT = "commit"
    PR = "pr"
    ISSUE = "issue"
    ADR = "adr"
    SIMULATION = "simulation"
    METRIC = "metric"
    FAULT = "fault"
    ANNOTATION = "annotation"


class EdgeRel(str, Enum):
    """Type of relationship between nodes in the knowledge graph."""
    
    CONTAINS = "CONTAINS"
    DEPENDS_ON = "DEPENDS_ON"
    PART_OF = "PART_OF"
    AFFECTS = "AFFECTS"
    CAUSED_BY = "CAUSED_BY"
    HAS_METRIC = "HAS_METRIC"
    HAS_ANNOTATION = "HAS_ANNOTATION"


class Node:
    """Base class for all nodes in the knowledge graph."""
    
    def __init__(self, id: str, type: NodeType):
        """Initialize a Node.
        
        Args:
            id: Unique identifier for the node
            type: Type of the node
        """
        self.id = id
        self.type = type


class Edge:
    """Base class for all edges in the knowledge graph."""
    
    def __init__(self, src: str, dst: str, rel: EdgeRel):
        """Initialize an Edge.
        
        Args:
            src: ID of the source node
            dst: ID of the destination node
            rel: Type of relationship
        """
        self.src = src
        self.dst = dst
        self.rel = rel


class SimulationNode(Node):
    """Simulation node in the knowledge graph."""
    
    def __init__(
        self,
        id: str,
        type: NodeType,
        sim_id: str,
        rev_range: str,
        scenario: str,
        severity: int,
        risk_score: int,
        manifest_hash: str,
        commit_target: str,
        diff_hash: str,
        affected_services: List[str],
    ):
        """Initialize a SimulationNode.
        
        Args:
            id: Unique identifier for the node
            type: Type of the node
            sim_id: Simulation ID
            rev_range: Git revision range
            scenario: Fault scenario ID
            severity: Severity level
            risk_score: Risk score
            manifest_hash: Hash of the simulation manifest
            commit_target: Target commit hash
            diff_hash: Hash of the diff
            affected_services: List of affected services
        """
        super().__init__(id, type)
        self.sim_id = sim_id
        self.rev_range = rev_range
        self.scenario = scenario
        self.severity = severity
        self.risk_score = risk_score
        self.manifest_hash = manifest_hash
        self.commit_target = commit_target
        self.diff_hash = diff_hash
        self.affected_services = affected_services


class MetricNode(Node):
    """Metric node in the knowledge graph."""
    
    def __init__(
        self,
        id: str,
        type: NodeType,
        name: str,
        value: Union[int, float, str],
        unit: Optional[str] = None,
    ):
        """Initialize a MetricNode.
        
        Args:
            id: Unique identifier for the node
            type: Type of the node
            name: Metric name
            value: Metric value
            unit: Metric unit (optional)
        """
        super().__init__(id, type)
        self.name = name
        self.value = value
        self.unit = unit


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
