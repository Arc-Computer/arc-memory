"""Tests for the export SDK functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arc_memory.sdk import Arc
from arc_memory.sdk.errors import ExportSDKError
from arc_memory.sdk.export import export_knowledge_graph
from arc_memory.sdk.models import ExportResult


@pytest.fixture
def mock_adapter():
    """Create a mock database adapter."""
    adapter = MagicMock()
    adapter.connection = MagicMock()
    adapter.get_node_by_id.return_value = {"id": "file:test.py", "type": "file"}
    return adapter


@pytest.fixture
def mock_repo_path():
    """Create a temporary directory for the repository."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_export_data():
    """Create mock export data."""
    return {
        "pr": "test-pr",
        "nodes": [
            {"id": "file:test.py", "type": "file", "name": "test.py"},
            {"id": "commit:123", "type": "commit", "name": "Initial commit"},
        ],
        "edges": [
            {"src": "commit:123", "dst": "file:test.py", "rel": "MODIFIES"},
        ],
        "changed_files": ["test.py"],
    }


class TestExportSDK:
    """Tests for the export SDK functionality."""

    @patch("arc_memory.sdk.export.format_export_data")
    @patch("arc_memory.sdk.export.get_pr_modified_files")
    @patch("arc_memory.sdk.export.get_related_nodes")
    def test_export_knowledge_graph(
        self,
        mock_get_related_nodes,
        mock_get_pr_modified_files,
        mock_format_export_data,
        mock_adapter,
        mock_repo_path,
        mock_export_data,
    ):
        """Test exporting the knowledge graph."""
        # Set up mocks
        mock_get_pr_modified_files.return_value = ["test.py"]
        mock_get_related_nodes.return_value = (
            [
                {"id": "file:test.py", "type": "file", "name": "test.py"},
                {"id": "commit:123", "type": "commit", "name": "Initial commit"},
            ],
            [
                {"src": "commit:123", "dst": "file:test.py", "rel": "MODIFIES"},
            ],
        )
        mock_format_export_data.return_value = mock_export_data

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            output_path = Path(temp_file.name)

        try:
            # Call the function
            result = export_knowledge_graph(
                adapter=mock_adapter,
                repo_path=mock_repo_path,
                output_path=output_path,
                pr_sha="test-pr",
            )

            # Check the result
            assert isinstance(result, ExportResult)
            assert result.output_path == str(output_path)
            assert result.format == "json"
            assert result.entity_count == 2
            assert result.relationship_count == 1
            assert not result.compressed
            assert not result.signed
            assert result.signature_path is None
            assert result.execution_time > 0

            # Check that the file was written
            assert os.path.exists(output_path)
            with open(output_path, "r") as f:
                data = json.load(f)
                assert data == mock_export_data

            # Check that the mocks were called correctly
            mock_get_pr_modified_files.assert_called_once_with(
                mock_repo_path, "test-pr", "main"
            )
            mock_get_related_nodes.assert_called_once()
            mock_format_export_data.assert_called_once_with(
                pr_sha="test-pr",
                nodes=[
                    {"id": "file:test.py", "type": "file", "name": "test.py"},
                    {"id": "commit:123", "type": "commit", "name": "Initial commit"},
                ],
                edges=[
                    {"src": "commit:123", "dst": "file:test.py", "rel": "MODIFIES"},
                ],
                changed_files=["test.py"],
            )
        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)

    @patch("arc_memory.sdk.export.format_export_data")
    @patch("arc_memory.sdk.export.get_pr_modified_files")
    @patch("arc_memory.sdk.export.get_related_nodes")
    def test_export_knowledge_graph_with_compression(
        self,
        mock_get_related_nodes,
        mock_get_pr_modified_files,
        mock_format_export_data,
        mock_adapter,
        mock_repo_path,
        mock_export_data,
    ):
        """Test exporting the knowledge graph with compression."""
        # Set up mocks
        mock_get_pr_modified_files.return_value = ["test.py"]
        mock_get_related_nodes.return_value = (
            [
                {"id": "file:test.py", "type": "file", "name": "test.py"},
                {"id": "commit:123", "type": "commit", "name": "Initial commit"},
            ],
            [
                {"src": "commit:123", "dst": "file:test.py", "rel": "MODIFIES"},
            ],
        )
        mock_format_export_data.return_value = mock_export_data

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            output_path = Path(temp_file.name)

        try:
            # Call the function
            result = export_knowledge_graph(
                adapter=mock_adapter,
                repo_path=mock_repo_path,
                output_path=output_path,
                pr_sha="test-pr",
                compress=True,
            )

            # Check the result
            assert isinstance(result, ExportResult)
            assert result.output_path == f"{output_path}.gz"
            assert result.format == "json"
            assert result.entity_count == 2
            assert result.relationship_count == 1
            assert result.compressed
            assert not result.signed
            assert result.signature_path is None
            assert result.execution_time > 0

            # Check that the compressed file was written
            compressed_path = Path(f"{output_path}.gz")
            assert os.path.exists(compressed_path)

            # Clean up the compressed file
            if os.path.exists(compressed_path):
                os.unlink(compressed_path)
        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)

    @patch("arc_memory.sdk.export.get_pr_modified_files")
    def test_export_knowledge_graph_git_error(
        self,
        mock_get_pr_modified_files,
        mock_adapter,
        mock_repo_path,
    ):
        """Test handling of Git errors."""
        # Set up mocks
        mock_get_pr_modified_files.side_effect = Exception("Git error")

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            output_path = Path(temp_file.name)

        try:
            # Call the function and expect an error
            with pytest.raises(ExportSDKError, match="Error exporting knowledge graph"):
                export_knowledge_graph(
                    adapter=mock_adapter,
                    repo_path=mock_repo_path,
                    output_path=output_path,
                    pr_sha="test-pr",
                )
        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestArcExport:
    """Tests for the Arc class export methods."""

    @patch("arc_memory.sdk.export.export_knowledge_graph")
    @patch("arc_memory.sdk.core.get_db_adapter")
    @patch("arc_memory.export.export_graph")
    def test_export_graph(self, mock_export_graph_impl, mock_get_db_adapter, mock_export_knowledge_graph, mock_repo_path):
        """Test the export_graph method of the Arc class."""
        # Set up mocks
        mock_export_knowledge_graph.return_value = ExportResult(
            output_path="/path/to/export.json",
            format="json",
            entity_count=10,
            relationship_count=20,
            compressed=False,
            signed=False,
            execution_time=1.5,
        )

        # Mock the export_graph_impl function
        mock_export_graph_impl.return_value = Path("/path/to/export.json")

        # Mock the database adapter
        mock_adapter = MagicMock()
        mock_adapter.is_connected.return_value = True
        mock_adapter.db_path = "/path/to/db.sqlite"
        mock_get_db_adapter.return_value = mock_adapter

        # Create an Arc instance
        arc = Arc(repo_path=mock_repo_path)

        # Replace the adapter with our mock
        arc.adapter = mock_adapter

        # Call the method with PR SHA
        result = arc.export_graph(
            output_path="/path/to/export.json",
            pr_sha="test-pr",
        )

        # Check the result for PR export
        assert isinstance(result, Path)
        assert str(result) == "/path/to/export.json"

        # Check that the mock was called correctly
        mock_export_graph_impl.assert_called_once_with(
            db_path=Path("/path/to/db.sqlite"),
            repo_path=arc.repo_path,
            pr_sha="test-pr",
            output_path=Path("/path/to/export.json"),
            compress=True,
            sign=False,
            key_id=None,
            base_branch="main",
            max_hops=3,
            enhance_for_llm=True,
            include_causal=True
        )

        # The current implementation only supports PR-specific export
        # We don't need to test the general export method since it's not implemented yet


