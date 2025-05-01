"""Simulation manifest generation for Arc Memory.

This module provides functions for generating simulation manifests for Chaos Mesh
experiments based on the affected services identified by the causal graph.
"""

import hashlib
import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Union

import yaml

from arc_memory.logging_conf import get_logger
from arc_memory.simulate.causal import CausalGraph, get_affected_services

logger = get_logger(__name__)


class FaultScenario(str, Enum):
    """Types of fault scenarios supported by the simulation."""

    NETWORK_LATENCY = "network_latency"
    CPU_STRESS = "cpu_stress"
    MEMORY_PRESSURE = "memory_pressure"
    DISK_IO = "disk_io"


class ManifestGenerator:
    """Generator for Chaos Mesh experiment manifests."""

    def __init__(
        self,
        causal_graph: CausalGraph,
        scenario: str = FaultScenario.NETWORK_LATENCY,
        severity: int = 50,
    ):
        """Initialize the manifest generator.

        Args:
            causal_graph: The causal graph derived from the TKG
            scenario: The fault scenario to simulate
            severity: The severity level (0-100) of the fault
        """
        self.causal_graph = causal_graph
        self.scenario = self._validate_scenario(scenario)
        self.severity = self._validate_severity(severity)

    def _validate_scenario(self, scenario: str) -> str:
        """Validate and normalize the scenario name.

        Args:
            scenario: The scenario name to validate

        Returns:
            The normalized scenario name

        Raises:
            ValueError: If the scenario is not supported
        """
        try:
            return FaultScenario(scenario.lower())
        except ValueError:
            valid_scenarios = ", ".join([s.value for s in FaultScenario])
            raise ValueError(
                f"Unsupported scenario: {scenario}. "
                f"Valid scenarios are: {valid_scenarios}"
            )

    def _validate_severity(self, severity: int) -> int:
        """Validate the severity level.

        Args:
            severity: The severity level to validate

        Returns:
            The validated severity level

        Raises:
            ValueError: If the severity is not in the range 0-100
        """
        if not 0 <= severity <= 100:
            raise ValueError(
                f"Severity must be in the range 0-100, got {severity}"
            )
        return severity

    def generate_manifest(
        self, affected_files: List[str], target_services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate a simulation manifest for the affected services.

        Args:
            affected_files: List of files affected by the changes
            target_services: Optional list of target services to simulate
                If not provided, will be derived from affected_files

        Returns:
            A dictionary containing the simulation manifest
        """
        # Identify affected services if not provided
        if target_services is None:
            target_services = get_affected_services(self.causal_graph, affected_files)

        if not target_services:
            logger.warning("No target services identified for simulation")
            return self._generate_empty_manifest()

        # Generate the appropriate manifest based on the scenario
        if self.scenario == FaultScenario.NETWORK_LATENCY:
            return self._generate_network_latency_manifest(target_services)
        elif self.scenario == FaultScenario.CPU_STRESS:
            return self._generate_cpu_stress_manifest(target_services)
        elif self.scenario == FaultScenario.MEMORY_PRESSURE:
            return self._generate_memory_pressure_manifest(target_services)
        elif self.scenario == FaultScenario.DISK_IO:
            return self._generate_disk_io_manifest(target_services)
        else:
            # This should never happen due to validation in __init__
            logger.error(f"Unsupported scenario: {self.scenario}")
            return self._generate_empty_manifest()

    def _generate_empty_manifest(self) -> Dict[str, Any]:
        """Generate an empty manifest when no services are affected.

        Returns:
            An empty manifest dictionary
        """
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "Schedule",
            "metadata": {
                "name": "empty-schedule",
                "namespace": "default",
                "annotations": {}
            },
            "spec": {
                "schedule": "0 * * * *",
                "historyLimit": 1,
                "concurrencyPolicy": "Forbid",
                "type": "NetworkChaos",
                "networkChaos": {
                    "action": "delay",
                    "mode": "one",
                    "selector": {
                        "namespaces": ["default"],
                        "labelSelectors": {"app": "nonexistent"}
                    },
                    "delay": {
                        "latency": "0ms",
                        "correlation": "0",
                        "jitter": "0ms"
                    }
                }
            }
        }

    def _generate_network_latency_manifest(self, target_services: List[str]) -> Dict[str, Any]:
        """Generate a network latency manifest for the target services.

        Args:
            target_services: List of services to target

        Returns:
            A dictionary containing the network latency manifest
        """
        # Calculate latency based on severity
        # Severity 0 = 0ms, Severity 100 = 1000ms
        latency_ms = int(self.severity * 10)

        # Calculate jitter based on severity (10% of latency)
        jitter_ms = int(latency_ms * 0.1)

        # Calculate correlation based on severity
        # Higher severity = higher correlation (more consistent latency)
        correlation = self.severity / 100

        # Generate a unique name for the experiment
        experiment_name = f"network-latency-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create the manifest
        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "NetworkChaos",
            "metadata": {
                "name": experiment_name,
                "namespace": "default"
            },
            "spec": {
                "action": "delay",
                "mode": "all",
                "selector": {
                    "namespaces": ["default"],
                    "labelSelectors": {
                        "service": "|".join(target_services)
                    }
                },
                "delay": {
                    "latency": f"{latency_ms}ms",
                    "correlation": str(correlation),
                    "jitter": f"{jitter_ms}ms"
                },
                "duration": "5m"
            }
        }

        return manifest

    def _generate_cpu_stress_manifest(self, target_services: List[str]) -> Dict[str, Any]:
        """Generate a CPU stress manifest for the target services.

        Args:
            target_services: List of services to target

        Returns:
            A dictionary containing the CPU stress manifest
        """
        # Calculate CPU load based on severity
        # Severity 0 = 0% CPU, Severity 100 = 100% CPU
        cpu_load = self.severity

        # Generate a unique name for the experiment
        experiment_name = f"cpu-stress-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create the manifest
        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "StressChaos",
            "metadata": {
                "name": experiment_name,
                "namespace": "default"
            },
            "spec": {
                "mode": "all",
                "selector": {
                    "namespaces": ["default"],
                    "labelSelectors": {
                        "service": "|".join(target_services)
                    }
                },
                "stressors": {
                    "cpu": {
                        "workers": 1,
                        "load": cpu_load
                    }
                },
                "duration": "5m"
            }
        }

        return manifest

    def _generate_memory_pressure_manifest(self, target_services: List[str]) -> Dict[str, Any]:
        """Generate a memory pressure manifest for the target services.

        Args:
            target_services: List of services to target

        Returns:
            A dictionary containing the memory pressure manifest
        """
        # Calculate memory consumption based on severity
        # Severity 0 = 0MB, Severity 100 = 1024MB (1GB)
        memory_mb = int(self.severity * 10.24)

        # Generate a unique name for the experiment
        experiment_name = f"memory-pressure-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create the manifest
        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "StressChaos",
            "metadata": {
                "name": experiment_name,
                "namespace": "default"
            },
            "spec": {
                "mode": "all",
                "selector": {
                    "namespaces": ["default"],
                    "labelSelectors": {
                        "service": "|".join(target_services)
                    }
                },
                "stressors": {
                    "memory": {
                        "workers": 1,
                        "size": f"{memory_mb}MB"
                    }
                },
                "duration": "5m"
            }
        }

        return manifest

    def _generate_disk_io_manifest(self, target_services: List[str]) -> Dict[str, Any]:
        """Generate a disk I/O manifest for the target services.

        Args:
            target_services: List of services to target

        Returns:
            A dictionary containing the disk I/O manifest
        """
        # Calculate I/O workers based on severity
        # Severity 0 = 1 worker, Severity 100 = 4 workers
        workers = 1 + int(self.severity / 33)

        # Generate a unique name for the experiment
        experiment_name = f"disk-io-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create the manifest
        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "IOChaos",
            "metadata": {
                "name": experiment_name,
                "namespace": "default"
            },
            "spec": {
                "action": "latency",
                "mode": "all",
                "selector": {
                    "namespaces": ["default"],
                    "labelSelectors": {
                        "service": "|".join(target_services)
                    }
                },
                "volumePath": "/data",
                "path": "",
                "delay": f"{self.severity}ms",
                "percent": self.severity,
                "duration": "5m"
            }
        }

        return manifest

    def save_manifest(self, manifest: Dict[str, Any], output_path: Union[str, Path]) -> None:
        """Save the manifest to a YAML file.

        Args:
            manifest: The manifest to save
            output_path: The path to save the manifest to
        """
        output_path = Path(output_path)

        # Create parent directories if they don't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save the manifest as YAML
        with open(output_path, 'w') as f:
            yaml.dump(manifest, f, default_flow_style=False)

        logger.info(f"Saved manifest to {output_path}")

    def calculate_manifest_hash(self, manifest: Dict[str, Any]) -> str:
        """Calculate a hash of the manifest for attestation.

        Args:
            manifest: The manifest to hash

        Returns:
            A hash of the manifest
        """
        # Convert the manifest to a JSON string
        manifest_json = json.dumps(manifest, sort_keys=True)

        # Calculate the SHA-256 hash
        hash_obj = hashlib.sha256(manifest_json.encode('utf-8'))

        return hash_obj.hexdigest()


def list_available_scenarios() -> List[Dict[str, str]]:
    """List all available fault scenarios with descriptions.

    Returns:
        A list of dictionaries containing scenario IDs and descriptions
    """
    return [
        {
            "id": "network_latency",
            "description": "Inject network latency between services"
        },
        {
            "id": "cpu_stress",
            "description": "Simulate CPU pressure on services"
        },
        {
            "id": "memory_pressure",
            "description": "Simulate memory pressure on services"
        },
        {
            "id": "disk_io",
            "description": "Simulate disk I/O pressure on services"
        }
    ]


def generate_simulation_manifest(
    causal_graph: CausalGraph,
    affected_files: List[str],
    scenario: str = FaultScenario.NETWORK_LATENCY,
    severity: int = 50,
    target_services: Optional[List[str]] = None,
    output_path: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """Generate a simulation manifest for the affected services.

    Args:
        causal_graph: The causal graph derived from the TKG
        affected_files: List of files affected by the changes
        scenario: The fault scenario to simulate
        severity: The severity level (0-100) of the fault
        target_services: Optional list of target services to simulate
            If not provided, will be derived from affected_files
        output_path: Optional path to save the manifest to

    Returns:
        A dictionary containing the simulation manifest
    """
    # Create the manifest generator
    generator = ManifestGenerator(causal_graph, scenario, severity)

    # Generate the manifest
    manifest = generator.generate_manifest(affected_files, target_services)

    # Save the manifest if an output path is provided
    if output_path:
        generator.save_manifest(manifest, output_path)

    # Calculate the manifest hash
    manifest_hash = generator.calculate_manifest_hash(manifest)

    # Ensure the metadata field exists
    if "metadata" not in manifest:
        manifest["metadata"] = {}

    # Ensure the annotations field exists
    if "annotations" not in manifest["metadata"]:
        manifest["metadata"]["annotations"] = {}

    # Add the hash to the manifest
    manifest["metadata"]["annotations"]["arc-memory.io/manifest-hash"] = manifest_hash

    return manifest
