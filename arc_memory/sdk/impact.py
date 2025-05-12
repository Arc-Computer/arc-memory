"""Component Impact API for Arc Memory SDK.

This module provides methods for analyzing the potential impact of changes
to components in the codebase.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from arc_memory.db.base import DatabaseAdapter
from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import EdgeRel, NodeType
from arc_memory.sdk.cache import cached
from arc_memory.sdk.errors import QueryError
from arc_memory.sdk.models import ImpactResult
from arc_memory.sdk.progress import ProgressCallback, ProgressStage

logger = get_logger(__name__)


@cached()
def analyze_component_impact(
    adapter: DatabaseAdapter,
    component_id: str,
    impact_types: Optional[List[str]] = None,
    max_depth: int = 3,
    callback: Optional[ProgressCallback] = None
) -> List[ImpactResult]:
    """Analyze the potential impact of changes to a component.

    This method identifies components that may be affected by changes to the
    specified component, based on historical co-change patterns and explicit
    dependencies in the knowledge graph.

    Args:
        adapter: The database adapter to use.
        component_id: The ID of the component to analyze.
        impact_types: Types of impact to include (direct, indirect, potential).
        max_depth: Maximum depth of impact analysis.
        callback: Optional callback for progress reporting.

    Returns:
        A list of ImpactResult objects representing affected components.

    Raises:
        QueryError: If the impact analysis fails.
    """
    try:
        # Report progress
        if callback:
            callback(
                ProgressStage.INITIALIZING,
                "Initializing impact analysis",
                0.0
            )

        # Default impact types
        if impact_types is None:
            impact_types = ["direct", "indirect", "potential"]

        # Get the component node
        component = adapter.get_node_by_id(component_id)
        if not component:
            raise QueryError(f"Component not found: {component_id}")

        # Report progress
        if callback:
            callback(
                ProgressStage.QUERYING,
                "Analyzing direct dependencies",
                0.2
            )

        # Analyze direct dependencies
        direct_impacts = _analyze_direct_dependencies(adapter, component_id)

        # Report progress
        if callback:
            callback(
                ProgressStage.PROCESSING,
                "Analyzing indirect dependencies",
                0.4
            )

        # Analyze indirect dependencies
        indirect_impacts = _analyze_indirect_dependencies(
            adapter, component_id, direct_impacts, max_depth
        )

        # Report progress
        if callback:
            callback(
                ProgressStage.ANALYZING,
                "Analyzing co-change patterns",
                0.6
            )

        # Analyze co-change patterns
        potential_impacts = _analyze_cochange_patterns(adapter, component_id)

        # Report progress
        if callback:
            callback(
                ProgressStage.COMPLETING,
                "Impact analysis complete",
                1.0
            )

        # Combine results based on requested impact types
        results = []
        if "direct" in impact_types:
            results.extend(direct_impacts)
        if "indirect" in impact_types:
            results.extend(indirect_impacts)
        if "potential" in impact_types:
            results.extend(potential_impacts)

        return results

    except Exception as e:
        logger.exception(f"Error in analyze_component_impact: {e}")
        raise QueryError(f"Failed to analyze component impact: {e}")


def _analyze_direct_dependencies(
    adapter: DatabaseAdapter, component_id: str
) -> List[ImpactResult]:
    """Analyze direct dependencies of a component.

    Args:
        adapter: The database adapter to use.
        component_id: The ID of the component to analyze.

    Returns:
        A list of ImpactResult objects representing directly affected components.
    """
    # This is a simplified implementation that would be enhanced in a real system
    results = []

    # Get outgoing edges
    outgoing_edges = adapter.get_edges_by_src(component_id)
    for edge in outgoing_edges:
        if edge["rel"] in ["DEPENDS_ON", "IMPORTS", "USES"]:
            target = adapter.get_node_by_id(edge["dst"])
            if target:
                results.append(
                    ImpactResult(
                        id=target["id"],
                        type=target["type"],
                        title=target.get("title"),
                        body=target.get("body"),
                        properties={},
                        related_entities=[],
                        impact_type="direct",
                        impact_score=0.9,
                        impact_path=[component_id, target["id"]]
                    )
                )

    # Get incoming edges
    incoming_edges = adapter.get_edges_by_dst(component_id)
    for edge in incoming_edges:
        if edge["rel"] in ["DEPENDS_ON", "IMPORTS", "USES"]:
            source = adapter.get_node_by_id(edge["src"])
            if source:
                results.append(
                    ImpactResult(
                        id=source["id"],
                        type=source["type"],
                        title=source.get("title"),
                        body=source.get("body"),
                        properties={},
                        related_entities=[],
                        impact_type="direct",
                        impact_score=0.8,
                        impact_path=[component_id, source["id"]]
                    )
                )

    return results


def _analyze_indirect_dependencies(
    adapter: DatabaseAdapter,
    component_id: str,
    direct_impacts: List[ImpactResult],
    max_depth: int
) -> List[ImpactResult]:
    """Analyze indirect dependencies of a component.

    Args:
        adapter: The database adapter to use.
        component_id: The ID of the component to analyze.
        direct_impacts: List of direct impacts already identified.
        max_depth: Maximum depth of indirect dependency analysis.

    Returns:
        A list of ImpactResult objects representing indirectly affected components.
    """
    # This is a simplified implementation that would be enhanced in a real system
    results = []
    visited = {component_id}
    for impact in direct_impacts:
        visited.add(impact.id)

    # Process each direct impact to find indirect impacts
    for impact in direct_impacts:
        # Recursively find dependencies up to max_depth
        indirect = _find_indirect_dependencies(
            adapter, impact.id, visited, max_depth - 1, [component_id, impact.id]
        )
        results.extend(indirect)

    return results


def _find_indirect_dependencies(
    adapter: DatabaseAdapter,
    component_id: str,
    visited: Set[str],
    depth: int,
    path: List[str]
) -> List[ImpactResult]:
    """Recursively find indirect dependencies.

    Args:
        adapter: The database adapter to use.
        component_id: The ID of the component to analyze.
        visited: Set of already visited component IDs.
        depth: Remaining depth for recursive analysis.
        path: Current path of dependencies.

    Returns:
        A list of ImpactResult objects representing indirectly affected components.
    """
    if depth <= 0:
        return []

    results = []

    # Get outgoing edges
    outgoing_edges = adapter.get_edges_by_src(component_id)
    for edge in outgoing_edges:
        if edge["rel"] in ["DEPENDS_ON", "IMPORTS", "USES"]:
            target_id = edge["dst"]
            if target_id not in visited:
                visited.add(target_id)
                target = adapter.get_node_by_id(target_id)
                if target:
                    # Calculate impact score based on depth
                    impact_score = 0.7 / depth

                    # Create impact result
                    new_path = path + [target_id]
                    results.append(
                        ImpactResult(
                            id=target["id"],
                            type=target["type"],
                            title=target.get("title"),
                            body=target.get("body"),
                            properties={},
                            related_entities=[],
                            impact_type="indirect",
                            impact_score=impact_score,
                            impact_path=new_path
                        )
                    )

                    # Recursively find more dependencies
                    indirect = _find_indirect_dependencies(
                        adapter, target_id, visited, depth - 1, new_path
                    )
                    results.extend(indirect)

    return results


def _analyze_cochange_patterns(
    adapter: DatabaseAdapter, component_id: str
) -> List[ImpactResult]:
    """Analyze co-change patterns for a component.

    Args:
        adapter: The database adapter to use.
        component_id: The ID of the component to analyze.

    Returns:
        A list of ImpactResult objects representing potentially affected components.
    """
    # This is a simplified implementation that would be enhanced in a real system
    # In a real implementation, we would analyze the commit history to find
    # components that frequently change together with the target component
    return []
