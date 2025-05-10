"""Tests for the simulation manifest generator."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import networkx as nx
import pytest
import yaml

from arc_memory.simulate.causal import CausalGraph
from arc_memory.simulate.manifest import (
    FaultScenario,
    ManifestGenerator,
    generate_simulation_manifest,
    list_available_scenarios,
)


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
    scenarios = list_available_scenarios()

    # Check that the list contains the expected scenarios
    assert len(scenarios) == 4

    # Check that each scenario has an ID and description
    for scenario in scenarios:
        assert "id" in scenario
        assert "description" in scenario


@mock.patch("arc_memory.simulate.manifest.ManifestGenerator")
def test_generate_simulation_manifest(mock_generator_class):
    """Test the generate_simulation_manifest function."""
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
        causal_graph=causal_graph,
        affected_files=["src/api/main.py"],
        scenario="network_latency",
        severity=50,
        target_services=["api-service"],
        output_path="test.yaml"
    )

    # Check that the manifest generator was created with the correct parameters
    mock_generator_class.assert_called_once_with(causal_graph, "network_latency", 50)

    # Check that generate_manifest was called with the correct parameters
    mock_generator.generate_manifest.assert_called_once_with(
        ["src/api/main.py"], ["api-service"]
    )

    # Check that save_manifest was called with the correct parameters
    mock_generator.save_manifest.assert_called_once_with(mock_manifest, "test.yaml")

    # Check that the manifest was returned
    assert manifest == mock_manifest
