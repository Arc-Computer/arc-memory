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
                memory=False,
                model_name="gpt-4o",
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
                memory=False,
                model_name="gpt-4o",
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
                    memory=False,
                    model_name="gpt-4o",
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
                    memory=False,
                    model_name="gpt-4o",
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
                memory=False,
                model_name="gpt-4o",
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

    def test_run_simulation_with_smol_agents(self):
        """Test run_simulation with Smol Agents workflow."""
        # Mock the Smol Agents workflow
        with mock.patch("arc_memory.cli.sim.HAS_SMOL_AGENTS", True):
            with mock.patch("arc_memory.cli.sim.run_smol_workflow") as mock_workflow:
                # Set up the mock to return a successful result
                mock_workflow.return_value = {
                    "success": True,
                    "attestation": {
                        "sim_id": "sim_test",
                        "risk_score": 25,
                        "severity": 50,
                        "scenario": "network_latency",
                        "metrics": {"latency_ms": 500, "error_rate": 0.05},
                        "explanation": "Test explanation",
                        "manifest_hash": "abc123",
                        "commit_target": "def456",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "diff_hash": "ghi789",
                        "rev_range": "HEAD~1..HEAD"
                    },
                    "affected_services": ["service1", "service2"],
                    "command_logs": []
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
                            timeout=600,
                            model_name="gpt-4o"
                        )

                        # Verify the workflow was called with the expected arguments
                        mock_workflow.assert_called_once_with(
                            rev_range="HEAD~1..HEAD",
                            scenario="network_latency",
                            severity=50,
                            timeout=600,
                            repo_path=os.getcwd(),
                            db_path=mock.ANY,
                            diff_data=None,
                            use_memory=False,
                            model_name="gpt-4o",
                            verbose=False
                        )

    def test_run_simulation_with_smol_agents_high_risk(self):
        """Test run_simulation with Smol Agents workflow and high risk score."""
        # Mock the Smol Agents workflow
        with mock.patch("arc_memory.cli.sim.HAS_SMOL_AGENTS", True):
            with mock.patch("arc_memory.cli.sim.run_smol_workflow") as mock_workflow:
                # Set up the mock to return a result with high risk score
                mock_workflow.return_value = {
                    "success": True,
                    "attestation": {
                        "sim_id": "sim_test",
                        "risk_score": 75,  # Higher than severity threshold
                        "severity": 50,
                        "scenario": "network_latency",
                        "metrics": {"latency_ms": 500, "error_rate": 0.05},
                        "explanation": "Test explanation",
                        "manifest_hash": "abc123",
                        "commit_target": "def456",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "diff_hash": "ghi789",
                        "rev_range": "HEAD~1..HEAD"
                    },
                    "affected_services": ["service1", "service2"],
                    "command_logs": []
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
                            timeout=600,
                            model_name="gpt-4o"
                        )

                        # Verify sys.exit was called with exit code 1 (risk score > severity)
                        mock_exit.assert_called_once_with(1)

    def test_run_simulation_with_smol_agents_failure(self):
        """Test run_simulation with Smol Agents workflow failure."""
        # Mock the Smol Agents workflow
        with mock.patch("arc_memory.cli.sim.HAS_SMOL_AGENTS", True):
            with mock.patch("arc_memory.cli.sim.run_smol_workflow") as mock_workflow:
                # Set up the mock to return a failed result
                mock_workflow.return_value = {
                    "success": False,
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
                            timeout=600,
                            model_name="gpt-4o"
                        )

                        # Verify sys.exit was called with exit code 2 (error)
                        mock_exit.assert_called_once_with(2)

    def test_run_simulation_without_smol_agents(self):
        """Test run_simulation without Smol Agents workflow."""
        # Mock the Smol Agents availability
        with mock.patch("arc_memory.cli.sim.HAS_SMOL_AGENTS", False):
            # Mock the console.print to avoid output during tests
            with mock.patch("arc_memory.cli.sim.console.print"):
                # Mock sys.exit to avoid exiting the test
                with mock.patch("arc_memory.cli.sim.sys.exit") as mock_exit:
                    # Call the run_simulation function
                    run_simulation(
                        rev_range="HEAD~1..HEAD",
                        scenario="network_latency",
                        severity=50,
                        timeout=600,
                        model_name="gpt-4o"
                    )

                    # Verify sys.exit was called with exit code 2 (error)
                    mock_exit.assert_called_once_with(2)
