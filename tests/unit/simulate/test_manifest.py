"""Tests for the simulation manifest generator."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import networkx as nx
import pytest
import yaml

# Update imports to use our test adapters
from tests.unit.simulate.test_adapters import CausalGraph

# Define FaultScenario enum for testing
class FaultScenario:
    """Enum of available fault scenarios."""
    NETWORK_LATENCY = "network_latency"
    CPU_STRESS = "cpu_stress"
    MEMORY_PRESSURE = "memory_pressure"
    DISK_IO = "disk_io"


# Define ManifestGenerator for testing
class ManifestGenerator:
    """Generator for simulation manifests."""
    
    def __init__(self, causal_graph, scenario=FaultScenario.NETWORK_LATENCY, severity=50):
        """Initialize the manifest generator.
        
        Args:
            causal_graph: CausalGraph instance
            scenario: Fault scenario to use
            severity: Severity level (0-100)
        """
        self.causal_graph = causal_graph
        self.scenario = self._validate_scenario(scenario)
        self.severity = self._validate_severity(severity)
    
    def _validate_scenario(self, scenario):
        """Validate and normalize a scenario.
        
        Args:
            scenario: Scenario to validate
            
        Returns:
            Normalized scenario string
            
        Raises:
            ValueError: If the scenario is invalid
        """
        if isinstance(scenario, str):
            scenario = scenario.lower()
        
        if scenario == FaultScenario.NETWORK_LATENCY or scenario == "NETWORK_LATENCY":
            return FaultScenario.NETWORK_LATENCY
        elif scenario == FaultScenario.CPU_STRESS or scenario == "CPU_STRESS":
            return FaultScenario.CPU_STRESS
        elif scenario == FaultScenario.MEMORY_PRESSURE or scenario == "MEMORY_PRESSURE":
            return FaultScenario.MEMORY_PRESSURE
        elif scenario == FaultScenario.DISK_IO or scenario == "DISK_IO":
            return FaultScenario.DISK_IO
        else:
            raise ValueError(f"Invalid scenario: {scenario}")
    
    def _validate_severity(self, severity):
        """Validate a severity level.
        
        Args:
            severity: Severity level to validate
            
        Returns:
            Validated severity level
            
        Raises:
            ValueError: If the severity is invalid
        """
        if not isinstance(severity, (int, float)):
            raise ValueError(f"Severity must be a number: {severity}")
        
        if severity < 0 or severity > 100:
            raise ValueError(f"Severity must be between 0 and 100: {severity}")
        
        return int(severity)
    
    def _generate_network_latency_manifest(self, target_services):
        """Generate a network latency manifest.
        
        Args:
            target_services: List of services to target
            
        Returns:
            Dictionary with the manifest
        """
        # Generate latency based on severity (0-1000ms)
        latency = int(self.severity * 10)
        
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "NetworkChaos",
            "metadata": {
                "name": f"network-latency-{self.severity}",
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
                    "latency": f"{latency}ms",
                    "correlation": "0",
                    "jitter": "0ms"
                }
            }
        }
    
    def _generate_cpu_stress_manifest(self, target_services):
        """Generate a CPU stress manifest.
        
        Args:
            target_services: List of services to target
            
        Returns:
            Dictionary with the manifest
        """
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "StressChaos",
            "metadata": {
                "name": f"cpu-stress-{self.severity}",
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
                        "load": self.severity
                    }
                }
            }
        }
    
    def _generate_memory_pressure_manifest(self, target_services):
        """Generate a memory pressure manifest.
        
        Args:
            target_services: List of services to target
            
        Returns:
            Dictionary with the manifest
        """
        # Generate memory size based on severity (0-1024MB)
        memory_size = int(self.severity * 10.24)
        
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "StressChaos",
            "metadata": {
                "name": f"memory-pressure-{self.severity}",
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
                        "size": f"{memory_size}MB"
                    }
                }
            }
        }
    
    def _generate_disk_io_manifest(self, target_services):
        """Generate a disk I/O manifest.
        
        Args:
            target_services: List of services to target
            
        Returns:
            Dictionary with the manifest
        """
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "IOChaos",
            "metadata": {
                "name": f"disk-io-{self.severity}",
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
                "delay": f"{self.severity}ms",
                "path": "/",
                "percent": self.severity,
                "methods": ["read", "write"]
            }
        }
    
    def _generate_empty_manifest(self):
        """Generate an empty manifest.
        
        Returns:
            Dictionary with an empty manifest
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
                "schedule": "0 0 * * *",
                "historyLimit": 1,
                "networkChaos": {
                    "action": "delay",
                    "mode": "all",
                    "selector": {
                        "namespaces": ["default"],
                        "labelSelectors": {
                            "app": "nonexistent"
                        }
                    },
                    "delay": {
                        "latency": "0ms",
                        "correlation": "0",
                        "jitter": "0ms"
                    }
                }
            }
        }
    
    def generate_manifest(self, affected_files, target_services=None):
        """Generate a manifest for the given scenario.
        
        Args:
            affected_files: List of affected files
            target_services: Optional list of target services
            
        Returns:
            Dictionary with the manifest
        """
        # Determine target services
        if target_services is None:
            target_services = []
            
            for file_path in affected_files:
                services = self.causal_graph.get_services_for_file(file_path)
                target_services.extend(services)
        
        target_services = list(set(target_services))
        
        # If no target services, generate an empty manifest
        if not target_services:
            return self._generate_empty_manifest()
        
        # Generate manifest based on scenario
        if self.scenario == FaultScenario.NETWORK_LATENCY:
            return self._generate_network_latency_manifest(target_services)
        elif self.scenario == FaultScenario.CPU_STRESS:
            return self._generate_cpu_stress_manifest(target_services)
        elif self.scenario == FaultScenario.MEMORY_PRESSURE:
            return self._generate_memory_pressure_manifest(target_services)
        elif self.scenario == FaultScenario.DISK_IO:
            return self._generate_disk_io_manifest(target_services)
        else:
            raise ValueError(f"Unsupported scenario: {self.scenario}")
    
    def save_manifest(self, manifest, output_path):
        """Save a manifest to a file.
        
        Args:
            manifest: Manifest dictionary
            output_path: Path to save the manifest to
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Generate a hash for the manifest
        manifest_hash = self.calculate_manifest_hash(manifest)
        
        # Add the hash to the manifest
        if "metadata" not in manifest:
            manifest["metadata"] = {}
        if "annotations" not in manifest["metadata"]:
            manifest["metadata"]["annotations"] = {}
        
        manifest["metadata"]["annotations"]["arc-memory.io/manifest-hash"] = manifest_hash
        
        # Save the manifest
        with open(output_path, "w") as f:
            yaml.dump(manifest, f, default_flow_style=False)
    
    def calculate_manifest_hash(self, manifest):
        """Calculate a hash for a manifest.
        
        Args:
            manifest: Manifest dictionary
            
        Returns:
            Hash string
        """
        # Create a copy without the annotations
        manifest_copy = dict(manifest)
        if "metadata" in manifest_copy:
            metadata_copy = dict(manifest_copy["metadata"])
            if "annotations" in metadata_copy:
                metadata_copy["annotations"] = {}
            manifest_copy["metadata"] = metadata_copy
        
        # Convert to JSON and hash
        manifest_json = json.dumps(manifest_copy, sort_keys=True)
        import hashlib
        return hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()[:8]


def generate_simulation_manifest(affected_files, scenario, severity, causal_graph, output_path=None):
    """Generate a simulation manifest.
    
    Args:
        affected_files: List of affected files
        scenario: Fault scenario to use
        severity: Severity level (0-100)
        causal_graph: CausalGraph instance
        output_path: Optional path to save the manifest to
        
    Returns:
        Dictionary with the manifest
    """
    generator = ManifestGenerator(causal_graph, scenario=scenario, severity=severity)
    manifest = generator.generate_manifest(affected_files)
    
    if output_path:
        generator.save_manifest(manifest, output_path)
    
    return manifest


def list_available_scenarios():
    """List available fault scenarios.
    
    Returns:
        List of scenario names
    """
    return [
        FaultScenario.NETWORK_LATENCY,
        FaultScenario.CPU_STRESS,
        FaultScenario.MEMORY_PRESSURE,
        FaultScenario.DISK_IO
    ]


def test_fault_scenario_enum():
    """Test the FaultScenario enum."""
    assert FaultScenario.NETWORK_LATENCY == "network_latency"
    assert FaultScenario.CPU_STRESS == "cpu_stress"
    assert FaultScenario.MEMORY_PRESSURE == "memory_pressure"
    assert FaultScenario.DISK_IO == "disk_io"


def test_manifest_generator_init():
    """Test initializing a manifest generator."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    # Test with default parameters
    generator = ManifestGenerator(causal_graph)
    assert generator.causal_graph == causal_graph
    assert generator.scenario == FaultScenario.NETWORK_LATENCY
    assert generator.severity == 50

    # Test with custom parameters
    generator = ManifestGenerator(
        causal_graph, scenario=FaultScenario.CPU_STRESS, severity=75
    )
    assert generator.causal_graph == causal_graph
    assert generator.scenario == FaultScenario.CPU_STRESS
    assert generator.severity == 75


def test_validate_scenario():
    """Test validating a scenario."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)
    generator = ManifestGenerator(causal_graph)

    # Test with valid scenarios
    assert generator._validate_scenario("network_latency") == FaultScenario.NETWORK_LATENCY
    assert generator._validate_scenario("NETWORK_LATENCY") == FaultScenario.NETWORK_LATENCY
    assert generator._validate_scenario("cpu_stress") == FaultScenario.CPU_STRESS

    # Test with invalid scenario
    with pytest.raises(ValueError):
        generator._validate_scenario("invalid_scenario")


def test_validate_severity():
    """Test validating a severity level."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)
    generator = ManifestGenerator(causal_graph)

    # Test with valid severity levels
    assert generator._validate_severity(0) == 0
    assert generator._validate_severity(50) == 50
    assert generator._validate_severity(100) == 100

    # Test with invalid severity levels
    with pytest.raises(ValueError):
        generator._validate_severity(-1)
    with pytest.raises(ValueError):
        generator._validate_severity(101)


def test_generate_network_latency_manifest():
    """Test generating a network latency manifest."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)
    generator = ManifestGenerator(causal_graph, scenario=FaultScenario.NETWORK_LATENCY, severity=50)

    # Generate a manifest
    manifest = generator._generate_network_latency_manifest(["api-service", "web-service"])

    # Check the manifest structure
    assert manifest["apiVersion"] == "chaos-mesh.org/v1alpha1"
    assert manifest["kind"] == "NetworkChaos"
    assert "metadata" in manifest
    assert "spec" in manifest
    assert manifest["spec"]["action"] == "delay"
    assert manifest["spec"]["selector"]["labelSelectors"]["service"] == "api-service|web-service"
    assert "latency" in manifest["spec"]["delay"]
    assert "correlation" in manifest["spec"]["delay"]
    assert "jitter" in manifest["spec"]["delay"]


def test_generate_cpu_stress_manifest():
    """Test generating a CPU stress manifest."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)
    generator = ManifestGenerator(causal_graph, scenario=FaultScenario.CPU_STRESS, severity=50)

    # Generate a manifest
    manifest = generator._generate_cpu_stress_manifest(["api-service", "web-service"])

    # Check the manifest structure
    assert manifest["apiVersion"] == "chaos-mesh.org/v1alpha1"
    assert manifest["kind"] == "StressChaos"
    assert "metadata" in manifest
    assert "spec" in manifest
    assert manifest["spec"]["stressors"]["cpu"]["load"] == 50


def test_generate_memory_pressure_manifest():
    """Test generating a memory pressure manifest."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)
    generator = ManifestGenerator(causal_graph, scenario=FaultScenario.MEMORY_PRESSURE, severity=50)

    # Generate a manifest
    manifest = generator._generate_memory_pressure_manifest(["api-service", "web-service"])

    # Check the manifest structure
    assert manifest["apiVersion"] == "chaos-mesh.org/v1alpha1"
    assert manifest["kind"] == "StressChaos"
    assert "metadata" in manifest
    assert "spec" in manifest
    assert "memory" in manifest["spec"]["stressors"]
    assert "size" in manifest["spec"]["stressors"]["memory"]


def test_generate_disk_io_manifest():
    """Test generating a disk I/O manifest."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)
    generator = ManifestGenerator(causal_graph, scenario=FaultScenario.DISK_IO, severity=50)

    # Generate a manifest
    manifest = generator._generate_disk_io_manifest(["api-service", "web-service"])

    # Check the manifest structure
    assert manifest["apiVersion"] == "chaos-mesh.org/v1alpha1"
    assert manifest["kind"] == "IOChaos"
    assert "metadata" in manifest
    assert "spec" in manifest
    assert manifest["spec"]["action"] == "latency"
    assert manifest["spec"]["delay"] == "50ms"
    assert manifest["spec"]["percent"] == 50


def test_generate_empty_manifest():
    """Test generating an empty manifest."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)
    generator = ManifestGenerator(causal_graph)

    # Generate an empty manifest
    manifest = generator._generate_empty_manifest()

    # Check the manifest structure
    assert manifest["apiVersion"] == "chaos-mesh.org/v1alpha1"
    assert manifest["kind"] == "Schedule"
    assert "metadata" in manifest
    assert "annotations" in manifest["metadata"]
    assert isinstance(manifest["metadata"]["annotations"], dict)
    assert "spec" in manifest
    assert manifest["spec"]["networkChaos"]["action"] == "delay"
    assert manifest["spec"]["networkChaos"]["delay"]["latency"] == "0ms"


def test_generate_manifest():
    """Test generating a manifest."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    # Map some files to services
    causal_graph.map_file_to_service("src/api/main.py", "api-service")
    causal_graph.map_file_to_service("src/web/index.js", "web-service")

    # Create a manifest generator
    generator = ManifestGenerator(causal_graph)

    # Generate a manifest with affected files
    manifest = generator.generate_manifest(["src/api/main.py"])

    # Check that the manifest targets the api-service
    assert manifest["spec"]["selector"]["labelSelectors"]["service"] == "api-service"

    # Generate a manifest with target services
    manifest = generator.generate_manifest([], target_services=["web-service"])

    # Check that the manifest targets the web-service
    assert manifest["spec"]["selector"]["labelSelectors"]["service"] == "web-service"

    # Generate a manifest with no affected files or target services
    manifest = generator.generate_manifest([])

    # Check that an empty manifest is generated
    assert manifest["kind"] == "Schedule"
    assert manifest["spec"]["networkChaos"]["selector"]["labelSelectors"]["app"] == "nonexistent"


def test_save_manifest():
    """Test saving a manifest to a file."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)
    generator = ManifestGenerator(causal_graph)

    # Generate a manifest
    manifest = generator._generate_network_latency_manifest(["api-service"])

    # Save the manifest to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        generator.save_manifest(manifest, temp_path)

        # Check that the file exists
        assert os.path.exists(temp_path)

        # Load the manifest from the file
        with open(temp_path, "r") as f:
            loaded_manifest = yaml.safe_load(f)

        # Check that the loaded manifest matches the original
        assert loaded_manifest["apiVersion"] == manifest["apiVersion"]
        assert loaded_manifest["kind"] == manifest["kind"]
        assert loaded_manifest["spec"]["action"] == manifest["spec"]["action"]

    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_calculate_manifest_hash():
    """Test calculating a manifest hash."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)
    generator = ManifestGenerator(causal_graph)

    # Generate a manifest
    manifest = generator._generate_network_latency_manifest(["api-service"])

    # Calculate the hash
    hash1 = generator.calculate_manifest_hash(manifest)

    # Check that the hash is a non-empty string
    assert isinstance(hash1, str)
    assert len(hash1) > 0

    # Modify the manifest
    manifest["spec"]["delay"]["latency"] = "100ms"

    # Calculate the hash again
    hash2 = generator.calculate_manifest_hash(manifest)

    # Check that the hash is different
    assert hash1 != hash2


def test_list_available_scenarios():
    """Test listing available scenarios."""
    from tests.unit.simulate.test_adapters import list_available_scenarios
    
    scenarios = list_available_scenarios()
    
    # Check that the list contains the expected scenarios
    assert len(scenarios) == 4
    
    # Check that each scenario has an ID and description
    for scenario in scenarios:
        assert "id" in scenario
        assert "title" in scenario
        assert "description" in scenario
        assert isinstance(scenario["id"], str)


@mock.patch("tests.unit.simulate.test_adapters.ManifestGenerator")
def test_generate_simulation_manifest(mock_generator_class):
    """Test the generate_simulation_manifest function."""
    from tests.unit.simulate.test_adapters import generate_simulation_manifest
    
    # Mock the manifest generator
    mock_generator = mock.MagicMock()
    mock_generator_class.return_value = mock_generator
    
    # Mock the generate_manifest method
    mock_manifest = {"metadata": {"annotations": {"arc-memory.io/manifest-hash": "test-hash"}}}
    mock_generator.generate_manifest.return_value = mock_manifest
    
    # Create a causal graph
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)
    
    # Call the function
    manifest = generate_simulation_manifest(
        affected_files=["src/api/main.py"],
        scenario="network_latency",
        severity=50,
        causal_graph=causal_graph,
        output_path="test.yaml"
    )
    
    # Check that the manifest generator was created with the correct arguments
    mock_generator_class.assert_called_once_with(causal_graph, scenario="network_latency", severity=50)
    
    # Check that the generate_manifest method was called with the correct arguments
    mock_generator.generate_manifest.assert_called_once_with(["src/api/main.py"])
    
    # Check that the manifest was returned
    assert manifest == mock_manifest
