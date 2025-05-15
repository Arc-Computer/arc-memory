"""
Custom Impact Analysis for Code Time Machine Demo

This module provides a custom implementation of the impact analysis that uses
the relationships we have in our graph.
"""

from typing import Any, Dict, List, Optional, Set

from arc_memory.db.base import DatabaseAdapter
from arc_memory.sdk.models import ImpactResult


def analyze_component_impact(
    adapter: DatabaseAdapter,
    component_id: str,
    impact_types: Optional[List[str]] = None,
    max_depth: int = 3
) -> List[ImpactResult]:
    """Analyze the potential impact of changes to a component.

    This is a custom implementation that uses the relationships we have in our graph.

    Args:
        adapter: The database adapter to use for querying the knowledge graph.
        component_id: The ID of the component to analyze.
        impact_types: Types of impact to include in the analysis.
        max_depth: Maximum depth of indirect dependency analysis.

    Returns:
        A list of ImpactResult objects representing affected components.
    """
    # Default impact types
    if impact_types is None:
        impact_types = ["direct", "indirect", "potential"]

    # Get the component node
    component = adapter.get_node_by_id(component_id)
    if not component:
        return []

    results = []

    # Analyze direct dependencies (CORRELATES_WITH, CONTAINS, MODIFIES, etc.)
    direct_impacts = []
    if "direct" in impact_types:
        direct_impacts = _analyze_direct_dependencies(adapter, component_id)
        results.extend(direct_impacts)

    # Analyze indirect dependencies
    if "indirect" in impact_types and direct_impacts:
        indirect_impacts = _analyze_indirect_dependencies(
            adapter, component_id, direct_impacts, max_depth
        )
        results.extend(indirect_impacts)

    # Analyze co-change patterns (MODIFIES relationships from commits)
    if "potential" in impact_types:
        potential_impacts = _analyze_cochange_patterns(adapter, component_id)
        results.extend(potential_impacts)

    return results


def _analyze_direct_dependencies(
    adapter: DatabaseAdapter, component_id: str
) -> List[ImpactResult]:
    """Analyze direct dependencies of a component.

    This function identifies components that are directly related to the target component.

    Args:
        adapter: The database adapter to use for querying the knowledge graph.
        component_id: The ID of the component to analyze.

    Returns:
        A list of ImpactResult objects representing directly affected components.
    """
    results = []

    # Get outgoing edges (any relationship type)
    outgoing_edges = adapter.get_edges_by_src(component_id)
    for edge in outgoing_edges:
        # Include all relationship types
        target = adapter.get_node_by_id(edge["dst"])
        if target:
            # Assign impact score based on relationship type
            impact_score = 0.9
            if edge["rel"] == "CORRELATES_WITH":
                impact_score = 0.85
            elif edge["rel"] == "CONTAINS":
                impact_score = 0.95

            results.append(
                ImpactResult(
                    id=target["id"],
                    type=target["type"],
                    title=target.get("title"),
                    body=target.get("body"),
                    properties={},
                    related_entities=[],
                    impact_type="direct",
                    impact_score=impact_score,
                    impact_path=[component_id, target["id"]]
                )
            )

    # Get incoming edges (any relationship type)
    incoming_edges = adapter.get_edges_by_dst(component_id)
    for edge in incoming_edges:
        # Only include certain relationship types for incoming edges
        if edge["rel"] in ["MODIFIES", "CONTAINS", "CORRELATES_WITH"]:
            source = adapter.get_node_by_id(edge["src"])
            if source and source["type"] != "commit":  # Skip commit nodes
                # Assign impact score based on relationship type
                impact_score = 0.8
                if edge["rel"] == "CORRELATES_WITH":
                    impact_score = 0.75
                elif edge["rel"] == "CONTAINS":
                    impact_score = 0.85

                results.append(
                    ImpactResult(
                        id=source["id"],
                        type=source["type"],
                        title=source.get("title"),
                        body=source.get("body"),
                        properties={},
                        related_entities=[],
                        impact_type="direct",
                        impact_score=impact_score,
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
        adapter: The database adapter to use for querying the knowledge graph.
        component_id: The ID of the component to analyze.
        direct_impacts: List of direct impacts already identified.
        max_depth: Maximum depth of indirect dependency analysis.

    Returns:
        A list of ImpactResult objects representing indirectly affected components.
    """
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
        adapter: The database adapter to use for querying the knowledge graph.
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
        # Include all relationship types
        target_id = edge["dst"]
        if target_id not in visited:
            visited.add(target_id)
            target = adapter.get_node_by_id(target_id)
            if target:
                # Calculate impact score based on depth and relationship type
                impact_score = 0.7 / depth
                if edge["rel"] == "CORRELATES_WITH":
                    impact_score = 0.65 / depth
                elif edge["rel"] == "CONTAINS":
                    impact_score = 0.75 / depth

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
        adapter: The database adapter to use for querying the knowledge graph.
        component_id: The ID of the component to analyze.

    Returns:
        A list of ImpactResult objects representing potentially affected components.
    """
    results = []

    # Get incoming MODIFIES edges from commits
    incoming_edges = adapter.get_edges_by_dst(component_id)
    commit_ids = []
    for edge in incoming_edges:
        if edge["rel"] == "MODIFIES" and edge["src"].startswith("commit:"):
            commit_ids.append(edge["src"])

    # For each commit, find other files that were modified
    visited = {component_id}
    for commit_id in commit_ids:
        outgoing_edges = adapter.get_edges_by_src(commit_id)
        for edge in outgoing_edges:
            if edge["rel"] == "MODIFIES" and edge["dst"] != component_id and edge["dst"] not in visited:
                visited.add(edge["dst"])
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
                            impact_type="potential",
                            impact_score=0.6,
                            impact_path=[component_id, commit_id, target["id"]]
                        )
                    )

    return results
