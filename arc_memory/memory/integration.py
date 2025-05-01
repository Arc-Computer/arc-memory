"""Integration functions for memory integration.

This module provides functions for integrating memory with the simulation workflow,
enabling the storage of simulation results in memory and the retrieval of relevant
past simulations to enhance explanation generation.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Tuple, cast

from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import (
    Node,
    Edge,
    NodeType,
    EdgeRel,
    SimulationNode,
    MetricNode,
)
from arc_memory.sql.db import ensure_connection, get_connection
from arc_memory.memory.storage import store_simulation_results
from arc_memory.memory.query import get_similar_simulations

logger = get_logger(__name__)


def store_simulation_in_memory(
    db_path: str,
    attestation: Dict[str, Any],
    metrics: Dict[str, Any],
    affected_services: List[str],
    diff_data: Optional[Dict[str, Any]] = None,
) -> Optional[SimulationNode]:
    """Store simulation results in memory.

    Args:
        db_path: Path to the knowledge graph database
        attestation: Attestation data from the simulation
        metrics: Metrics collected during the simulation
        affected_services: List of services affected by the changes
        diff_data: Optional diff data from the simulation

    Returns:
        The created SimulationNode or None if storage fails
    """
    try:
        # Extract data from the attestation
        sim_id = attestation.get("sim_id", "")
        rev_range = attestation.get("rev_range", "")
        scenario = attestation.get("scenario", "")
        severity = attestation.get("severity", 0)
        risk_score = attestation.get("risk_score", 0)
        manifest_hash = attestation.get("manifest_hash", "")
        commit_target = attestation.get("commit_target", "")
        diff_hash = attestation.get("diff_hash", "")
        explanation = attestation.get("explanation", "")
        
        # Parse the timestamp
        timestamp_str = attestation.get("timestamp", "")
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Failed to parse timestamp: {timestamp_str}")
        
        # Extract file IDs from diff data if available
        file_ids = None
        if diff_data and "files" in diff_data:
            file_ids = [f"file:{file['path']}" for file in diff_data["files"]]
        
        # Extract commit ID from diff data if available
        commit_id = None
        if diff_data and "end_commit" in diff_data:
            commit_id = f"commit:{diff_data['end_commit']}"
        
        # Store the simulation results
        conn = get_connection(db_path)
        sim_node, _ = store_simulation_results(
            conn_or_path=conn,
            sim_id=sim_id,
            rev_range=rev_range,
            scenario=scenario,
            severity=severity,
            risk_score=risk_score,
            manifest_hash=manifest_hash,
            commit_target=commit_target,
            diff_hash=diff_hash,
            affected_services=affected_services,
            metrics=metrics,
            explanation=explanation,
            timestamp=timestamp,
            commit_id=commit_id,
            file_ids=file_ids,
        )
        
        logger.info(f"Stored simulation in memory: {sim_id}")
        return sim_node
    except Exception as e:
        logger.error(f"Error storing simulation in memory: {e}")
        return None


def retrieve_relevant_simulations(
    db_path: str,
    affected_services: List[str],
    scenario: str,
    severity: int,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """Retrieve simulations relevant to current changes.

    Args:
        db_path: Path to the knowledge graph database
        affected_services: List of services affected by the changes
        scenario: The fault scenario being simulated
        severity: The severity level of the simulation (0-100)
        limit: Maximum number of simulations to return

    Returns:
        A list of relevant simulations as dictionaries
    """
    try:
        # Define a severity range (±20 points)
        min_severity = max(0, severity - 20)
        max_severity = min(100, severity + 20)
        
        # Get similar simulations
        conn = get_connection(db_path)
        similar_sims = get_similar_simulations(
            conn_or_path=conn,
            affected_services=affected_services,
            scenario=scenario,
            severity_range=(min_severity, max_severity),
            limit=limit,
        )
        
        # Convert to dictionaries for easier consumption
        result = []
        for sim in similar_sims:
            result.append({
                "sim_id": sim.sim_id,
                "scenario": sim.scenario,
                "severity": sim.severity,
                "risk_score": sim.risk_score,
                "affected_services": sim.affected_services,
                "explanation": sim.body,
                "timestamp": sim.ts.isoformat() if sim.ts else None,
            })
        
        logger.info(f"Retrieved {len(result)} relevant simulations")
        return result
    except Exception as e:
        logger.error(f"Error retrieving relevant simulations: {e}")
        return []


def enhance_explanation_with_memory(
    db_path: str,
    explanation: str,
    affected_services: List[str],
    scenario: str,
    severity: int,
    risk_score: int,
) -> str:
    """Enhance explanation generation with historical context.

    Args:
        db_path: Path to the knowledge graph database
        explanation: Original explanation
        affected_services: List of services affected by the changes
        scenario: The fault scenario being simulated
        severity: The severity level of the simulation (0-100)
        risk_score: Calculated risk score (0-100)

    Returns:
        Enhanced explanation with historical context
    """
    try:
        # Retrieve relevant simulations
        relevant_sims = retrieve_relevant_simulations(
            db_path=db_path,
            affected_services=affected_services,
            scenario=scenario,
            severity=severity,
        )
        
        # If no relevant simulations, return the original explanation
        if not relevant_sims:
            return explanation
        
        # Enhance the explanation with historical context
        enhanced_explanation = explanation
        
        # Add a section about historical context
        enhanced_explanation += "\n\n## Historical Context\n\n"
        
        # Add information about similar simulations
        enhanced_explanation += f"Based on {len(relevant_sims)} similar simulations in the past:\n\n"
        
        # Calculate average risk score of similar simulations
        avg_risk_score = sum(sim["risk_score"] for sim in relevant_sims) / len(relevant_sims)
        
        # Compare current risk score with historical average
        if risk_score > avg_risk_score + 10:
            enhanced_explanation += f"- This change has a **higher risk** ({risk_score}) than similar changes in the past (avg: {avg_risk_score:.1f}).\n"
        elif risk_score < avg_risk_score - 10:
            enhanced_explanation += f"- This change has a **lower risk** ({risk_score}) than similar changes in the past (avg: {avg_risk_score:.1f}).\n"
        else:
            enhanced_explanation += f"- This change has a **similar risk** ({risk_score}) to similar changes in the past (avg: {avg_risk_score:.1f}).\n"
        
        # Add specific examples
        enhanced_explanation += "\nRelevant historical simulations:\n\n"
        
        for i, sim in enumerate(relevant_sims, 1):
            sim_date = sim.get("timestamp", "").split("T")[0] if sim.get("timestamp") else "Unknown date"
            enhanced_explanation += f"{i}. **Simulation {sim['sim_id']}** ({sim_date}): Risk score {sim['risk_score']}/100\n"
            
            # Add a brief summary of the simulation
            if sim.get("explanation"):
                # Extract the first sentence or up to 100 characters
                summary = sim["explanation"].split(".")[0]
                if len(summary) > 100:
                    summary = summary[:97] + "..."
                enhanced_explanation += f"   {summary}\n"
        
        logger.info("Enhanced explanation with historical context")
        return enhanced_explanation
    except Exception as e:
        logger.error(f"Error enhancing explanation with memory: {e}")
        return explanation
