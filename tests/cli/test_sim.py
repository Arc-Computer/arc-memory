"""Tests for the sim CLI command."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from arc_memory.cli.sim import app, run_simulation


class TestSimCLI:
    """Tests for the sim CLI command."""

    runner = CliRunner()

    def test_sim_command_basic(self):
        """Test basic sim command with default options."""
        # Mock the run_simulation function
        with mock.patch("arc_memory.cli.sim.run_simulation") as mock_run_sim:
            # Call the CLI command with default options
            result = self.runner.invoke(app, [])

            # Verify the function was called with default arguments
            mock_run_sim.assert_called_once_with(
                rev_range="HEAD~1..HEAD",
                diff_path=None,
                scenario="network_latency",
                severity=50,
                timeout=600,
                output_path=None,
                open_ui=False,
                verbose=False,
                debug=False,
            )

            # Verify the exit code
            assert result.exit_code == 0

    def test_sim_command_with_rev_range(self):
        """Test sim command with custom rev-range."""
        # Mock the run_simulation function
        with mock.patch("arc_memory.cli.sim.run_simulation") as mock_run_sim:
            # Call the CLI command with custom rev-range
            result = self.runner.invoke(app, ["--rev-range", "HEAD~3..HEAD"])

            # Verify the function was called with the custom rev-range
            mock_run_sim.assert_called_once_with(
                rev_range="HEAD~3..HEAD",
                diff_path=None,
                scenario="network_latency",
                severity=50,
                timeout=600,
                output_path=None,
                open_ui=False,
                verbose=False,
                debug=False,
            )

            # Verify the exit code
            assert result.exit_code == 0

    def test_sim_command_with_diff_file(self):
        """Test sim command with pre-serialized diff file."""
        # Create a temporary diff file
        with tempfile.NamedTemporaryFile(suffix=".json") as temp_file:
            # Write a sample diff to the file
            diff_data = {
                "files": [
                    {"path": "file1.py", "additions": 10, "deletions": 5},
                    {"path": "file2.py", "additions": 20, "deletions": 15}
                ],
                "end_commit": "abc123",
                "timestamp": "2023-01-01T00:00:00Z"
            }
            temp_file.write(json.dumps(diff_data).encode())
            temp_file.flush()

            # Mock the run_simulation function
            with mock.patch("arc_memory.cli.sim.run_simulation") as mock_run_sim:
                # Call the CLI command with the diff file
                result = self.runner.invoke(app, ["--diff", temp_file.name])

                # Verify the function was called with the diff file
                mock_run_sim.assert_called_once_with(
                    rev_range="HEAD~1..HEAD",
                    diff_path=Path(temp_file.name),
                    scenario="network_latency",
                    severity=50,
                    timeout=600,
                    output_path=None,
                    open_ui=False,
                    verbose=False,
                    debug=False,
                )

                # Verify the exit code
                assert result.exit_code == 0

    def test_sim_command_with_output_file(self):
        """Test sim command with output file."""
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".json") as temp_file:
            # Mock the run_simulation function
            with mock.patch("arc_memory.cli.sim.run_simulation") as mock_run_sim:
                # Call the CLI command with the output file
                result = self.runner.invoke(app, ["--output", temp_file.name])

                # Verify the function was called with the output file
                mock_run_sim.assert_called_once_with(
                    rev_range="HEAD~1..HEAD",
                    diff_path=None,
                    scenario="network_latency",
                    severity=50,
                    timeout=600,
                    output_path=Path(temp_file.name),
                    open_ui=False,
                    verbose=False,
                    debug=False,
                )

                # Verify the exit code
                assert result.exit_code == 0

    def test_sim_command_with_all_options(self):
        """Test sim command with all options."""
        # Mock the run_simulation function
        with mock.patch("arc_memory.cli.sim.run_simulation") as mock_run_sim:
            # Call the CLI command with all options
            result = self.runner.invoke(app, [
                "--rev-range", "HEAD~3..HEAD",
                "--scenario", "cpu_stress",
                "--severity", "75",
                "--timeout", "300",
                "--open-ui",
                "--verbose",
                "--debug"
            ])

            # Verify the function was called with all options
            mock_run_sim.assert_called_once_with(
                rev_range="HEAD~3..HEAD",
                diff_path=None,
                scenario="cpu_stress",
                severity=75,
                timeout=300,
                output_path=None,
                open_ui=True,
                verbose=True,
                debug=True,
            )

            # Verify the exit code
            assert result.exit_code == 0

    def test_sim_command_list_scenarios(self):
        """Test the list-scenarios subcommand."""
        # Mock the list_available_scenarios function
        with mock.patch("arc_memory.cli.sim.list_available_scenarios") as mock_list_scenarios:
            # Set up the mock to return some scenarios
            mock_list_scenarios.return_value = [
                {"id": "network_latency", "description": "Network latency between services"},
                {"id": "cpu_stress", "description": "CPU stress on services"}
            ]

            # Call the list-scenarios subcommand
            result = self.runner.invoke(app, ["list-scenarios"])

            # Verify the function was called
            mock_list_scenarios.assert_called_once()

            # Verify the output contains the scenario information
            assert "network_latency" in result.stdout
            assert "Network latency between services" in result.stdout
            assert "cpu_stress" in result.stdout
            assert "CPU stress on services" in result.stdout

            # Verify the exit code
            assert result.exit_code == 0

    def test_run_simulation_with_langgraph(self):
        """Test run_simulation with LangGraph workflow."""
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

                # Mock the console.print to avoid output during tests
                with mock.patch("arc_memory.cli.sim.console.print"):
                    # Mock sys.exit to avoid exiting the test
                    with mock.patch("arc_memory.cli.sim.sys.exit") as mock_exit:
                        # Call the run_simulation function
                        run_simulation(
                            rev_range="HEAD~1..HEAD",
                            scenario="network_latency",
                            severity=50,
                            timeout=600
                        )

                        # Verify the workflow was called with the expected arguments
                        mock_workflow.assert_called_once_with(
                            rev_range="HEAD~1..HEAD",
                            scenario="network_latency",
                            severity=50,
                            timeout=600,
                            repo_path=os.getcwd(),
                            db_path=mock.ANY,
                            diff_data=None
                        )

                        # Verify sys.exit was not called (risk score < severity)
                        mock_exit.assert_not_called()

    def test_run_simulation_with_langgraph_high_risk(self):
        """Test run_simulation with LangGraph workflow and high risk score."""
        # Mock the LangGraph workflow
        with mock.patch("arc_memory.cli.sim.HAS_LANGGRAPH", True):
            with mock.patch("arc_memory.cli.sim.run_langgraph_workflow") as mock_workflow:
                # Set up the mock to return a result with high risk score
                mock_workflow.return_value = {
                    "status": "completed",
                    "attestation": {
                        "sim_id": "sim_test",
                        "risk_score": 75,  # Higher than severity threshold
                        "metrics": {"latency_ms": 500, "error_rate": 0.05},
                        "explanation": "Test explanation",
                        "manifest_hash": "abc123",
                        "commit_target": "def456",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "diff_hash": "ghi789"
                    },
                    "affected_services": ["service1", "service2"]
                }

                # Mock the console.print to avoid output during tests
                with mock.patch("arc_memory.cli.sim.console.print"):
                    # Mock sys.exit to avoid exiting the test
                    with mock.patch("arc_memory.cli.sim.sys.exit") as mock_exit:
                        # Call the run_simulation function
                        run_simulation(
                            rev_range="HEAD~1..HEAD",
                            scenario="network_latency",
                            severity=50,
                            timeout=600
                        )

                        # Verify sys.exit was called with exit code 1 (risk score > severity)
                        mock_exit.assert_called_once_with(1)

    def test_run_simulation_with_langgraph_failure(self):
        """Test run_simulation with LangGraph workflow failure."""
        # Mock the LangGraph workflow
        with mock.patch("arc_memory.cli.sim.HAS_LANGGRAPH", True):
            with mock.patch("arc_memory.cli.sim.run_langgraph_workflow") as mock_workflow:
                # Set up the mock to return a failed result
                mock_workflow.return_value = {
                    "status": "failed",
                    "error": "Test error"
                }

                # Mock the console.print to avoid output during tests
                with mock.patch("arc_memory.cli.sim.console.print"):
                    # Mock sys.exit to avoid exiting the test
                    with mock.patch("arc_memory.cli.sim.sys.exit") as mock_exit:
                        # Call the run_simulation function
                        run_simulation(
                            rev_range="HEAD~1..HEAD",
                            scenario="network_latency",
                            severity=50,
                            timeout=600
                        )

                        # Verify sys.exit was called with exit code 2 (error)
                        mock_exit.assert_called_once_with(2)

    def test_run_simulation_without_langgraph(self):
        """Test run_simulation without LangGraph workflow."""
        # Mock the LangGraph availability
        with mock.patch("arc_memory.cli.sim.HAS_LANGGRAPH", False):
            # Mock the traditional approach functions
            with mock.patch("arc_memory.cli.sim.serialize_diff") as mock_serialize_diff:
                with mock.patch("arc_memory.cli.sim.analyze_diff") as mock_analyze_diff:
                    with mock.patch("arc_memory.cli.sim.derive_causal") as mock_derive_causal:
                        with mock.patch("arc_memory.cli.sim.generate_simulation_manifest") as mock_generate_manifest:
                            with mock.patch("arc_memory.cli.sim.run_simulation_and_extract_metrics") as mock_run_sim:
                                # Set up the mocks
                                mock_serialize_diff.return_value = {
                                    "files": [
                                        {"path": "file1.py", "additions": 10, "deletions": 5},
                                        {"path": "file2.py", "additions": 20, "deletions": 15}
                                    ],
                                    "end_commit": "abc123",
                                    "timestamp": "2023-01-01T00:00:00Z"
                                }
                                mock_analyze_diff.return_value = ["service1", "service2"]
                                mock_derive_causal.return_value = {
                                    "nodes": ["service1", "service2"],
                                    "edges": [{"source": "service1", "target": "service2"}]
                                }
                                mock_generate_manifest.return_value = {
                                    "metadata": {
                                        "annotations": {
                                            "arc-memory.io/manifest-hash": "abc123"
                                        }
                                    }
                                }
                                mock_run_sim.return_value = (
                                    {"latency_ms": 500, "error_rate": 0.05},
                                    25  # Risk score
                                )

                                # Mock the console.print to avoid output during tests
                                with mock.patch("arc_memory.cli.sim.console.print"):
                                    # Mock sys.exit to avoid exiting the test
                                    with mock.patch("arc_memory.cli.sim.sys.exit") as mock_exit:
                                        # Call the run_simulation function
                                        run_simulation(
                                            rev_range="HEAD~1..HEAD",
                                            scenario="network_latency",
                                            severity=50,
                                            timeout=600
                                        )

                                        # Verify the functions were called
                                        mock_serialize_diff.assert_called_once_with("HEAD~1..HEAD")
                                        mock_analyze_diff.assert_called_once()
                                        mock_derive_causal.assert_called_once()
                                        mock_generate_manifest.assert_called_once()
                                        mock_run_sim.assert_called_once()

                                        # Verify sys.exit was not called (risk score < severity)
                                        mock_exit.assert_not_called()
