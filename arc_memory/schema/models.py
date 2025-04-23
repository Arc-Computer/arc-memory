"""Data models for Arc Memory."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    COMMIT = "commit"
    PR = "pr"
    ISSUE = "issue"
    ADR = "adr"


class EdgeRel(str, Enum):
    """Types of relationships between nodes."""

    MODIFIES = "MODIFIES"  # Commit modifies a file
    MERGES = "MERGES"      # PR merges a commit
    MENTIONS = "MENTIONS"  # PR/Issue mentions another entity
    DECIDES = "DECIDES"    # ADR decides on a file/commit


class Node(BaseModel):
    """Base class for all nodes in the knowledge graph."""

    id: str
    type: NodeType
    title: str
    body: str
    created_at: datetime
    extra: Dict[str, Any] = Field(default_factory=dict)


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

    node_count: int
    edge_count: int
    build_timestamp: datetime
    schema_version: str
    last_commit_hash: Optional[str] = None
    last_processed: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """A search result from the knowledge graph."""

    id: str
    type: NodeType
    title: str
    snippet: str
    score: float
