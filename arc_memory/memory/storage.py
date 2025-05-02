"""Storage functions for memory integration.

This module provides functions for storing simulation results in the knowledge graph,
creating nodes and edges that represent simulations, metrics, and their relationships
to code entities.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import (
    Edge,
    EdgeRel,
    SimulationNode,
    MetricNode,
)
from arc_memory.sql.db import add_nodes_and_edges, ensure_connection

logger = get_logger(__name__)


def create_simulation_node(
    sim_id: str,
    rev_range: str,
    scenario: str,
    severity: int,
    risk_score: int,
    manifest_hash: str,
    commit_target: str,
    diff_hash: str,
    affected_services: List[str],
    explanation: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> SimulationNode:
    """Create a node representing a simulation run.

    Args:
        sim_id: Unique identifier for the simulation
        rev_range: Git rev-range used for the simulation
        scenario: The fault scenario that was simulated
        severity: The severity level of the simulation (0-100)
        risk_score: Calculated risk score (0-100)
        manifest_hash: Hash of the simulation manifest
        commit_target: Target commit hash
        diff_hash: Hash of the diff
        affected_services: List of services affected by the changes
        explanation: Optional explanation of the simulation results
        timestamp: Optional timestamp for the simulation (defaults to now)

    Returns:
        A SimulationNode object
    """
    # Generate a unique ID for the simulation node
    node_id = f"simulation:{sim_id}"

    # Create a title for the simulation
    title = f"Simulation {sim_id} ({scenario}, severity {severity})"

    # Use the explanation as the body, or generate a simple one if not provided
    if not explanation:
        explanation = (
            f"Simulation of {scenario} scenario with severity {severity} "
            f"on rev-range {rev_range}. Risk score: {risk_score}/100."
        )

    # Create the simulation node
    current_time = timestamp or datetime.now()
    sim_node = SimulationNode(
        id=node_id,
        title=title,
        body=explanation,
        ts=current_time,
        timestamp=current_time,  # Set explicit timestamp field
        sim_id=sim_id,
        rev_range=rev_range,
        scenario=scenario,
        severity=severity,
        risk_score=risk_score,
        manifest_hash=manifest_hash,
        commit_target=commit_target,
        diff_hash=diff_hash,
        affected_services=affected_services,
    )

    logger.info(f"Created simulation node: {node_id}")
    return sim_node


def create_metric_nodes(
    sim_id: str,
    metrics: Dict[str, Any],
    timestamp: Optional[datetime] = None,
) -> List[MetricNode]:
    """Create nodes for metrics collected during simulation.

    Args:
        sim_id: Unique identifier for the simulation
        metrics: Dictionary of metrics collected during simulation
        timestamp: Optional timestamp for the metrics (defaults to now)

    Returns:
        A list of MetricNode objects
    """
    metric_nodes = []
    ts = timestamp or datetime.now()

    # Process each metric in the metrics dictionary
    for name, value in metrics.items():
        # Skip non-numeric metrics
        if not isinstance(value, (int, float)):
            continue

        # Generate a unique ID for the metric node
        metric_id = f"metric:{sim_id}:{name}"

        # Determine the unit based on the metric name
        unit = None
        if "latency" in name.lower() or "duration" in name.lower():
            unit = "ms"
        elif "rate" in name.lower() or "percentage" in name.lower():
            unit = "%"
        elif "count" in name.lower():
            unit = "count"

        # Create a title for the metric
        title = f"{name.replace('_', ' ').title()}: {value}"

        # Create the metric node
        metric_node = MetricNode(
            id=metric_id,
            title=title,
            body=f"Metric collected during simulation {sim_id}",
            ts=ts,
            name=name,
            value=float(value),
            unit=unit,
            timestamp=ts,  # Ensure timestamp is set
            service=None,  # We don't have service-specific metrics yet
        )

        metric_nodes.append(metric_node)

    logger.info(f"Created {len(metric_nodes)} metric nodes for simulation {sim_id}")
    return metric_nodes


def create_simulation_edges(
    sim_node: SimulationNode,
    metric_nodes: List[MetricNode],
    commit_id: Optional[str] = None,
    pr_id: Optional[str] = None,
    file_ids: Optional[List[str]] = None,
) -> List[Edge]:
    """Create edges connecting simulation nodes to related entities.

    Args:
        sim_node: The simulation node
        metric_nodes: List of metric nodes
        commit_id: Optional ID of the commit that was simulated
        pr_id: Optional ID of the PR that was simulated
        file_ids: Optional list of file IDs that were affected

    Returns:
        A list of Edge objects
    """
    edges = []

    # Connect simulation to metrics
    for metric_node in metric_nodes:
        # Use the simulation timestamp if metric timestamp is not available
        timestamp = metric_node.timestamp or sim_node.ts
        edges.append(
            Edge(
                src=sim_node.id,
                dst=metric_node.id,
                rel=EdgeRel.MEASURES,
                properties={
                    "timestamp": timestamp.isoformat() if timestamp else None,
                },
            )
        )

    # Connect simulation to commit if provided
    if commit_id:
        edges.append(
            Edge(
                src=sim_node.id,
                dst=commit_id,
                rel=EdgeRel.SIMULATES,
                properties={
                    "timestamp": sim_node.ts.isoformat() if sim_node.ts else None,
                    "rev_range": sim_node.rev_range,
                },
            )
        )

    # Connect simulation to PR if provided
    if pr_id:
        edges.append(
            Edge(
                src=sim_node.id,
                dst=pr_id,
                rel=EdgeRel.SIMULATES,
                properties={
                    "timestamp": sim_node.ts.isoformat() if sim_node.ts else None,
                    "rev_range": sim_node.rev_range,
                },
            )
        )

    # Connect simulation to affected files if provided
    if file_ids:
        for file_id in file_ids:
            edges.append(
                Edge(
                    src=sim_node.id,
                    dst=file_id,
                    rel=EdgeRel.AFFECTS,
                    properties={
                        "timestamp": sim_node.ts.isoformat() if sim_node.ts else None,
                    },
                )
            )

    # Connect simulation to affected services
    for service in sim_node.affected_services:
        # Create a service ID (this is a bit of a hack, as we don't have service nodes yet)
        service_id = f"service:{service}"

        # Add AFFECTS edge
        edges.append(
            Edge(
                src=sim_node.id,
                dst=service_id,
                rel=EdgeRel.AFFECTS,
                properties={
                    "timestamp": sim_node.ts.isoformat() if sim_node.ts else None,
                    "risk_score": sim_node.risk_score,
                },
            )
        )

        # Add PREDICTS edge
        edges.append(
            Edge(
                src=sim_node.id,
                dst=service_id,
                rel=EdgeRel.PREDICTS,
                properties={
                    "timestamp": sim_node.ts.isoformat() if sim_node.ts else None,
                    "prediction": f"Risk score: {sim_node.risk_score}/100",
                    "risk_score": sim_node.risk_score,
                },
            )
        )

    logger.info(f"Created {len(edges)} edges for simulation {sim_node.sim_id}")
    return edges


def store_simulation_results(
    conn_or_path: Any,
    sim_id: str,
    rev_range: str,
    scenario: str,
    severity: int,
    risk_score: int,
    manifest_hash: str,
    commit_target: str,
    diff_hash: str,
    affected_services: List[str],
    metrics: Dict[str, Any],
    explanation: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    commit_id: Optional[str] = None,
    pr_id: Optional[str] = None,
    file_ids: Optional[List[str]] = None,
) -> Tuple[SimulationNode, List[MetricNode]]:
    """Store simulation results in the knowledge graph.

    Args:
        conn_or_path: Database connection or path
        sim_id: Unique identifier for the simulation
        rev_range: Git rev-range used for the simulation
        scenario: The fault scenario that was simulated
        severity: The severity level of the simulation (0-100)
        risk_score: Calculated risk score (0-100)
        manifest_hash: Hash of the simulation manifest
        commit_target: Target commit hash
        diff_hash: Hash of the diff
        affected_services: List of services affected by the changes
        metrics: Dictionary of metrics collected during simulation
        explanation: Optional explanation of the simulation results
        timestamp: Optional timestamp for the simulation (defaults to now)
        commit_id: Optional ID of the commit that was simulated
        pr_id: Optional ID of the PR that was simulated
        file_ids: Optional list of file IDs that were affected

    Returns:
        A tuple of (SimulationNode, List[MetricNode])
    """
    # Get a valid connection
    conn = ensure_connection(conn_or_path)

    # Create the simulation node
    sim_node = create_simulation_node(
        sim_id=sim_id,
        rev_range=rev_range,
        scenario=scenario,
        severity=severity,
        risk_score=risk_score,
        manifest_hash=manifest_hash,
        commit_target=commit_target,
        diff_hash=diff_hash,
        affected_services=affected_services,
        explanation=explanation,
        timestamp=timestamp,
    )

    # Create metric nodes
    metric_nodes = create_metric_nodes(
        sim_id=sim_id,
        metrics=metrics,
        timestamp=timestamp or sim_node.ts,
    )

    # Create edges
    edges = create_simulation_edges(
        sim_node=sim_node,
        metric_nodes=metric_nodes,
        commit_id=commit_id,
        pr_id=pr_id,
        file_ids=file_ids,
    )

    # Add nodes and edges to the database
    nodes = [sim_node] + metric_nodes
    add_nodes_and_edges(conn, nodes, edges)

    logger.info(
        f"Stored simulation results in knowledge graph: "
        f"{len(nodes)} nodes, {len(edges)} edges"
    )

    return sim_node, metric_nodes
