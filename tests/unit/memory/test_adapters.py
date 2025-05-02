"""Test adapters for memory integration tests.

This module provides adapter functions to bridge the gap between
the old memory integration tests and the new implementation with Smol Agents.
"""

import json
from unittest import mock
import sys
from typing import Dict, List, Any, Optional, Union

from arc_memory.schema.models import (
    NodeType,
    SimulationNode
)


def retrieve_relevant_simulations(
    db_path: str,
    affected_services: list,
    scenario: str = None,
    severity: int = None,
    severity_range: tuple = None,
    limit: int = 5,
) -> list:
    """Retrieve relevant simulations from memory.
    
    Args:
        db_path: Path to the knowledge graph database
        affected_services: List of affected service names
        scenario: Optional fault scenario
        severity: Optional severity level
        severity_range: Optional tuple of (min, max) severity
        limit: Maximum number of simulations to return
        
    Returns:
        List of relevant simulations
    """
    # For testing purposes, return a mock list of simulations
    return [
        {
            "sim_id": "sim_test_1",
            "scenario": scenario or "network_latency",
            "severity": severity or 50,
            "risk_score": 25,
            "affected_services": affected_services[:1],
            "explanation": "Test explanation 1",
            "timestamp": "2023-01-01T12:00:00Z"
        },
        {
            "sim_id": "sim_test_2",
            "scenario": scenario or "network_latency",
            "severity": (severity + 10) if severity else 60,
            "risk_score": 30,
            "affected_services": affected_services,
            "explanation": "Test explanation 2",
            "timestamp": "2023-01-02T12:00:00Z"
        }
    ]


def enhance_explanation_with_memory(
    explanation: str,
    affected_services: list,
    scenario: str,
    severity: int,
    risk_score: int,
    db_path: str,
) -> str:
    """Enhance explanation with historical context from memory.
    
    Args:
        explanation: Original explanation
        affected_services: List of affected service names
        scenario: Fault scenario
        severity: Severity level
        risk_score: Risk score
        db_path: Path to the knowledge graph database
        
    Returns:
        Enhanced explanation
    """
    # Get relevant simulations
    relevant_sims = retrieve_relevant_simulations(
        db_path=db_path,
        affected_services=affected_services,
        scenario=scenario,
        severity=severity
    )
    
    # If no relevant simulations, return the original explanation
    if not relevant_sims:
        return explanation
    
    # Calculate the average risk score of relevant simulations
    avg_risk = sum(sim["risk_score"] for sim in relevant_sims) / len(relevant_sims)
    
    # Compare the current risk score with the average
    risk_comparison = "higher" if risk_score > avg_risk else "lower"
    
    # Enhance the explanation with historical context
    enhanced = f"{explanation}\n\n## Historical Context\n\n"
    enhanced += f"This change poses a {risk_comparison} risk ({risk_score}) than similar changes in the past (avg. {avg_risk:.1f}).\n\n"
    
    # Add details for each relevant simulation
    for sim in relevant_sims:
        enhanced += f"- Simulation {sim['sim_id']} ({sim['timestamp']}): Risk score {sim['risk_score']}, affected {', '.join(sim['affected_services'])}\n"
    
    return enhanced


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
    # Create a mock simulation node
    sim_node = SimulationNode(
        id=f"simulation:sim_test_1",
        type=NodeType.SIMULATION,
        sim_id="sim_test_1",
        rev_range=rev_range,
        scenario=scenario,
        severity=severity,
        risk_score=risk_score,
        manifest_hash=attestation.get("manifest_hash", "abc123") if attestation else "abc123",
        commit_target=attestation.get("commit_target", "def456") if attestation else "def456",
        diff_hash=attestation.get("diff_hash", "ghi789") if attestation else "ghi789",
        affected_services=affected_services,
    )
    
    return sim_node


def get_relevant_simulations(
    affected_services: List[str],
    scenario: str = "network_latency",
    severity: int = 50,
    limit: int = 5,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get relevant simulations for a set of services.
    
    Args:
        affected_services: List of affected service names
        scenario: Fault scenario ID
        severity: Severity level (0-100)
        limit: Maximum number of simulations to return
        db_path: Path to the knowledge graph database (optional)
        
    Returns:
        List of relevant simulations
    """
    return retrieve_relevant_simulations(
        db_path=db_path or "test.db",
        affected_services=affected_services,
        scenario=scenario,
        severity_range=(max(0, severity - 20), min(100, severity + 20)),
        limit=limit
    )


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
        affected_services: List of affected service names
        scenario: Fault scenario ID
        severity: Severity level (0-100)
        risk_score: Risk score (0-100)
        db_path: Path to the knowledge graph database (optional)
        
    Returns:
        Enhanced explanation
    """
    return enhance_explanation_with_memory(
        explanation=explanation,
        affected_services=affected_services,
        scenario=scenario,
        severity=severity,
        risk_score=risk_score,
        db_path=db_path or "test.db"
    )


# Create mock module for arc_memory.memory.integration
memory_integration_mock = mock.MagicMock()
memory_integration_mock.retrieve_relevant_simulations = retrieve_relevant_simulations
memory_integration_mock.enhance_explanation_with_memory = enhance_explanation_with_memory
memory_integration_mock.store_simulation_in_memory = store_simulation_in_memory

# Install mock in sys.modules
sys.modules['arc_memory.memory.integration'] = memory_integration_mock

# Create mock module for arc_memory.simulate.memory
memory_mock = mock.MagicMock()
memory_mock.store_simulation_in_memory = store_simulation_in_memory
memory_mock.get_relevant_simulations = get_relevant_simulations
memory_mock.enhance_explanation = enhance_explanation

# Install mock in sys.modules
sys.modules['arc_memory.simulate.memory'] = memory_mock 