"""Return type models for Arc Memory SDK.

This module provides Pydantic models for the return types of Arc Memory SDK methods.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from arc_memory.schema.models import NodeType, EdgeRel


class QueryResult(BaseModel):
    """Result of a natural language query to the knowledge graph.

    This model represents the result of a natural language query to the knowledge graph,
    including the query, the answer, and supporting evidence.
    """

    query: str
    """The original query."""

    answer: str
    """The answer to the query."""

    confidence: float = 0.0
    """Confidence score for the answer (0.0-1.0)."""

    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    """Supporting evidence for the answer."""

    query_understanding: Optional[str] = None
    """How the system interpreted the query."""

    reasoning: Optional[str] = None
    """Reasoning process used to arrive at the answer."""

    execution_time: float = 0.0
    """Time taken to execute the query in seconds."""


class RelatedEntity(BaseModel):
    """A related entity in the knowledge graph.

    This model represents an entity related to another entity in the knowledge graph,
    including the relationship type and direction.
    """

    id: str
    """The ID of the related entity."""

    type: NodeType
    """The type of the related entity."""

    title: Optional[str] = None
    """The title of the related entity."""

    relationship: EdgeRel
    """The type of relationship."""

    direction: str
    """The direction of the relationship (incoming or outgoing)."""

    properties: Dict[str, Any] = Field(default_factory=dict)
    """Properties of the relationship."""


class EntityDetails(BaseModel):
    """Details of an entity in the knowledge graph.

    This model represents the details of an entity in the knowledge graph,
    including its properties and relationships.
    """

    id: str
    """The ID of the entity."""

    type: NodeType
    """The type of the entity."""

    title: Optional[str] = None
    """The title of the entity."""

    body: Optional[str] = None
    """The body or content of the entity."""

    timestamp: Optional[datetime] = None
    """The timestamp of the entity."""

    properties: Dict[str, Any] = Field(default_factory=dict)
    """Additional properties of the entity."""

    related_entities: List[RelatedEntity] = Field(default_factory=list)
    """Entities related to this entity."""


class GraphStatistics(BaseModel):
    """Statistics about the knowledge graph.

    This model represents statistics about the knowledge graph,
    including the number of nodes and edges.
    """

    node_count: int
    """The number of nodes in the graph."""

    edge_count: int
    """The number of edges in the graph."""

    node_types: Dict[str, int] = Field(default_factory=dict)
    """Count of nodes by type."""

    edge_types: Dict[str, int] = Field(default_factory=dict)
    """Count of edges by type."""

    last_updated: Optional[datetime] = None
    """When the graph was last updated."""

    build_time: Optional[float] = None
    """Time taken to build the graph in seconds."""


class DecisionTrailEntry(EntityDetails):
    """An entry in a decision trail.

    This model extends EntityDetails to include decision-specific information.
    """

    rationale: Optional[str] = None
    """The rationale behind this decision or change."""

    importance: float = 0.5
    """Importance score for this entry in the decision trail (0.0-1.0)."""

    trail_position: int = 0
    """Position in the decision trail (0 = most recent)."""


class ImpactResult(EntityDetails):
    """Result of an impact analysis.

    This model extends EntityDetails to include impact-specific information.
    """

    impact_type: str
    """Type of impact (direct, indirect, potential)."""

    impact_score: float
    """Score indicating the severity of the impact (0.0-1.0)."""

    impact_path: List[str] = Field(default_factory=list)
    """Path of entities showing how the impact propagates."""


class HistoryEntry(EntityDetails):
    """An entry in an entity's history.

    This model extends EntityDetails to include history-specific information.
    """

    change_type: str
    """Type of change (created, modified, referenced)."""

    previous_version: Optional[str] = None
    """ID of the previous version of this entity, if applicable."""


class ExportResult(BaseModel):
    """Result of exporting the knowledge graph.

    This model represents the result of exporting the knowledge graph to a file,
    including information about the export format, size, and location.
    """

    output_path: str
    """Path to the exported file."""

    format: str
    """Format of the export (json, csv, etc.)."""

    entity_count: int
    """Number of entities exported."""

    relationship_count: int
    """Number of relationships exported."""

    compressed: bool = False
    """Whether the export is compressed."""

    signed: bool = False
    """Whether the export is signed."""

    signature_path: Optional[str] = None
    """Path to the signature file, if signed."""

    execution_time: float = 0.0
    """Time taken to execute the export in seconds."""
