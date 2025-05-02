"""Tests for memory integration with the sim CLI command."""

import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
from pathlib import Path
import json
import typer
from typer.testing import CliRunner
import pytest

from arc_memory.cli.sim import app, history


class TestSimMemoryIntegration(unittest.TestCase):
    """Tests for memory integration with the sim CLI command."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for the test
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")

        # Create a CLI runner
        self.runner = CliRunner()

    def tearDown(self):
        """Clean up after the test."""
        self.temp_dir.cleanup()

    @pytest.mark.skip(reason="Memory integration needs to be updated for Smol Agents")
    @patch("arc_memory.cli.sim.run_langgraph_workflow")
    def test_sim_with_memory_flag(self, mock_run_workflow):
        """Test running a simulation with the --memory flag."""
        # Set up the mock to return a successful result
        mock_run_workflow.return_value = {
            "status": "completed",
            "attestation": {
                "sim_id": "sim_test",
                "risk_score": 35,
                "metrics": {"latency_ms": 250},
                "explanation": "Test explanation",
                "manifest_hash": "abc123",
                "commit_target": "def456",
                "timestamp": "2023-01-01T00:00:00Z",
                "diff_hash": "ghi789",
            },
            "affected_services": ["api-service", "auth-service"],
            "memory": {
                "memory_used": True,
                "similar_simulations_count": 2,
                "simulation_stored": True,
            },
        }

        # Create a temporary output file
        output_file = os.path.join(self.temp_dir.name, "output.json")

        # Run the command with the --memory flag
        with patch("arc_memory.cli.sim.ensure_arc_dir") as mock_ensure_arc_dir:
            # Set up the mock to return the temp directory
            mock_ensure_arc_dir.return_value = Path(self.temp_dir.name)

            # Mock os.getcwd to avoid directory issues
            with patch("os.getcwd", return_value="/tmp"):
                with patch("arc_memory.cli.sim.os.getcwd", return_value="/tmp"):
                    # Run the command
                    result = self.runner.invoke(
                        app,
                        ["--memory", "--output", output_file],
                        catch_exceptions=False,
                    )

        # Check that the command ran successfully
        self.assertEqual(result.exit_code, 0)

        # Check that run_langgraph_workflow was called with use_memory=True
        mock_run_workflow.assert_called_once()
        kwargs = mock_run_workflow.call_args.kwargs
        self.assertTrue(kwargs["use_memory"])

    @patch("arc_memory.cli.sim.get_simulations_by_service")
    @patch("arc_memory.cli.sim.get_connection")
    @patch("arc_memory.cli.sim.ensure_arc_dir")
    def test_history_command_with_service(self, mock_ensure_arc_dir, mock_get_connection, mock_get_simulations):
        """Test the history command with a service filter."""
        # Set up the mocks
        mock_ensure_arc_dir.return_value = Path(self.temp_dir.name)
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn

        # Create mock simulation nodes
        from arc_memory.schema.models import SimulationNode
        from datetime import datetime

        mock_simulations = [
            SimulationNode(
                id="simulation:sim1",
                title="Simulation 1",
                body="Explanation 1",
                ts=datetime(2023, 1, 1),
                sim_id="sim1",
                rev_range="HEAD~1..HEAD",
                scenario="network_latency",
                severity=50,
                risk_score=35,
                manifest_hash="abc123",
                commit_target="def456",
                diff_hash="ghi789",
                affected_services=["api-service", "auth-service"],
            ),
            SimulationNode(
                id="simulation:sim2",
                title="Simulation 2",
                body="Explanation 2",
                ts=datetime(2023, 1, 2),
                sim_id="sim2",
                rev_range="HEAD~2..HEAD",
                scenario="network_latency",
                severity=60,
                risk_score=45,
                manifest_hash="def456",
                commit_target="ghi789",
                diff_hash="jkl012",
                affected_services=["api-service", "db-service"],
            ),
        ]
        mock_get_simulations.return_value = mock_simulations

        # Create a temporary output file
        output_file = os.path.join(self.temp_dir.name, "history.json")

        # Run the history command
        result = self.runner.invoke(
            app,
            ["history", "--service", "api-service", "--output", output_file],
            catch_exceptions=False,
        )

        # Check that the command ran successfully
        self.assertEqual(result.exit_code, 0)

        # Check that get_simulations_by_service was called with the correct arguments
        mock_get_simulations.assert_called_once_with(mock_conn, "api-service", limit=10)

        # Check that the output file was created
        self.assertTrue(os.path.exists(output_file))

        # Check the content of the output file
        with open(output_file, "r") as f:
            output_data = json.load(f)

        # Check that the output contains the expected data
        self.assertEqual(len(output_data), 2)
        self.assertEqual(output_data[0]["sim_id"], "sim1")
        self.assertEqual(output_data[1]["sim_id"], "sim2")

    @patch("arc_memory.cli.sim.get_simulations_by_file")
    @patch("arc_memory.cli.sim.get_connection")
    @patch("arc_memory.cli.sim.ensure_arc_dir")
    def test_history_command_with_file(self, mock_ensure_arc_dir, mock_get_connection, mock_get_simulations):
        """Test the history command with a file filter."""
        # Set up the mocks
        mock_ensure_arc_dir.return_value = Path(self.temp_dir.name)
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn

        # Create mock simulation nodes
        from arc_memory.schema.models import SimulationNode
        from datetime import datetime

        mock_simulations = [
            SimulationNode(
                id="simulation:sim1",
                title="Simulation 1",
                body="Explanation 1",
                ts=datetime(2023, 1, 1),
                sim_id="sim1",
                rev_range="HEAD~1..HEAD",
                scenario="network_latency",
                severity=50,
                risk_score=35,
                manifest_hash="abc123",
                commit_target="def456",
                diff_hash="ghi789",
                affected_services=["api-service"],
            ),
        ]
        mock_get_simulations.return_value = mock_simulations

        # Run the history command
        result = self.runner.invoke(
            app,
            ["history", "--file", "src/api.py"],
            catch_exceptions=False,
        )

        # Check that the command ran successfully
        self.assertEqual(result.exit_code, 0)

        # Check that get_simulations_by_file was called with the correct arguments
        mock_get_simulations.assert_called_once_with(mock_conn, "src/api.py", limit=10)


if __name__ == "__main__":
    unittest.main()
