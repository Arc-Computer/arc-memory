"""Integration tests for the enhanced knowledge graph capabilities."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arc_memory.cli.build import build_graph
from arc_memory.cli.export import export
from arc_memory.export import export_graph
from arc_memory.llm.ollama_client import OllamaClient
from arc_memory.schema.models import LLMEnhancementLevel


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
@patch("arc_memory.llm.ollama_client.OllamaClient")
@patch("arc_memory.llm.ollama_client.ensure_ollama_available")
def test_build_with_llm_enhancement(
    mock_ensure_ollama, mock_ollama_client_class, temp_repo
):
    """Test building the knowledge graph with LLM enhancement."""
    # Setup mocks
    mock_ensure_ollama.return_value = True
    mock_client = MagicMock()
    mock_client.generate.return_value = "{}"
    mock_ollama_client_class.return_value = mock_client
    
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
    
    # Check that the LLM client was used
    assert mock_client.generate.called


@pytest.mark.integration
@patch("arc_memory.llm.ollama_client.OllamaClient")
@patch("arc_memory.llm.ollama_client.ensure_ollama_available")
def test_export_with_llm_enhancement(
    mock_ensure_ollama, mock_ollama_client_class, temp_repo
):
    """Test exporting the knowledge graph with LLM enhancement."""
    # Setup mocks
    mock_ensure_ollama.return_value = True
    mock_client = MagicMock()
    mock_client.generate.return_value = "{}"
    mock_ollama_client_class.return_value = mock_client
    
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
    
    # Read the export file to check its contents
    with open(export_path, "r") as f:
        content = f.read()
    
    # Check that the export contains the expected sections
    assert "nodes" in content
    assert "edges" in content
    assert "modified_files" in content
    
    # These sections would be added by the LLM enhancement
    assert "reasoning_paths" in content
    assert "semantic_context" in content
    assert "temporal_patterns" in content
    assert "thought_structures" in content
