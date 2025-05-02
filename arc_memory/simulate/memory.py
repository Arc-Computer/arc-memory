"""Memory integration for Arc Memory simulation.

This module provides a simplified wrapper around the memory integration functions
for storing simulation results in the knowledge graph and retrieving relevant
past simulations to enhance explanation generation.
"""

import os
from typing import Dict, List, Any, Optional

from arc_memory.logging_conf import get_logger
from arc_memory.schema.models import SimulationNode
from arc_memory.sql.db import ensure_arc_dir

# Import the memory integration functions
from arc_memory.memory.integration import (
    store_simulation_in_memory as _store_simulation_in_memory,
    retrieve_relevant_simulations,
    enhance_explanation_with_memory,
)

logger = get_logger(__name__)


def store_simulation_in_memory(
    rev_range: str,
    scenario: str,
    severity: int,
    risk_score: int,
    affected_services: List[str],
    metrics: Dict[str, Any],
    explanation: str,
    attestation: Optional[Dict[str, Any]] = None,
    diff_data: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None,
) -> Optional[SimulationNode]:
    """Store simulation results in memory.
    
    Args:
        rev_range: Git revision range
        scenario: Fault scenario ID
        severity: Severity level (0-100)
        risk_score: Calculated risk score
        affected_services: List of affected service names
        metrics: Processed metrics from the simulation
        explanation: Human-readable explanation
        attestation: Attestation data (optional)
        diff_data: Diff data (optional)
        db_path: Path to the knowledge graph database (optional)
        
    Returns:
        The created SimulationNode or None if storage fails
    """
    try:
        # Get the database path
        if db_path is None:
            arc_dir = ensure_arc_dir()
            db_path = str(arc_dir / "graph.db")
        
        # If attestation is not provided, create a minimal one
        if attestation is None:
            import hashlib
            import json
            import time
            
            # Generate a unique simulation ID
            sim_id = f"sim_{rev_range.replace('..', '_').replace('/', '_')}"
            
            # Create a minimal attestation
            attestation = {
                "sim_id": sim_id,
                "rev_range": rev_range,
                "scenario": scenario,
                "severity": severity,
                "risk_score": risk_score,
                "manifest_hash": "",
                "commit_target": rev_range.split("..")[-1] if ".." in rev_range else rev_range,
                "diff_hash": hashlib.sha256(json.dumps(diff_data or {}, sort_keys=True).encode()).hexdigest(),
                "explanation": explanation,
                "timestamp": int(time.time()),
            }
        
        # Store the simulation in memory
        sim_node = _store_simulation_in_memory(
            db_path=db_path,
            attestation=attestation,
            metrics=metrics,
            affected_services=affected_services,
            diff_data=diff_data,
        )
        
        logger.info(f"Stored simulation in memory: {attestation.get('sim_id', 'unknown')}")
        return sim_node
    except Exception as e:
        logger.error(f"Error storing simulation in memory: {e}")
        return None


def get_relevant_simulations(
    affected_services: List[str],
    scenario: str,
    severity: int,
    limit: int = 3,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get simulations relevant to current changes.
    
    Args:
        affected_services: List of services affected by the changes
        scenario: The fault scenario being simulated
        severity: The severity level of the simulation (0-100)
        limit: Maximum number of simulations to return
        db_path: Path to the knowledge graph database (optional)
        
    Returns:
        A list of relevant simulations as dictionaries
    """
    try:
        # Get the database path
        if db_path is None:
            arc_dir = ensure_arc_dir()
            db_path = str(arc_dir / "graph.db")
        
        # Retrieve relevant simulations
        return retrieve_relevant_simulations(
            db_path=db_path,
            affected_services=affected_services,
            scenario=scenario,
            severity=severity,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error retrieving relevant simulations: {e}")
        return []


def enhance_explanation(
    explanation: str,
    affected_services: List[str],
    scenario: str,
    severity: int,
    risk_score: int,
    db_path: Optional[str] = None,
) -> str:
    """Enhance explanation with historical context.
    
    Args:
        explanation: Original explanation
        affected_services: List of services affected by the changes
        scenario: The fault scenario being simulated
        severity: The severity level of the simulation (0-100)
        risk_score: Calculated risk score (0-100)
        db_path: Path to the knowledge graph database (optional)
        
    Returns:
        Enhanced explanation with historical context
    """
    try:
        # Get the database path
        if db_path is None:
            arc_dir = ensure_arc_dir()
            db_path = str(arc_dir / "graph.db")
        
        # Enhance the explanation
        return enhance_explanation_with_memory(
            db_path=db_path,
            explanation=explanation,
            affected_services=affected_services,
            scenario=scenario,
            severity=severity,
            risk_score=risk_score,
        )
    except Exception as e:
        logger.error(f"Error enhancing explanation: {e}")
        return explanation
