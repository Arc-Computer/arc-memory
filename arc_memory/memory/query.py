"""Query functions for memory integration.

This module provides functions for querying past simulations from the knowledge graph,
enabling the retrieval of historical context for similar changes and their outcomes.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import (
    NodeType,
    EdgeRel,
    SimulationNode,
    MetricNode,
)
from arc_memory.sql.db import (
    ensure_connection,
    get_node_by_id,
    get_edges_by_src,
    get_edges_by_dst,
)

logger = get_logger(__name__)


def _node_to_simulation(node_data: Dict[str, Any]) -> Optional[SimulationNode]:
    """Convert a node dictionary to a SimulationNode object.

    Args:
        node_data: Node data from the database

    Returns:
        A SimulationNode object or None if conversion fails
    """
    try:
        # Check if this is a simulation node
        if node_data["type"] != NodeType.SIMULATION.value:
            return None

        # Extract extra data
        extra = node_data.get("extra", {})

        # Parse timestamp
        ts = None
        if extra.get("ts"):
            try:
                ts = datetime.fromisoformat(extra.get("ts"))
            except ValueError:
                logger.warning(f"Failed to parse ts: {extra.get('ts')}")

        # Parse explicit timestamp if available
        timestamp = None
        if extra.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(extra.get("timestamp"))
            except ValueError:
                logger.warning(f"Failed to parse timestamp: {extra.get('timestamp')}")

        # Use ts as timestamp if timestamp is not available
        if not timestamp:
            timestamp = ts

        # Create a SimulationNode
        return SimulationNode(
            id=node_data["id"],
            title=node_data.get("title"),
            body=node_data.get("body"),
            ts=ts,
            timestamp=timestamp,
            sim_id=extra.get("sim_id", ""),
            rev_range=extra.get("rev_range", ""),
            scenario=extra.get("scenario", ""),
            severity=extra.get("severity", 0),
            risk_score=extra.get("risk_score", 0),
            manifest_hash=extra.get("manifest_hash", ""),
            commit_target=extra.get("commit_target", ""),
            diff_hash=extra.get("diff_hash", ""),
            affected_services=extra.get("affected_services", []),
        )
    except Exception as e:
        logger.error(f"Error converting node to simulation: {e}")
        return None


def _node_to_metric(node_data: Dict[str, Any]) -> Optional[MetricNode]:
    """Convert a node dictionary to a MetricNode object.

    Args:
        node_data: Node data from the database

    Returns:
        A MetricNode object or None if conversion fails
    """
    try:
        # Check if this is a metric node
        if node_data["type"] != NodeType.METRIC.value:
            return None

        # Extract extra data
        extra = node_data.get("extra", {})

        # Parse timestamps
        ts = None
        if extra.get("ts"):
            try:
                ts = datetime.fromisoformat(extra.get("ts"))
            except ValueError:
                logger.warning(f"Failed to parse ts: {extra.get('ts')}")

        timestamp = None
        if extra.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(extra.get("timestamp"))
            except ValueError:
                logger.warning(f"Failed to parse timestamp: {extra.get('timestamp')}")

        # Use ts as timestamp if timestamp is not available
        if not timestamp:
            timestamp = ts or datetime.now()

        # Create a MetricNode
        return MetricNode(
            id=node_data["id"],
            title=node_data.get("title"),
            body=node_data.get("body"),
            ts=ts or datetime.now(),
            name=extra.get("name", ""),
            value=float(extra.get("value", 0.0)),
            unit=extra.get("unit"),
            timestamp=timestamp,
            service=extra.get("service"),
        )
    except Exception as e:
        logger.error(f"Error converting node to metric: {e}")
        return None


def get_simulation_by_id(
    conn_or_path: Any,
    sim_id: str,
) -> Optional[SimulationNode]:
    """Get a simulation by its ID.

    Args:
        conn_or_path: Database connection or path
        sim_id: Simulation ID (either the full node ID or just the sim_id part)

    Returns:
        A SimulationNode object or None if not found
    """
    # Get a valid connection
    conn = ensure_connection(conn_or_path)

    # Normalize the simulation ID
    if not sim_id.startswith("simulation:"):
        node_id = f"simulation:{sim_id}"
    else:
        node_id = sim_id

    # Get the node from the database
    node_data = get_node_by_id(conn, node_id)
    if not node_data:
        logger.warning(f"Simulation not found: {sim_id}")
        return None

    # Convert to a SimulationNode
    sim_node = _node_to_simulation(node_data)
    if not sim_node:
        logger.warning(f"Failed to convert node to simulation: {node_id}")
        return None

    logger.info(f"Retrieved simulation: {sim_id}")
    return sim_node


def get_simulations_by_service(
    conn_or_path: Any,
    service: str,
    limit: int = 10,
) -> List[SimulationNode]:
    """Get simulations that affected a specific service.

    Args:
        conn_or_path: Database connection or path
        service: Service name
        limit: Maximum number of simulations to return

    Returns:
        A list of SimulationNode objects
    """
    # Get a valid connection
    conn = ensure_connection(conn_or_path)

    # Normalize the service ID
    if not service.startswith("service:"):
        service_id = f"service:{service}"
    else:
        service_id = service

    # Get edges where the service is the destination and the relationship is AFFECTS
    edges = get_edges_by_dst(conn, service_id, rel_type=EdgeRel.AFFECTS)

    # Get the simulation nodes
    simulations = []
    for edge in edges:
        # Get the simulation node
        node_data = get_node_by_id(conn, edge["src"])
        if not node_data:
            continue

        # Convert to a SimulationNode
        sim_node = _node_to_simulation(node_data)
        if sim_node:
            simulations.append(sim_node)

        # Check if we've reached the limit
        if len(simulations) >= limit:
            break

    logger.info(f"Retrieved {len(simulations)} simulations for service: {service}")
    return simulations


def get_simulations_by_file(
    conn_or_path: Any,
    file_path: str,
    limit: int = 10,
) -> List[SimulationNode]:
    """Get simulations that involved changes to a specific file.

    Args:
        conn_or_path: Database connection or path
        file_path: File path
        limit: Maximum number of simulations to return

    Returns:
        A list of SimulationNode objects
    """
    # Get a valid connection
    conn = ensure_connection(conn_or_path)

    # Normalize the file ID
    if not file_path.startswith("file:"):
        file_id = f"file:{file_path}"
    else:
        file_id = file_path

    # Get edges where the file is the destination and the relationship is AFFECTS
    edges = get_edges_by_dst(conn, file_id, rel_type=EdgeRel.AFFECTS)

    # Get the simulation nodes
    simulations = []
    for edge in edges:
        # Get the simulation node
        node_data = get_node_by_id(conn, edge["src"])
        if not node_data:
            continue

        # Convert to a SimulationNode
        sim_node = _node_to_simulation(node_data)
        if sim_node:
            simulations.append(sim_node)

        # Check if we've reached the limit
        if len(simulations) >= limit:
            break

    logger.info(f"Retrieved {len(simulations)} simulations for file: {file_path}")
    return simulations


def get_similar_simulations(
    conn_or_path: Any,
    affected_services: List[str],
    scenario: Optional[str] = None,
    severity_range: Optional[Tuple[int, int]] = None,
    limit: int = 5,
) -> List[SimulationNode]:
    """Find simulations similar to a given one.

    Args:
        conn_or_path: Database connection or path
        affected_services: List of services affected by the changes
        scenario: Optional scenario to filter by
        severity_range: Optional tuple of (min_severity, max_severity)
        limit: Maximum number of simulations to return

    Returns:
        A list of SimulationNode objects
    """
    # Get a valid connection
    conn = ensure_connection(conn_or_path)

    # Get all simulation nodes
    # Note: This is not efficient for large databases, but it's simple for now
    # In a real implementation, we would use a more efficient query
    try:
        cursor = conn.execute(
            """
            SELECT id, type, title, body, extra
            FROM nodes
            WHERE type = ?
            """,
            (NodeType.SIMULATION.value,),
        )

        # Convert to SimulationNode objects
        all_simulations = []
        for row in cursor:
            node_data = {
                "id": row[0],
                "type": row[1],
                "title": row[2],
                "body": row[3],
                "extra": json.loads(row[4]) if row[4] else {},
            }

            sim_node = _node_to_simulation(node_data)
            if sim_node:
                all_simulations.append(sim_node)

        # Filter by scenario if provided
        if scenario:
            all_simulations = [
                sim for sim in all_simulations
                if sim.scenario == scenario
            ]

        # Filter by severity range if provided
        if severity_range:
            min_severity, max_severity = severity_range
            all_simulations = [
                sim for sim in all_simulations
                if min_severity <= sim.severity <= max_severity
            ]

        # Calculate similarity based on affected services
        # This is a simple implementation that counts the number of matching services
        similar_simulations = []
        for sim in all_simulations:
            # Count the number of matching services
            matching_services = set(sim.affected_services) & set(affected_services)
            similarity_score = len(matching_services) / max(
                len(sim.affected_services), len(affected_services), 1
            )

            # Only consider simulations with at least one matching service
            if matching_services:
                similar_simulations.append((sim, similarity_score))

        # Sort by similarity score (descending)
        similar_simulations.sort(key=lambda x: x[1], reverse=True)

        # Return the top N simulations
        result = [sim for sim, _ in similar_simulations[:limit]]

        logger.info(f"Retrieved {len(result)} similar simulations")
        return result
    except Exception as e:
        logger.error(f"Error retrieving similar simulations: {e}")
        return []


def get_simulation_metrics(
    conn_or_path: Any,
    sim_id: str,
) -> List[MetricNode]:
    """Get metrics for a specific simulation.

    Args:
        conn_or_path: Database connection or path
        sim_id: Simulation ID (either the full node ID or just the sim_id part)

    Returns:
        A list of MetricNode objects
    """
    # Get a valid connection
    conn = ensure_connection(conn_or_path)

    # Normalize the simulation ID
    if not sim_id.startswith("simulation:"):
        node_id = f"simulation:{sim_id}"
    else:
        node_id = sim_id

    # Get edges where the simulation is the source and the relationship is MEASURES
    edges = get_edges_by_src(conn, node_id, rel_type=EdgeRel.MEASURES)

    # Get the metric nodes
    metrics = []
    for edge in edges:
        # Get the metric node
        node_data = get_node_by_id(conn, edge["dst"])
        if not node_data:
            continue

        # Convert to a MetricNode
        metric_node = _node_to_metric(node_data)
        if metric_node:
            metrics.append(metric_node)

    logger.info(f"Retrieved {len(metrics)} metrics for simulation: {sim_id}")
    return metrics
