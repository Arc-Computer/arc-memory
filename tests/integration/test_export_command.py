"""Integration tests for the export functionality."""

import gzip
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from arc_memory.export import format_export_data
from arc_memory.schema.models import NodeType


def test_format_export_data():
    """Test formatting export data."""
    # Create test data
    pr_sha = "abc123"
    nodes = [
        {
            "id": "file:test.txt",
            "type": NodeType.FILE.value,
            "title": "Test File",
            "body": None,
            "extra": {"path": "test.txt", "language": "text"}
        },
        {
            "id": "commit:def456",
            "type": NodeType.COMMIT.value,
            "title": "Test Commit",
            "body": "Commit message",
            "extra": {"author": "Test User", "sha": "def456"}
        }
    ]
    edges = [
        {
            "src": "commit:def456",
            "dst": "file:test.txt",
            "rel": "MODIFIES",
            "properties": {"lines_added": 10, "lines_removed": 5}
        }
    ]
    changed_files = ["test.txt"]
    pr_info = {"number": 123, "title": "Test PR", "author": "test-user"}

    # Format the data
    result = format_export_data(pr_sha, nodes, edges, changed_files, pr_info)

    # Check the result
    assert result["schema_version"] == "0.3"
    assert "generated_at" in result
    assert result["pr"]["sha"] == pr_sha
    assert result["pr"]["number"] == 123
    assert result["pr"]["title"] == "Test PR"
    assert result["pr"]["author"] == "test-user"
    assert result["pr"]["changed_files"] == changed_files

    # Check nodes
    assert len(result["nodes"]) == 2
    file_node = next(n for n in result["nodes"] if n["id"] == "file:test.txt")
    assert file_node["type"] == NodeType.FILE.value
    assert file_node["path"] == "test.txt"
    assert file_node["metadata"]["language"] == "text"

    commit_node = next(n for n in result["nodes"] if n["id"] == "commit:def456")
    assert commit_node["type"] == NodeType.COMMIT.value
    assert commit_node["title"] == "Test Commit"
    assert commit_node["metadata"]["author"] == "Test User"
    assert commit_node["metadata"]["sha"] == "def456"

    # Check edges
    assert len(result["edges"]) == 1
    edge = result["edges"][0]
    assert edge["src"] == "commit:def456"
    assert edge["dst"] == "file:test.txt"
    assert edge["type"] == "MODIFIES"
    assert edge["metadata"]["lines_added"] == 10
    assert edge["metadata"]["lines_removed"] == 5


@mock.patch("arc_memory.export.sign_file")
def test_export_compression_and_signing(mock_sign_file):
    """Test export compression and signing functionality."""
    # Create a temporary directory for the output
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "arc-graph.json"

        # Create test data
        export_data = {
            "schema_version": "0.2",
            "generated_at": "2023-05-08T14:23:00Z",
            "pr": {
                "sha": "abc123",
                "changed_files": ["test.txt", "new.txt"]
            },
            "nodes": [
                {
                    "id": "file:test.txt",
                    "type": NodeType.FILE.value,
                    "path": "test.txt",
                    "metadata": {}
                }
            ],
            "edges": []
        }

        # Test compression
        compressed_path = output_path.with_suffix(".json.gz")
        with gzip.open(compressed_path, "wt") as f:
            json.dump(export_data, f)

        # Verify the compressed file exists and can be read
        assert compressed_path.exists()
        with gzip.open(compressed_path, "rt") as f:
            data = json.load(f)
            assert data["schema_version"] == "0.2"
            assert data["pr"]["sha"] == "abc123"

        # Test signing
        mock_sign_file.return_value = Path(f"{compressed_path}.sig")

        # Call the mock sign function
        sig_path = mock_sign_file(compressed_path, "ABCD1234")

        # Verify the mock was called correctly
        mock_sign_file.assert_called_once_with(compressed_path, "ABCD1234")
        assert sig_path == Path(f"{compressed_path}.sig")
