"""Integration tests for the export command."""

import gzip
import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from arc_memory.cli.export import app as export_app
from arc_memory.schema.models import EdgeRel, NodeType


@pytest.fixture
def mock_export_graph():
    """Mock the export_graph function."""
    with mock.patch("arc_memory.cli.export.export_graph") as mock_export:
        # Set up the mock to return a path
        mock_export.return_value = Path("/tmp/arc-graph.json.gz")
        yield mock_export


def test_export_command(mock_export_graph):
    """Test the export command."""
    runner = CliRunner()
    result = runner.invoke(
        export_app, ["abc123", "--out", "arc-graph.json", "--compress"], catch_exceptions=False
    )

    # Check that the command ran successfully
    assert result.exit_code == 0

    # Check that export_graph was called with the expected arguments
    mock_export_graph.assert_called_once()
    args, kwargs = mock_export_graph.call_args
    assert kwargs["pr_sha"] == "abc123"
    assert kwargs["output_path"] == Path("arc-graph.json")
    assert kwargs["compress"] is True
    assert kwargs["sign"] is False
    assert kwargs["key_id"] is None


def test_export_command_with_signing(mock_export_graph):
    """Test the export command with signing."""
    runner = CliRunner()
    result = runner.invoke(
        export_app, ["abc123", "--out", "arc-graph.json", "--sign", "--key", "ABCD1234"], catch_exceptions=False
    )

    # Check that the command ran successfully
    assert result.exit_code == 0

    # Check that export_graph was called with the expected arguments
    mock_export_graph.assert_called_once()
    args, kwargs = mock_export_graph.call_args
    assert kwargs["pr_sha"] == "abc123"
    assert kwargs["output_path"] == Path("arc-graph.json")
    assert kwargs["sign"] is True
    assert kwargs["key_id"] == "ABCD1234"


def test_export_command_with_custom_paths(mock_export_graph):
    """Test the export command with custom repository and database paths."""
    runner = CliRunner()
    result = runner.invoke(
        export_app, [
            "abc123", "--out", "arc-graph.json",
            "--repo", "/custom/repo/path",
            "--db", "/custom/db/path"
        ], catch_exceptions=False
    )

    # Check that the command ran successfully
    assert result.exit_code == 0

    # Check that export_graph was called with the expected arguments
    mock_export_graph.assert_called_once()
    args, kwargs = mock_export_graph.call_args
    assert kwargs["pr_sha"] == "abc123"
    assert kwargs["output_path"] == Path("arc-graph.json")
    assert kwargs["repo_path"] == Path("/custom/repo/path")
    assert kwargs["db_path"] == Path("/custom/db/path")


def test_export_command_with_base_branch(mock_export_graph):
    """Test the export command with a custom base branch."""
    runner = CliRunner()
    result = runner.invoke(
        export_app, ["abc123", "--out", "arc-graph.json", "--base", "develop"], catch_exceptions=False
    )

    # Check that the command ran successfully
    assert result.exit_code == 0

    # Check that export_graph was called with the expected arguments
    mock_export_graph.assert_called_once()
    args, kwargs = mock_export_graph.call_args
    assert kwargs["pr_sha"] == "abc123"
    assert kwargs["output_path"] == Path("arc-graph.json")
    assert kwargs["base_branch"] == "develop"


@mock.patch("arc_memory.cli.export.ensure_arc_dir")
def test_export_command_database_not_found(mock_ensure_arc_dir, mock_export_graph):
    """Test the export command when the database is not found."""
    # Set up the mock to return a path that doesn't exist
    mock_ensure_arc_dir.return_value = Path("/nonexistent")

    # Set up the mock to raise an exception
    mock_export_graph.side_effect = FileNotFoundError("Database not found")

    runner = CliRunner()
    result = runner.invoke(
        export_app, ["abc123", "--out", "arc-graph.json"], catch_exceptions=False
    )

    # Check that the command failed
    assert result.exit_code == 1

    # Check that the error message is in the output
    assert "Database not found" in result.stdout


@mock.patch("arc_memory.cli.export.export_graph")
def test_export_command_end_to_end(mock_export_graph):
    """Test the export command end-to-end with a real output file."""
    # Create a temporary directory for the output
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "arc-graph.json"

        # Set up the mock to create a real output file
        def side_effect(*args, **kwargs):
            # Create a simple export file
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

            # Write the file based on compression setting
            if kwargs.get("compress", True):
                final_path = output_path.with_suffix(".json.gz")
                with gzip.open(final_path, "wt") as f:
                    json.dump(export_data, f)
            else:
                with open(output_path, "w") as f:
                    json.dump(export_data, f)

            return output_path if not kwargs.get("compress", True) else output_path.with_suffix(".json.gz")

        mock_export_graph.side_effect = side_effect

        # Run the command
        runner = CliRunner()
        result = runner.invoke(
            export_app, ["abc123", "--out", str(output_path), "--no-compress"], catch_exceptions=False
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the output file was created
        assert output_path.exists()

        # Check the content of the output file
        with open(output_path, "r") as f:
            data = json.load(f)
            assert data["schema_version"] == "0.2"
            assert data["pr"]["sha"] == "abc123"
            assert len(data["nodes"]) == 1
            assert data["nodes"][0]["id"] == "file:test.txt"
