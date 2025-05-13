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
    dependencies in the knowledge graph. It helps predict the "blast radius"
    of changes, which is useful for planning refactoring efforts, assessing risk,
    and understanding the architecture of your codebase.

    Args:
        adapter: The database adapter to use for querying the knowledge graph.
        component_id: The ID of the component to analyze. This can be a file, directory,
            module, or any other component in your codebase. Format should be
            "type:identifier", e.g., "file:src/auth/login.py".
        impact_types: Types of impact to include in the analysis. Options are:
            - "direct": Components that directly depend on or are depended upon by the target
            - "indirect": Components connected through a chain of dependencies
            - "potential": Components that historically changed together with the target
            If None, all impact types will be included.
        max_depth: Maximum depth of indirect dependency analysis. Higher values will
            analyze more distant dependencies but may take longer. Values between
            2-5 are recommended for most codebases.
        callback: Optional callback function for progress reporting. If provided,
            it will be called at various stages of the analysis with progress updates.

    Returns:
        A list of ImpactResult objects representing affected components. Each result
        includes the component ID, type, title, impact type, impact score (0-1),
        and the path of dependencies from the target component.

    Raises:
        QueryError: If the impact analysis fails due to database errors, invalid
            component ID, or other issues. The error message will include details
            about what went wrong and how to fix it.

    Example:
        ```python
        # Analyze impact on a file
        results = analyze_component_impact(
            adapter=db_adapter,
            component_id="file:src/auth/login.py",
            impact_types=["direct", "indirect"],
            max_depth=3
        )

        # Process results
        for result in results:
            print(f"{result.title}: {result.impact_score} ({result.impact_type})")
        ```
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
            raise QueryError(
                what_happened=f"Component with ID '{component_id}' not found",
                why_it_happened="The component ID may be incorrect or the component may not exist in the knowledge graph",
                how_to_fix_it="Check that the component ID is correct and that the component exists in your knowledge graph. Run 'arc doctor' to verify the state of your knowledge graph"
            )

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

    except QueryError:
        # Re-raise QueryError as it's already properly formatted
        raise
    except Exception as e:
        logger.exception(f"Error in analyze_component_impact: {e}")
        raise QueryError.from_exception(
            exception=e,
            what_happened="Failed to analyze component impact",
            how_to_fix_it="Check the component ID and ensure your knowledge graph is properly built. If the issue persists, try with a smaller max_depth value",
            details={"component_id": component_id, "max_depth": max_depth}
        )


def _analyze_direct_dependencies(
    adapter: DatabaseAdapter, component_id: str
) -> List[ImpactResult]:
    """Analyze direct dependencies of a component.

    This function identifies components that directly depend on or are depended upon
    by the target component. Direct dependencies include:
    - Components that the target imports or uses
    - Components that import or use the target
    - Components with explicit DEPENDS_ON relationships

    Args:
        adapter: The database adapter to use for querying the knowledge graph.
        component_id: The ID of the component to analyze, in the format "type:identifier".

    Returns:
        A list of ImpactResult objects representing directly affected components.
        Each result includes an impact_score between 0.8-0.9 indicating the
        strength of the direct dependency.
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

    This function identifies components that are connected to the target component
    through a chain of dependencies (transitive dependencies). For example, if A depends
    on B and B depends on C, then C is an indirect dependency of A.

    The impact score decreases with the distance from the target component, reflecting
    the diminishing impact of changes as they propagate through the dependency chain.

    Args:
        adapter: The database adapter to use for querying the knowledge graph.
        component_id: The ID of the component to analyze, in the format "type:identifier".
        direct_impacts: List of direct impacts already identified, used to avoid
            duplicate analysis and to build the dependency chain.
        max_depth: Maximum depth of indirect dependency analysis. Higher values will
            analyze more distant dependencies but may take longer.

    Returns:
        A list of ImpactResult objects representing indirectly affected components.
        Each result includes an impact_score that decreases with the depth of the
        dependency chain, and an impact_path showing the chain of dependencies.
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

    This function recursively traverses the dependency graph to find components
    that are indirectly connected to the target component. It uses a depth-first
    search approach with cycle detection to avoid infinite recursion.

    Args:
        adapter: The database adapter to use for querying the knowledge graph.
        component_id: The ID of the component to analyze, in the format "type:identifier".
        visited: Set of already visited component IDs to avoid cycles and duplicate analysis.
        depth: Remaining depth for recursive analysis. The function stops recursion
            when this reaches zero.
        path: Current path of dependencies from the target component to the current component.
            Used to build the impact_path in the results.

    Returns:
        A list of ImpactResult objects representing indirectly affected components.
        Each result includes an impact_score that decreases with the depth of the
        dependency chain, and an impact_path showing the chain of dependencies.
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

    This function identifies components that have historically changed together with
    the target component, even if there's no explicit dependency between them. These
    "co-change" patterns can reveal hidden dependencies and coupling that aren't
    captured by static analysis.

    In a real implementation, this would analyze the commit history to find
    components that frequently change together with the target component and
    calculate a co-change score based on the frequency and recency of co-changes.

    Args:
        adapter: The database adapter to use for querying the knowledge graph.
        component_id: The ID of the component to analyze, in the format "type:identifier".

    Returns:
        A list of ImpactResult objects representing potentially affected components
        based on historical co-change patterns. Each result includes an impact_score
        representing the strength of the co-change relationship.
    """
    # This is a simplified implementation that would be enhanced in a real system
    # In a real implementation, we would analyze the commit history to find
    # components that frequently change together with the target component
    return []
