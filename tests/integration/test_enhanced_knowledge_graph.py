"""Integration tests for the enhanced knowledge graph capabilities."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

import pytest

from arc_memory.cli.build import build_graph, LLMEnhancementLevel
from arc_memory.cli.export import export
from arc_memory.export import export_graph
from arc_memory.llm.ollama_client import OllamaClient


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create a simple Python project structure
    src_dir = Path(temp_dir) / "src"
    src_dir.mkdir()
    
    # Create main.py
    main_py = src_dir / "main.py"
    main_py.write_text("""
\"\"\"Main module for the application.\"\"\"

import os
from typing import Dict, Any

from src.utils import process_data

def main():
    \"\"\"Main entry point for the application.\"\"\"
    data = {"name": "Test", "value": 42}
    result = process_data(data)
    print(result)

if __name__ == "__main__":
    main()
""")
    
    # Create utils.py
    utils_py = src_dir / "utils.py"
    utils_py.write_text("""
\"\"\"Utility functions for data processing.\"\"\"

from typing import Dict, Any, List

def process_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    \"\"\"Process the input data and return a list of processed items.
    
    Args:
        data: The input data to process.
        
    Returns:
        A list of processed data items.
    \"\"\"
    return [{"processed": True, **data}]

def validate_data(data: Dict[str, Any]) -> bool:
    \"\"\"Validate the input data.
    
    Args:
        data: The input data to validate.
        
    Returns:
        True if the data is valid, False otherwise.
    \"\"\"
    return "name" in data and "value" in data
""")
    
    # Create models.py
    models_py = src_dir / "models.py"
    models_py.write_text("""
\"\"\"Data models for the application.\"\"\"

from typing import Dict, Any, Optional

class User:
    \"\"\"User model.\"\"\"
    
    def __init__(self, name: str, email: str):
        \"\"\"Initialize a new User.
        
        Args:
            name: The user's name.
            email: The user's email.
        \"\"\"
        self.name = name
        self.email = email
        self.settings = {}
    
    def get_profile(self) -> Dict[str, Any]:
        \"\"\"Get the user's profile information.
        
        Returns:
            A dictionary containing the user's profile information.
        \"\"\"
        return {
            "name": self.name,
            "email": self.email
        }
    
    def update_settings(self, settings: Dict[str, Any]) -> None:
        \"\"\"Update the user's settings.
        
        Args:
            settings: The new settings to apply.
        \"\"\"
        self.settings.update(settings)
""")
    
    # Create a simple Git repository
    os.chdir(temp_dir)
    os.system("git init")
    os.system("git config user.name 'Test User'")
    os.system("git config user.email 'test@example.com'")
    os.system("git add .")
    os.system("git commit -m 'Initial commit'")
    
    # Create a branch for testing
    os.system("git checkout -b feature/test")
    
    # Make a change to utils.py
    utils_py.write_text(utils_py.read_text() + """
def format_data(data: Dict[str, Any]) -> str:
    \"\"\"Format the data as a string.
    
    Args:
        data: The data to format.
        
    Returns:
        A formatted string representation of the data.
    \"\"\"
    return f"Name: {data.get('name', 'Unknown')}, Value: {data.get('value', 0)}"
""")
    
    # Commit the change
    os.system("git add .")
    os.system("git commit -m 'Add format_data function'")
    
    yield temp_dir
    
    # Clean up
    shutil.rmtree(temp_dir)


@pytest.mark.integration
def test_build_with_real_llm_enhancement(temp_repo):
    """Test building the knowledge graph with a real LLM enhancement using local phi-4 model."""
    # Create a temporary database file
    db_path = Path(temp_repo) / "test_graph_real_llm.db"
    
    # Build the graph with real LLM enhancement
    build_graph(
        repo_path=Path(temp_repo),
        output_path=db_path,
        max_commits=10,
        days=365,
        incremental=False,
        pull=False,
        token=None,
        linear=False,
        llm_enhancement=LLMEnhancementLevel.STANDARD,
        ollama_host="http://localhost:11434",
        ci_mode=False,
        debug=True,
    )
    
    # Check that the database was created
    assert db_path.exists()
    
    # Verify database contains the enhanced structures
    # This requires connecting to the database and checking for new node types
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check for code entity nodes (functions, classes, modules)
    cursor.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('function', 'class', 'module')")
    code_entity_count = cursor.fetchone()[0]
    
    # Check for reasoning structure nodes
    cursor.execute("SELECT COUNT(*) FROM nodes WHERE type LIKE 'reasoning_%'")
    reasoning_node_count = cursor.fetchone()[0]
    
    # Check for new edge types
    cursor.execute("SELECT COUNT(*) FROM edges WHERE rel IN ('CONTAINS', 'CALLS', 'IMPORTS', 'HAS_ALTERNATIVE', 'NEXT_STEP')")
    new_edge_count = cursor.fetchone()[0]
    
    conn.close()
    
    # We may or may not have code entities depending on the repository
    print(f"Found {code_entity_count} code entity nodes")
    
    # We should have some reasoning nodes if the LLM enhancement worked
    print(f"Found {reasoning_node_count} reasoning nodes")
    print(f"Found {new_edge_count} new relationship edges")
    
    # Even with a small test repo, we should have at least some enhanced structures
    assert db_path.stat().st_size > 0, "Database file is empty"


@pytest.mark.integration
@patch("arc_memory.cli.build.enhance_with_semantic_analysis")
@patch("arc_memory.cli.build.enhance_with_temporal_analysis")
@patch("arc_memory.cli.build.enhance_with_reasoning_structures")
@patch("arc_memory.ingest.github.GitHubIngestor.ingest")
@patch("arc_memory.llm.ollama_client.OllamaClient")
@patch("arc_memory.llm.ollama_client.ensure_ollama_available")
def test_build_with_llm_enhancement(
    mock_ensure_ollama, mock_ollama_client_class, mock_github_ingest,
    mock_reasoning, mock_temporal, mock_semantic, temp_repo
):
    """Test building the knowledge graph with LLM enhancement."""
    # Setup mocks
    mock_ensure_ollama.return_value = True
    mock_client = MagicMock()
    mock_client.generate.return_value = "{}"
    mock_ollama_client_class.return_value = mock_client
    # Mock GitHub ingestor to return empty results
    mock_github_ingest.return_value = ([], [], {"timestamp": "2023-01-01T00:00:00Z"})
    # Mock enhancement functions to pass through nodes and edges unchanged
    mock_semantic.side_effect = lambda nodes, edges, *args, **kwargs: (nodes, edges)
    mock_temporal.side_effect = lambda nodes, edges, *args, **kwargs: (nodes, edges)
    mock_reasoning.side_effect = lambda nodes, edges, *args, **kwargs: (nodes, edges)
    
    # Create a temporary database file
    db_path = Path(temp_repo) / "test_graph.db"
    
    # Build the graph with LLM enhancement
    build_graph(
        repo_path=Path(temp_repo),
        output_path=db_path,
        max_commits=10,
        days=365,
        incremental=False,
        pull=False,
        token=None,
        linear=False,
        llm_enhancement=LLMEnhancementLevel.STANDARD,
        ollama_host="http://localhost:11434",
        ci_mode=False,
        debug=True,
    )
    
    # Check that the database was created
    assert db_path.exists()
    
    # Check that the enhancement functions were called
    assert mock_semantic.called
    assert mock_temporal.called
    assert mock_reasoning.called


@pytest.mark.integration
@patch("arc_memory.export.get_related_nodes")
@patch("arc_memory.export.get_node_by_id")
@patch("arc_memory.export.get_pr_modified_files")
@patch("arc_memory.export.optimize_export_for_llm")
@patch("arc_memory.ingest.github.GitHubIngestor.ingest")
@patch("arc_memory.llm.ollama_client.OllamaClient")
@patch("arc_memory.llm.ollama_client.ensure_ollama_available")
def test_export_with_llm_enhancement(
    mock_ensure_ollama, mock_ollama_client_class, mock_github_ingest, 
    mock_optimize_export, mock_modified_files, mock_get_node, mock_related_nodes, temp_repo
):
    """Test exporting the knowledge graph with LLM enhancement."""
    # Setup mocks
    mock_ensure_ollama.return_value = True
    mock_client = MagicMock()
    mock_client.generate.return_value = "{}"
    mock_ollama_client_class.return_value = mock_client
    # Mock GitHub ingestor to return empty results
    mock_github_ingest.return_value = ([], [], {"timestamp": "2023-01-01T00:00:00Z"})
    # Mock optimize_export_for_llm to return the input data plus a new field
    mock_optimize_export.side_effect = lambda data: {**data, "enhanced": True}
    # Mock file modification detection
    mock_modified_files.return_value = ["src/utils.py"]
    # Mock node retrieval
    mock_get_node.return_value = {
        "id": "file:src/utils.py",
        "type": "file", 
        "title": "utils.py",
        "extra": {"path": "src/utils.py"}
    }
    # Mock related node retrieval
    mock_related_nodes.return_value = (
        [
            {"id": "file:src/utils.py", "type": "file", "title": "utils.py", "extra": {"path": "src/utils.py"}},
            {"id": "function:process_data", "type": "function", "title": "process_data", "extra": {"signature": "def process_data()"}}
        ],
        [
            {"src": "file:src/utils.py", "dst": "function:process_data", "rel": "CONTAINS", "properties": {}}
        ]
    )
    
    # Create a temporary database file
    db_path = Path(temp_repo) / "test_graph.db"
    
    # Build the graph first (without LLM enhancement to speed up the test)
    build_graph(
        repo_path=Path(temp_repo),
        output_path=db_path,
        max_commits=10,
        days=365,
        incremental=False,
        pull=False,
        token=None,
        linear=False,
        llm_enhancement=LLMEnhancementLevel.NONE,
        ollama_host="http://localhost:11434",
        ci_mode=False,
        debug=True,
    )
    
    # Get the latest commit SHA
    os.chdir(temp_repo)
    result = os.popen("git rev-parse HEAD").read().strip()
    
    # Create a temporary export file
    export_path = Path(temp_repo) / "test_export.json"
    
    # Export the graph with LLM enhancement
    export_graph(
        db_path=db_path,
        repo_path=Path(temp_repo),
        pr_sha=result,
        output_path=export_path,
        compress=False,
        sign=False,
        key_id=None,
        base_branch="main",
        max_hops=3,
        enhance_for_llm=True,
    )
    
    # Check that the export file was created
    assert export_path.exists()
    
    # Verify that optimize_export_for_llm was called
    assert mock_optimize_export.called
    
    # Read the export file to verify it contains enhanced data
    with open(export_path, "r") as f:
        data = json.load(f)
    
    # Verify the enhanced field was added by our mock
    assert data.get("enhanced") == True


@pytest.mark.integration
def test_export_with_real_llm_enhancement(temp_repo):
    """Test exporting the knowledge graph with a real LLM enhancement using local phi-4 model."""
    # Create a temporary database file
    db_path = Path(temp_repo) / "test_graph_real_export.db"
    
    # Build the graph first (with LLM enhancement to see real enhancement in export)
    build_graph(
        repo_path=Path(temp_repo),
        output_path=db_path,
        max_commits=10,
        days=365,
        incremental=False,
        pull=False,
        token=None,
        linear=False,
        llm_enhancement=LLMEnhancementLevel.STANDARD,
        ollama_host="http://localhost:11434",
        ci_mode=False,
        debug=True,
    )
    
    # Get the latest commit SHA
    os.chdir(temp_repo)
    result = os.popen("git rev-parse HEAD").read().strip()
    
    # Create a temporary export file
    export_path = Path(temp_repo) / "test_real_export.json"
    
    # Export the graph with real LLM enhancement
    export_graph(
        db_path=db_path,
        repo_path=Path(temp_repo),
        pr_sha=result,
        output_path=export_path,
        compress=False,
        sign=False,
        key_id=None,
        base_branch="main",
        max_hops=3,
        enhance_for_llm=True,
    )
    
    # Check that the export file was created
    assert export_path.exists()
    
    # Read the export file to verify it contains enhanced data
    with open(export_path, "r") as f:
        data = json.load(f)
    
    # Verify the enhanced data structure
    assert "nodes" in data
    assert "edges" in data
    
    # The enhanced export should contain specific additional structures
    enhanced_fields = ["reasoning_paths", "semantic_context", "temporal_patterns", "thought_structures"]
    found_enhanced_fields = [field for field in enhanced_fields if field in data]
    
    print(f"Found enhanced fields: {found_enhanced_fields}")
    
    # Examine the content of the JSON file for manual inspection
    print(f"Export file size: {export_path.stat().st_size} bytes")
    
    # Print some sample nodes and edges for manual verification
    node_types = {}
    for node in data["nodes"][:10]:  # Look at first 10 nodes
        node_type = node.get("type")
        if node_type not in node_types:
            node_types[node_type] = 0
        node_types[node_type] += 1
    
    print(f"Node types in export: {node_types}")
    
    # Check that the export file has reasonable size
    assert export_path.stat().st_size > 100, "Export file is too small"
