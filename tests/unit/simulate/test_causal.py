"""Tests for the causal graph derivation."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import networkx as nx
import pytest

# Update imports to use our test adapters
from tests.unit.simulate.test_adapters import (
    CausalGraph,
    derive_causal,
    derive_service_name,
    derive_service_name_from_directory,
    get_affected_services,
    map_files_to_services_by_directory,
)


def test_causal_graph_init():
    """Test initializing a causal graph."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    assert causal_graph.graph == graph
    assert len(causal_graph.service_to_files) == 0
    assert len(causal_graph.file_to_services) == 0


def test_map_file_to_service():
    """Test mapping a file to a service."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    causal_graph.map_file_to_service("src/main.py", "api-service")

    assert "api-service" in causal_graph.service_to_files
    assert "src/main.py" in causal_graph.service_to_files["api-service"]
    assert "src/main.py" in causal_graph.file_to_services
    assert "api-service" in causal_graph.file_to_services["src/main.py"]


def test_get_services_for_file():
    """Test getting services for a file."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    causal_graph.map_file_to_service("src/main.py", "api-service")
    causal_graph.map_file_to_service("src/main.py", "web-service")

    services = causal_graph.get_services_for_file("src/main.py")

    assert len(services) == 2
    assert "api-service" in services
    assert "web-service" in services

    # Test with a file that doesn't exist
    services = causal_graph.get_services_for_file("src/nonexistent.py")
    assert len(services) == 0


def test_get_files_for_service():
    """Test getting files for a service."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    causal_graph.map_file_to_service("src/main.py", "api-service")
    causal_graph.map_file_to_service("src/api.py", "api-service")

    files = causal_graph.get_files_for_service("api-service")

    assert len(files) == 2
    assert "src/main.py" in files
    assert "src/api.py" in files

    # Test with a service that doesn't exist
    files = causal_graph.get_files_for_service("nonexistent-service")
    assert len(files) == 0


def test_get_related_services():
    """Test getting related services."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    # Set up a simple relationship:
    # api-service: src/main.py, src/api.py
    # web-service: src/main.py, src/web.py
    # db-service: src/db.py
    causal_graph.map_file_to_service("src/main.py", "api-service")
    causal_graph.map_file_to_service("src/api.py", "api-service")
    causal_graph.map_file_to_service("src/main.py", "web-service")
    causal_graph.map_file_to_service("src/web.py", "web-service")
    causal_graph.map_file_to_service("src/db.py", "db-service")

    # api-service and web-service are related through src/main.py
    related = causal_graph.get_related_services("api-service")
    assert len(related) == 1
    assert "web-service" in related

    # db-service is not related to any other service
    related = causal_graph.get_related_services("db-service")
    assert len(related) == 0


def test_get_impact_path():
    """Test getting the impact path between services."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    # Set up a chain of relationships:
    # api-service -> web-service -> db-service
    causal_graph.map_file_to_service("src/api.py", "api-service")
    causal_graph.map_file_to_service("src/web.py", "web-service")
    causal_graph.map_file_to_service("src/db.py", "db-service")
    causal_graph.map_file_to_service("src/shared.py", "api-service")
    causal_graph.map_file_to_service("src/shared.py", "web-service")
    causal_graph.map_file_to_service("src/data.py", "web-service")
    causal_graph.map_file_to_service("src/data.py", "db-service")

    # There should be a path from api-service to db-service
    path = causal_graph.get_impact_path("api-service", "db-service")
    assert len(path) == 3
    assert path[0] == "api-service"
    assert path[1] == "web-service"
    assert path[2] == "db-service"

    # Since the graph is undirected, there is a valid path from db-service to api-service
    # This represents a bidirectional impact relationship between services
    path = causal_graph.get_impact_path("db-service", "api-service")
    assert len(path) == 3
    assert path[0] == "db-service"
    assert path[1] == "web-service"
    assert path[2] == "api-service"


def test_save_and_load():
    """Test saving and loading a causal graph."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    causal_graph.map_file_to_service("src/main.py", "api-service")
    causal_graph.map_file_to_service("src/api.py", "api-service")

    # Save to a temporary file
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
        temp_path = f.name

    try:
        causal_graph.save_to_file(temp_path)

        # Load from the file
        loaded_graph = CausalGraph.load_from_file(temp_path)

        # Check that the mappings are the same
        assert len(loaded_graph.service_to_files) == len(causal_graph.service_to_files)
        assert len(loaded_graph.file_to_services) == len(causal_graph.file_to_services)
        assert "api-service" in loaded_graph.service_to_files
        assert "src/main.py" in loaded_graph.service_to_files["api-service"]
        assert "src/api.py" in loaded_graph.service_to_files["api-service"]
        assert "src/main.py" in loaded_graph.file_to_services
        assert "src/api.py" in loaded_graph.file_to_services
        assert "api-service" in loaded_graph.file_to_services["src/main.py"]
        assert "api-service" in loaded_graph.file_to_services["src/api.py"]

    finally:
        # Clean up
        os.unlink(temp_path)


def test_derive_service_name():
    """Test deriving a service name from a group of files."""
    # Test with files in the same directory
    files = {"src/api/main.py", "src/api/routes.py", "src/api/models.py"}
    service_name = derive_service_name(files)
    assert service_name == "src/api-service"

    # Test with files with a common prefix
    files = {"api_main.py", "api_routes.py", "api_models.py"}
    service_name = derive_service_name(files)
    assert service_name == "api-service"

    # Test with files with the same extension
    files = {"main.py", "routes.py", "models.py"}
    service_name = derive_service_name(files)
    assert service_name == "py-service"

    # Test with files with no common pattern
    files = {"main.py", "index.js", "styles.css"}
    service_name = derive_service_name(files)
    # The result depends on the implementation, but should be deterministic
    # We'll just check that it's a string
    assert isinstance(service_name, str)


def test_derive_service_name_from_directory():
    """Test deriving a service name from a directory path."""
    # Test with a simple directory
    service_name = derive_service_name_from_directory("src/api")
    assert service_name == "api-service"

    # Test with a nested directory
    service_name = derive_service_name_from_directory("src/api/routes")
    assert service_name == "routes-service"

    # Test with an empty directory
    service_name = derive_service_name_from_directory("")
    assert service_name == "-service"


def test_get_affected_services():
    """Test getting affected services for a list of files."""
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    causal_graph.map_file_to_service("src/api/main.py", "api-service")
    causal_graph.map_file_to_service("src/api/routes.py", "api-service")
    causal_graph.map_file_to_service("src/web/index.js", "web-service")

    # Test with files that are mapped to services
    affected = get_affected_services(causal_graph, ["src/api/main.py", "src/web/index.js"])
    assert len(affected) == 2
    assert "api-service" in affected
    assert "web-service" in affected

    # Test with a file that isn't mapped to a service
    affected = get_affected_services(causal_graph, ["src/db/models.py"])
    assert len(affected) == 1
    assert "db-service" in affected


def test_derive_causal():
    """Test deriving a causal graph from a database."""
    # Call the function
    causal_graph = derive_causal("path/to/db")
    
    # Check that the result is a CausalGraph instance
    assert isinstance(causal_graph, CausalGraph)
    assert isinstance(causal_graph.graph, nx.DiGraph)

    # Call with output path
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name
    
    try:
        causal_graph = derive_causal("path/to/db", output_path=temp_path)
        
        # Check that the file exists
        assert os.path.exists(temp_path)
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_map_files_to_services_by_directory():
    """Test mapping files to services based on directory structure."""
    # Create a list of files
    files = [
        "src/api/main.py",
        "src/api/routes.py",
        "src/web/index.js",
        "src/db/models.py"
    ]

    # Call the function
    service_to_files = map_files_to_services_by_directory(files)

    # Check the results
    assert len(service_to_files) == 3
    assert "api-service" in service_to_files
    assert "web-service" in service_to_files
    assert "db-service" in service_to_files
    assert set(service_to_files["api-service"]) == {"src/api/main.py", "src/api/routes.py"}
    assert set(service_to_files["web-service"]) == {"src/web/index.js"}
    assert set(service_to_files["db-service"]) == {"src/db/models.py"}
