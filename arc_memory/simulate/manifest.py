"""Simulation manifest generation for Arc Memory.

This module provides functionality for generating simulation manifests
that describe the parameters and targets for fault injection experiments.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def list_available_scenarios() -> List[Dict[str, Any]]:
    """List available simulation scenarios.
    
    Returns:
        List of scenario dictionaries with id, name, and description
    """
    return [
        {
            "id": "network_latency",
            "name": "Network Latency",
            "description": "Introduces latency in network communication between services"
        },
        {
            "id": "network_loss",
            "name": "Network Packet Loss",
            "description": "Simulates packet loss in network communication"
        },
        {
            "id": "cpu_stress",
            "name": "CPU Stress",
            "description": "Introduces CPU stress on target services"
        },
        {
            "id": "memory_stress",
            "name": "Memory Stress",
            "description": "Introduces memory pressure on target services"
        },
        {
            "id": "disk_stress",
            "name": "Disk I/O Stress",
            "description": "Introduces disk I/O pressure on target services"
        },
        {
            "id": "pod_failure",
            "name": "Pod Failure",
            "description": "Simulates pod failures for target services"
        }
    ]


def generate_simulation_manifest(
    causal_graph: Dict[str, Any],
    affected_files: List[str],
    scenario: str = "network_latency",
    severity: int = 50,
    target_services: Optional[List[str]] = None,
    output_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Generate a simulation manifest for fault injection.
    
    Args:
        causal_graph: Causal graph from the knowledge graph
        affected_files: List of affected file paths
        scenario: Fault scenario ID (default: "network_latency")
        severity: Severity level (0-100) (default: 50)
        target_services: List of target service names (optional)
        output_path: Path to save the manifest (optional)
        
    Returns:
        Dictionary containing the manifest
        
    Raises:
        ValueError: If the scenario is invalid
    """
    logger.info(f"Generating simulation manifest for scenario: {scenario}")
    
    # Validate the scenario
    available_scenarios = [s["id"] for s in list_available_scenarios()]
    if scenario not in available_scenarios:
        raise ValueError(f"Invalid scenario: {scenario}. Available scenarios: {', '.join(available_scenarios)}")
    
    # Determine target services if not provided
    if target_services is None:
        target_services = []
        
        # Use the causal graph to identify services affected by the files
        file_to_services = causal_graph.get("file_to_services", {})
        for file_path in affected_files:
            services = file_to_services.get(file_path, [])
            for service in services:
                if service not in target_services:
                    target_services.append(service)
    
    # Create the manifest
    manifest = {
        "scenario": scenario,
        "severity": severity,
        "affected_services": target_services,
        "affected_files": affected_files,
        "causal_graph": causal_graph
    }
    
    # Save the manifest if output_path is provided
    if output_path:
        # Ensure the directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine the format based on the file extension
        if output_path.suffix.lower() == ".yaml" or output_path.suffix.lower() == ".yml":
            with open(output_path, "w") as f:
                yaml.dump(manifest, f, default_flow_style=False)
        else:
            with open(output_path, "w") as f:
                json.dump(manifest, f, indent=2)
        
        logger.info(f"Saved simulation manifest to {output_path}")
    
    return manifest
