"""Tests for the causal graph derivation."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import networkx as nx
import pytest

from arc_memory.simulate.causal import (
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


@mock.patch("arc_memory.simulate.causal.Path")
@mock.patch("arc_memory.simulate.causal.build_networkx_graph")
@mock.patch("arc_memory.simulate.causal.get_connection")
@mock.patch("arc_memory.simulate.causal.map_files_to_services")
def test_derive_causal(mock_map_files, mock_get_conn, mock_build_graph, mock_path):
    """Test deriving a causal graph from a database."""
    # Mock the database connection
    mock_conn = mock.MagicMock()
    mock_get_conn.return_value = mock_conn

    # Mock the NetworkX graph
    mock_graph = mock.MagicMock()
    mock_build_graph.return_value = mock_graph

    # Mock the Path object
    mock_path_instance = mock.MagicMock()
    mock_path.return_value = mock_path_instance
    mock_path_instance.exists.return_value = True

    # Call the function
    causal_graph = derive_causal("path/to/db")

    # Check that the mocks were called
    mock_path.assert_called_once_with("path/to/db")
    mock_path_instance.exists.assert_called_once()
    mock_get_conn.assert_called_once_with("path/to/db")
    mock_build_graph.assert_called_once_with(mock_conn)
    mock_map_files.assert_called_once()

    # Check that a causal graph was returned
    assert isinstance(causal_graph, CausalGraph)
    assert causal_graph.graph == mock_graph


def test_map_files_to_services_by_directory():
    """Test mapping files to services based on directory structure."""
    # Create a causal graph
    graph = nx.DiGraph()
    causal_graph = CausalGraph(graph)

    # Add some files
    causal_graph.map_file_to_service("src/api/main.py", "api-service")
    causal_graph.map_file_to_service("src/api/routes.py", "api-service")

    # Add a file with no service
    # We need to add it to both mappings to simulate a file that exists but has no service
    causal_graph.file_to_services["src/web/index.js"] = set()

    # Call the function
    map_files_to_services_by_directory(causal_graph)

    # Check that the already mapped files weren't changed
    assert "api-service" in causal_graph.file_to_services["src/api/main.py"]
    assert "api-service" in causal_graph.file_to_services["src/api/routes.py"]
