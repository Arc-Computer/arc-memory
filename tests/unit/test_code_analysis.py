"""Unit tests for the code analysis plugin."""

import ast
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arc_memory.ingest.code_analysis import CodeAnalysisIngestor
from arc_memory.schema.models import EdgeRel, NodeType


@pytest.fixture
def code_analysis_ingestor():
    """Create a CodeAnalysisIngestor instance."""
    return CodeAnalysisIngestor()


def test_get_name(code_analysis_ingestor):
    """Test that the plugin returns the correct name."""
    assert code_analysis_ingestor.get_name() == "code_analysis"


def test_get_node_types(code_analysis_ingestor):
    """Test that the plugin returns the correct node types."""
    node_types = code_analysis_ingestor.get_node_types()
    assert NodeType.FUNCTION in node_types
    assert NodeType.CLASS in node_types
    assert NodeType.MODULE in node_types
    assert NodeType.COMPONENT in node_types
    assert NodeType.SERVICE in node_types


def test_get_edge_types(code_analysis_ingestor):
    """Test that the plugin returns the correct edge types."""
    edge_types = code_analysis_ingestor.get_edge_types()
    assert EdgeRel.CONTAINS in edge_types
    assert EdgeRel.CALLS in edge_types
    assert EdgeRel.IMPORTS in edge_types
    assert EdgeRel.INHERITS_FROM in edge_types
    assert EdgeRel.IMPLEMENTS in edge_types
    assert EdgeRel.PART_OF in edge_types


def test_get_code_files(code_analysis_ingestor, tmp_path):
    """Test that the plugin correctly identifies code files."""
    # Create test directory structure
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    # Create Python files
    (repo_path / "main.py").write_text("print('Hello, world!')")
    (repo_path / "utils.py").write_text("def add(a, b): return a + b")

    # Create a hidden directory with Python files (should be ignored)
    hidden_dir = repo_path / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "secret.py").write_text("print('Secret')")

    # Create a node_modules directory with JS files (should be ignored)
    node_modules = repo_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "index.js").write_text("console.log('Hello');")

    # Create a regular directory with JS files
    src_dir = repo_path / "src"
    src_dir.mkdir()
    (src_dir / "app.js").write_text("console.log('App');")

    # Get code files
    code_files = code_analysis_ingestor._get_code_files(repo_path)

    # Convert to relative paths for easier comparison
    rel_paths = [os.path.relpath(f, repo_path) for f in code_files]

    # Check results
    assert "main.py" in rel_paths
    assert "utils.py" in rel_paths
    assert os.path.join("src", "app.js") in rel_paths
    assert os.path.join(".hidden", "secret.py") not in rel_paths
    assert os.path.join("node_modules", "index.js") not in rel_paths


def test_analyze_python_file(code_analysis_ingestor, tmp_path):
    """Test Python file analysis."""
    # Create a test Python file
    test_file = tmp_path / "test_module.py"
    test_file.write_text("""
\"\"\"Test module docstring.\"\"\"

import os
import sys
from typing import List, Optional

class TestClass:
    \"\"\"Test class docstring.\"\"\"

    def __init__(self, name: str):
        \"\"\"Initialize with a name.\"\"\"
        self.name = name

    def greet(self) -> str:
        \"\"\"Return a greeting.\"\"\"
        return f"Hello, {self.name}!"

def add_numbers(a: int, b: int) -> int:
    \"\"\"Add two numbers and return the result.\"\"\"
    return a + b
""")

    # Analyze the file
    nodes, edges = code_analysis_ingestor._analyze_python_file(
        str(test_file), "test_module.py"
    )

    # Check that we have the expected nodes
    assert len(nodes) == 5  # Module, class, __init__ method, greet method, add_numbers function

    # Check module node
    module_node = next(n for n in nodes if n.type == NodeType.MODULE)
    assert module_node.name == "test_module"
    assert module_node.docstring == "Test module docstring."
    assert "os" in module_node.imports
    assert "sys" in module_node.imports

    # Check class node
    class_node = next(n for n in nodes if n.type == NodeType.CLASS)
    assert class_node.name == "TestClass"
    assert class_node.docstring == "Test class docstring."
    assert "__init__" in class_node.methods
    assert "greet" in class_node.methods

    # Check function node
    func_node = next(n for n in nodes if n.type == NodeType.FUNCTION and n.name == "add_numbers")
    assert func_node.docstring == "Add two numbers and return the result."
    assert func_node.return_type == "int"
    assert len(func_node.parameters) == 2
    assert func_node.parameters[0]["name"] == "a"
    assert func_node.parameters[0]["type"] == "int"

    # Check edges
    assert len(edges) == 5  # file-module, module-class, class-init, class-greet, module-function


@patch("arc_memory.llm.ollama_client.OllamaClient")
def test_enhance_with_llm(mock_ollama_client, code_analysis_ingestor):
    """Test LLM enhancement of code analysis."""
    # Setup mock
    mock_client = MagicMock()
    mock_ollama_client.return_value = mock_client
    code_analysis_ingestor.ollama_client = mock_client

    # Create test nodes and edges
    nodes = [
        MagicMock(id="function:test.py:test_func", type=NodeType.FUNCTION, embedding=None),
        MagicMock(id="class:test.py:TestClass", type=NodeType.CLASS, embedding=None)
    ]
    edges = [
        MagicMock(src="module:test.py", dst="function:test.py:test_func", rel=EdgeRel.CONTAINS)
    ]

    # Call the method
    enhanced_nodes, enhanced_edges = code_analysis_ingestor._enhance_with_llm(
        nodes, edges, "standard"
    )

    # Check that embeddings were added
    for node in enhanced_nodes:
        if hasattr(node, "embedding"):
            assert node.embedding is not None


def test_ingest(code_analysis_ingestor, tmp_path):
    """Test the ingest method."""
    # Create test Python files
    test_file1 = tmp_path / "test1.py"
    test_file1.write_text("""
\"\"\"Test module 1.\"\"\"

def test_function():
    \"\"\"Test function.\"\"\"
    return True
""")

    test_file2 = tmp_path / "test2.py"
    test_file2.write_text("""
\"\"\"Test module 2.\"\"\"

class TestClass:
    \"\"\"Test class.\"\"\"

    def __init__(self):
        \"\"\"Initialize.\"\"\"
        pass
""")

    # Call the method
    nodes, edges, metadata = code_analysis_ingestor.ingest(tmp_path, llm_enhancement_level="none")

    # Check results
    assert len(nodes) > 0
    assert len(edges) > 0
    assert metadata["processed_files"] > 0

    # Check that we have the expected node types
    node_types = [node.type for node in nodes]
    assert NodeType.MODULE in node_types
    assert NodeType.FUNCTION in node_types or NodeType.CLASS in node_types
