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

    @pytest.mark.skip(reason="Using Smol Agents instead of LangGraph")
    def test_end_to_end_with_langgraph(self, temp_git_repo):
        """Test the full workflow from CLI to output with LangGraph."""
        pass

    @pytest.mark.skip(reason="Using Smol Agents instead of LangGraph")
    def test_end_to_end_with_different_scenarios(self, temp_git_repo):
        """Test the sim command with different scenarios."""
        pass

    @pytest.mark.skip(reason="Using Smol Agents instead of LangGraph")
    def test_end_to_end_with_different_severity(self, temp_git_repo):
        """Test the sim command with different severity levels."""
        pass

    @pytest.mark.skip(reason="Using Smol Agents instead of LangGraph")
    def test_end_to_end_with_diff_file(self, temp_git_repo):
        """Test the sim command with a pre-serialized diff file."""
        pass

    def test_end_to_end_with_smol_agents(self, temp_git_repo):
        """Test the full workflow from CLI to output with Smol Agents."""
        # Mock the Smol Agents workflow
        with mock.patch("arc_memory.cli.sim.run_simulation_with_smol_agents") as mock_workflow:
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
                # Use the temporary Git repository as the working directory
                # without actually changing the current directory
                with mock.patch("os.getcwd", return_value=temp_git_repo):
                    # Mock the run_simulation function to use the temp_git_repo
                    with mock.patch("arc_memory.cli.sim.os.getcwd", return_value=temp_git_repo):
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
