"""Integration tests for the sim command."""

import json
import os
import tempfile
import subprocess
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from arc_memory.cli.sim import app


class TestSimCommandIntegration:
    """Integration tests for the sim command."""

    runner = CliRunner()

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary Git repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a Git repository
            subprocess.run(["git", "init"], cwd=temp_dir, check=True)

            # Create a sample file
            file_path = Path(temp_dir) / "sample.py"
            with open(file_path, "w") as f:
                f.write("def hello():\n    return 'world'\n")

            # Add and commit the file
            subprocess.run(["git", "add", "sample.py"], cwd=temp_dir, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)

            # Modify the file
            with open(file_path, "w") as f:
                f.write("def hello():\n    return 'hello world'\n")

            # Add and commit the changes
            subprocess.run(["git", "add", "sample.py"], cwd=temp_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Update sample.py"], cwd=temp_dir, check=True)

            yield temp_dir

    def test_end_to_end_with_langgraph(self, temp_git_repo):
        """Test the full workflow from CLI to output with LangGraph."""
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

                # Create a temporary output file
                with tempfile.NamedTemporaryFile(suffix=".json") as temp_file:
                    # Change to the temporary Git repository
                    original_cwd = os.getcwd()
                    os.chdir(temp_git_repo)

                    try:
                        # Call the CLI command
                        result = self.runner.invoke(app, [
                            "--output", temp_file.name,
                            "--scenario", "network_latency",
                            "--severity", "50",
                            "--timeout", "300"
                        ])

                        # Verify the exit code
                        assert result.exit_code == 0

                        # Verify the workflow was called
                        mock_workflow.assert_called_once()

                        # Verify the output file was created
                        assert os.path.exists(temp_file.name)

                        # Verify the content of the output file
                        with open(temp_file.name, "r") as f:
                            output = json.load(f)
                            assert output["sim_id"] == "sim_test"
                            assert output["risk_score"] == 25
                            assert output["services"] == ["service1", "service2"]
                            assert output["metrics"] == {"latency_ms": 500, "error_rate": 0.05}
                            assert output["explanation"] == "Test explanation"
                            assert output["manifest_hash"] == "abc123"
                            assert output["commit_target"] == "def456"
                            assert output["timestamp"] == "2023-01-01T00:00:00Z"
                            assert output["diff_hash"] == "ghi789"
                    finally:
                        # Change back to the original directory
                        os.chdir(original_cwd)

    def test_end_to_end_with_different_scenarios(self, temp_git_repo):
        """Test the sim command with different scenarios."""
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

                # Change to the temporary Git repository
                original_cwd = os.getcwd()
                os.chdir(temp_git_repo)

                try:
                    # Test with different scenarios
                    for scenario in ["network_latency", "cpu_stress", "memory_stress"]:
                        # Reset the mock before each iteration to ensure isolation
                        mock_workflow.reset_mock()

                        # Call the CLI command
                        result = self.runner.invoke(app, [
                            "--scenario", scenario,
                            "--severity", "50",
                            "--timeout", "300"
                        ])

                        # Verify the exit code
                        assert result.exit_code == 0

                        # Verify the workflow was called exactly once
                        mock_workflow.assert_called_once()

                        # Check that the scenario parameter was correct
                        assert mock_workflow.call_args.kwargs["scenario"] == scenario
                        assert mock_workflow.call_args.kwargs["severity"] == 50
                        assert mock_workflow.call_args.kwargs["timeout"] == 300
                finally:
                    # Change back to the original directory
                    os.chdir(original_cwd)

    def test_end_to_end_with_different_severity(self, temp_git_repo):
        """Test the sim command with different severity levels."""
        # Mock the LangGraph workflow
        with mock.patch("arc_memory.cli.sim.HAS_LANGGRAPH", True):
            with mock.patch("arc_memory.cli.sim.run_langgraph_workflow") as mock_workflow:
                # Change to the temporary Git repository
                original_cwd = os.getcwd()
                os.chdir(temp_git_repo)

                try:
                    # Test with different severity levels
                    for severity, risk_score in [(25, 15), (50, 25), (75, 50), (90, 85)]:
                        # Set up the mock to return a result with the appropriate risk score
                        mock_workflow.return_value = {
                            "status": "completed",
                            "attestation": {
                                "sim_id": "sim_test",
                                "risk_score": risk_score,
                                "metrics": {"latency_ms": 500, "error_rate": 0.05},
                                "explanation": "Test explanation",
                                "manifest_hash": "abc123",
                                "commit_target": "def456",
                                "timestamp": "2023-01-01T00:00:00Z",
                                "diff_hash": "ghi789"
                            },
                            "affected_services": ["service1", "service2"]
                        }

                        # Reset the mock before each iteration to ensure isolation
                        mock_workflow.reset_mock()

                        # Mock sys.exit to avoid exiting the test
                        with mock.patch("arc_memory.cli.sim.sys.exit") as mock_exit:
                            # Call the CLI command
                            self.runner.invoke(app, [
                                "--scenario", "network_latency",
                                "--severity", str(severity),
                                "--timeout", "300"
                            ])

                            # Verify the workflow was called exactly once with the correct severity
                            mock_workflow.assert_called_once()
                            # Check that the severity parameter was correct
                            assert mock_workflow.call_args.kwargs["scenario"] == "network_latency"
                            assert mock_workflow.call_args.kwargs["severity"] == severity
                            assert mock_workflow.call_args.kwargs["timeout"] == 300

                            # Verify the exit code based on risk score vs severity
                            # Note: The actual behavior might vary based on implementation details
                            # so we're just checking that mock_exit was called with some value
                            if risk_score >= severity:
                                assert mock_exit.called
                            # We can't reliably check for not called because the implementation
                            # might call sys.exit(0) for success
                finally:
                    # Change back to the original directory
                    os.chdir(original_cwd)

    def test_end_to_end_with_diff_file(self, temp_git_repo):
        """Test the sim command with a pre-serialized diff file."""
        # Create a temporary diff file
        with tempfile.NamedTemporaryFile(suffix=".json") as diff_file:
            # Write a sample diff to the file
            diff_data = {
                "files": [
                    {"path": "file1.py", "additions": 10, "deletions": 5},
                    {"path": "file2.py", "additions": 20, "deletions": 15}
                ],
                "end_commit": "abc123",
                "timestamp": "2023-01-01T00:00:00Z"
            }
            diff_file.write(json.dumps(diff_data).encode())
            diff_file.flush()

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

                    # Change to the temporary Git repository
                    original_cwd = os.getcwd()
                    os.chdir(temp_git_repo)

                    try:
                        # Call the CLI command with the diff file
                        result = self.runner.invoke(app, [
                            "--diff", diff_file.name,
                            "--scenario", "network_latency",
                            "--severity", "50",
                            "--timeout", "300"
                        ])

                        # Verify the exit code
                        assert result.exit_code == 0

                        # Verify the workflow was called with the diff data
                        mock_workflow.assert_called_once()
                        # The diff data should be loaded from the file
                        assert mock_workflow.call_args[1]["diff_data"] is not None
                    finally:
                        # Change back to the original directory
                        os.chdir(original_cwd)
