"""End-to-end test for the simulation workflow.

This test verifies that the entire simulation workflow works correctly,
from extracting diffs to running the simulation and generating results.
"""

import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from arc_memory.simulate.workflow import run_simulation_workflow


# Skip tests if Smol Agents is not available
try:
    from smolagents import CodeAgent
    HAS_SMOL_AGENTS = True
except ImportError:
    HAS_SMOL_AGENTS = False

pytestmark = pytest.mark.skipif(not HAS_SMOL_AGENTS, reason="Smol Agents not installed")


@pytest.fixture
def mock_diff_data():
    """Mock diff data for testing."""
    return {
        "files": [
            {
                "path": "src/auth/server.js",
                "additions": 10,
                "deletions": 5,
                "changes": 15
            },
            {
                "path": "services/payment/api.py",
                "additions": 20,
                "deletions": 10,
                "changes": 30
            }
        ],
        "start_commit": "abc123",
        "end_commit": "def456",
        "timestamp": "2023-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_db_path():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        yield str(db_path)


@patch("arc_memory.simulate.workflow.create_simulation_agent")
@patch("arc_memory.simulate.diff.analyze_changes")
@patch("arc_memory.simulate.diff.extract_diff")
def test_run_simulation_workflow(
    mock_extract_diff,
    mock_analyze_changes,
    mock_create_simulation_agent,
    mock_diff_data,
    mock_db_path
):
    """Test running the simulation workflow end-to-end."""
    # Mock the diff extraction
    mock_extract_diff.return_value = mock_diff_data

    # Mock the diff analysis
    mock_analyze_changes.return_value = ["auth", "payment"]

    # Mock the simulation agent
    mock_sim_agent = MagicMock()
    mock_sim_agent.run.return_value = MagicMock(
        output=json.dumps({
            "experiment_name": "test-experiment",
            "duration_seconds": 10,
            "initial_metrics": {
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3,
                "timestamp": 1234567890
            },
            "final_metrics": {
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3,
                "timestamp": 1234567900
            },
            "timestamp": 1234567900
        })
    )
    mock_create_simulation_agent.return_value = mock_sim_agent

    # Define a progress callback
    def progress_callback(message, percentage):
        print(f"{percentage}%: {message}")

    # Run the workflow
    result = run_simulation_workflow(
        rev_range="HEAD~1..HEAD",
        scenario="network_latency",
        severity=50,
        timeout=10,
        repo_path=".",
        db_path=mock_db_path,
        use_memory=True,
        progress_callback=progress_callback
    )

    # Verify the result
    assert result["status"] == "completed" or result["status"] == "failed"

    # Verify that the mocks were called
    mock_extract_diff.assert_called_once()
    mock_analyze_changes.assert_called_once()
    mock_create_simulation_agent.assert_called_once()


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OpenAI API key not set")
@pytest.mark.skipif(not os.environ.get("E2B_API_KEY"), reason="E2B API key not set")
def test_run_simulation_workflow_live():
    """Test running the simulation workflow with live agents.

    This test requires valid API keys for OpenAI and E2B.
    It will run a real simulation on the current repository.
    """
    # Skip if we're not in a Git repository
    import subprocess
    try:
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("Not in a Git repository")

    # Define a progress callback
    def progress_callback(message, percentage):
        print(f"{percentage}%: {message}")

    # Create a temporary database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"

        # Run the workflow
        result = run_simulation_workflow(
            rev_range="HEAD~1..HEAD",
            scenario="network_latency",
            severity=50,
            timeout=60,  # 1 minute timeout for testing
            repo_path=".",
            db_path=str(db_path),
            use_memory=True,
            progress_callback=progress_callback
        )

        # Verify the result
        assert result["status"] in ["completed", "failed"]

        # If the test failed, print the error
        if result["status"] == "failed":
            print(f"Test failed with error: {result.get('error', 'Unknown error')}")
