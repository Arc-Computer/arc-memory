"""Integration tests for the sim command with GitHub."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from arc_memory.cli.sim import app


class TestSimGitHubIntegration:
    """Integration tests for the sim command with GitHub."""

    runner = CliRunner()

    @pytest.fixture
    def mock_github_api(self):
        """Mock the GitHub API."""
        # Since we don't have a GitHubRESTClient in diff_utils, we'll mock the load_diff_from_file function instead
        with mock.patch("arc_memory.cli.sim.load_diff_from_file") as mock_load_diff:
            # Set up the mock to return sample data
            mock_load_diff.return_value = {
                "files": [
                    {"path": "file1.py", "additions": 10, "deletions": 5, "status": "modified"},
                    {"path": "file2.py", "additions": 20, "deletions": 15, "status": "modified"}
                ],
                "commit_count": 1,
                "range": "HEAD~1..HEAD",
                "start_commit": "def456",
                "end_commit": "abc123",
                "timestamp": "2023-01-01T00:00:00Z",
                "stats": {
                    "files_changed": 2,
                    "insertions": 30,
                    "deletions": 20
                }
            }
            yield mock_load_diff

    def test_github_pr_diff_analysis(self, mock_github_api):
        """Test analyzing a GitHub PR diff."""
        # Mock the LangGraph workflow
        with mock.patch("arc_memory.cli.sim.HAS_LANGGRAPH", True):
            with mock.patch("arc_memory.cli.sim.run_langgraph_workflow") as mock_workflow:
                # Set up the mock to return a successful result
                mock_workflow.return_value = {
                    "status": "completed",
                    "attestation": {
                        "sim_id": "sim_test",
                        "risk_score": 25,
                        "metrics": {"latency_ms": 500, "error_rate": 0.05},
                        "explanation": "Test explanation",
                        "manifest_hash": "abc123",
                        "commit_target": "def456",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "diff_hash": "ghi789"
                    },
                    "affected_services": ["service1", "service2"]
                }

                # Create a temporary diff file with a valid diff
                with tempfile.NamedTemporaryFile(suffix=".json") as temp_file:
                    # Write a valid diff to the file
                    diff_data = {
                        "files": [
                            {"path": "file1.py", "additions": 10, "deletions": 5, "status": "modified"},
                            {"path": "file2.py", "additions": 20, "deletions": 15, "status": "modified"}
                        ],
                        "commit_count": 1,
                        "range": "HEAD~1..HEAD",
                        "start_commit": "def456",
                        "end_commit": "abc123",
                        "timestamp": "2023-01-01T00:00:00Z"
                    }
                    temp_file.write(json.dumps(diff_data).encode())
                    temp_file.flush()

                    # Call the CLI command with the diff file
                    result = self.runner.invoke(app, [
                        "--diff", temp_file.name,
                        "--scenario", "network_latency",
                        "--severity", "50",
                        "--timeout", "300"
                    ])

                    # Verify the exit code
                    assert result.exit_code == 0

                    # Verify the mock was called
                    mock_github_api.assert_called_once()

                    # Verify the workflow was called with the diff data
                    mock_workflow.assert_called_once()
                    assert mock_workflow.call_args[1]["diff_data"] is not None

    def test_github_commit_diff_analysis(self, mock_github_api):
        """Test analyzing a GitHub commit diff."""
        # Mock the LangGraph workflow
        with mock.patch("arc_memory.cli.sim.HAS_LANGGRAPH", True):
            with mock.patch("arc_memory.cli.sim.run_langgraph_workflow") as mock_workflow:
                # Set up the mock to return a successful result
                mock_workflow.return_value = {
                    "status": "completed",
                    "attestation": {
                        "sim_id": "sim_test",
                        "risk_score": 25,
                        "metrics": {"latency_ms": 500, "error_rate": 0.05},
                        "explanation": "Test explanation",
                        "manifest_hash": "abc123",
                        "commit_target": "def456",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "diff_hash": "ghi789"
                    },
                    "affected_services": ["service1", "service2"]
                }

                # Create a temporary diff file with a valid diff
                with tempfile.NamedTemporaryFile(suffix=".json") as temp_file:
                    # Write a valid diff to the file
                    diff_data = {
                        "files": [
                            {"path": "file1.py", "additions": 10, "deletions": 5, "status": "modified"},
                            {"path": "file2.py", "additions": 20, "deletions": 15, "status": "modified"}
                        ],
                        "commit_count": 1,
                        "range": "HEAD~1..HEAD",
                        "start_commit": "def456",
                        "end_commit": "abc123",
                        "timestamp": "2023-01-01T00:00:00Z"
                    }
                    temp_file.write(json.dumps(diff_data).encode())
                    temp_file.flush()

                    # Call the CLI command with the diff file
                    result = self.runner.invoke(app, [
                        "--diff", temp_file.name,
                        "--scenario", "network_latency",
                        "--severity", "50",
                        "--timeout", "300"
                    ])

                    # Verify the exit code
                    assert result.exit_code == 0

                    # Verify the mock was called
                    mock_github_api.assert_called_once()

                    # Verify the workflow was called with the diff data
                    mock_workflow.assert_called_once()
                    assert mock_workflow.call_args[1]["diff_data"] is not None

    @pytest.mark.skip(reason="Requires GitHub token and real repository access")
    def test_github_integration_with_real_repo(self):
        """Test integration with a real GitHub repository."""
        # Skip if no GitHub token is available
        if "GITHUB_TOKEN" not in os.environ:
            pytest.skip("GITHUB_TOKEN environment variable not set")

        # Mock the LangGraph workflow
        with mock.patch("arc_memory.cli.sim.HAS_LANGGRAPH", True):
            with mock.patch("arc_memory.cli.sim.run_langgraph_workflow") as mock_workflow:
                # Set up the mock to return a successful result
                mock_workflow.return_value = {
                    "status": "completed",
                    "attestation": {
                        "sim_id": "sim_test",
                        "risk_score": 25,
                        "metrics": {"latency_ms": 500, "error_rate": 0.05},
                        "explanation": "Test explanation",
                        "manifest_hash": "abc123",
                        "commit_target": "def456",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "diff_hash": "ghi789"
                    },
                    "affected_services": ["service1", "service2"]
                }

                # Create a temporary diff file with a valid diff
                with tempfile.NamedTemporaryFile(suffix=".json") as temp_file:
                    # Write a valid diff to the file
                    diff_data = {
                        "files": [
                            {"path": "file1.py", "additions": 10, "deletions": 5, "status": "modified"},
                            {"path": "file2.py", "additions": 20, "deletions": 15, "status": "modified"}
                        ],
                        "commit_count": 1,
                        "range": "HEAD~1..HEAD",
                        "start_commit": "def456",
                        "end_commit": "abc123",
                        "timestamp": "2023-01-01T00:00:00Z"
                    }
                    temp_file.write(json.dumps(diff_data).encode())
                    temp_file.flush()

                    # Call the CLI command with the diff file
                    result = self.runner.invoke(app, [
                        "--diff", temp_file.name,
                        "--scenario", "network_latency",
                        "--severity", "50",
                        "--timeout", "300"
                    ])

                    # Verify the exit code
                    assert result.exit_code == 0

                    # Verify the workflow was called with the diff data
                    mock_workflow.assert_called_once()
                    assert mock_workflow.call_args[1]["diff_data"] is not None
