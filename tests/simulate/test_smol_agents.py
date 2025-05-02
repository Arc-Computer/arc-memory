"""Tests for Smol Agents integration in Arc Memory simulation."""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from arc_memory.simulate.agents.diff_agent import create_diff_agent, analyze_diff_with_agent
from arc_memory.simulate.agents.sandbox_agent import create_sandbox_agent, run_sandbox_tests_with_agent


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
        ]
    }


@pytest.fixture
def mock_manifest_data(mock_diff_data, tmp_path):
    """Mock manifest data for testing."""
    # Save the diff data to a file
    diff_path = tmp_path / "diff.json"
    with open(diff_path, 'w') as f:
        json.dump(mock_diff_data, f, indent=2)
    
    # Create a mock causal graph
    causal_graph = {
        "service_to_files": {
            "auth": ["src/auth/server.js"],
            "payment": ["services/payment/api.py"]
        },
        "file_to_services": {
            "src/auth/server.js": ["auth"],
            "services/payment/api.py": ["payment"]
        }
    }
    
    # Save the causal graph to a file
    causal_path = tmp_path / "causal.json"
    with open(causal_path, 'w') as f:
        json.dump(causal_graph, f, indent=2)
    
    # Create the manifest
    manifest = {
        "scenario": "network_latency",
        "severity": 50,
        "affected_services": ["auth", "payment"],
        "diff_path": str(diff_path),
        "causal_path": str(causal_path),
        "output_dir": str(tmp_path)
    }
    
    # Save the manifest to a file
    manifest_path = tmp_path / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return {
        "manifest": manifest,
        "manifest_path": str(manifest_path),
        "diff_path": str(diff_path),
        "causal_path": str(causal_path)
    }


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OpenAI API key not set")
def test_create_diff_agent():
    """Test creating a diff agent."""
    agent = create_diff_agent()
    assert agent is not None
    assert isinstance(agent, CodeAgent)


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OpenAI API key not set")
def test_create_sandbox_agent():
    """Test creating a sandbox agent."""
    agent = create_sandbox_agent()
    assert agent is not None
    assert isinstance(agent, CodeAgent)


@patch("arc_memory.simulate.agents.diff_agent.CodeAgent")
def test_analyze_diff_with_agent(mock_code_agent, mock_diff_data):
    """Test analyzing a diff with an agent."""
    # Create a mock agent
    mock_agent = MagicMock()
    mock_agent.run.return_value = MagicMock(output='["auth", "payment"]')
    mock_code_agent.return_value = mock_agent
    
    # Create the agent
    agent = create_diff_agent()
    
    # Analyze the diff
    affected_services = analyze_diff_with_agent(agent, mock_diff_data, "mock_db_path")
    
    # Check the results
    assert affected_services == ["auth", "payment"]
    assert mock_agent.run.called


@patch("arc_memory.simulate.agents.sandbox_agent.CodeAgent")
def test_run_sandbox_tests_with_agent(mock_code_agent, mock_manifest_data):
    """Test running sandbox tests with an agent."""
    # Create a mock agent
    mock_agent = MagicMock()
    mock_agent.run.return_value = MagicMock(
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
    mock_code_agent.return_value = mock_agent
    
    # Create the agent
    agent = create_sandbox_agent()
    
    # Run the sandbox tests
    results = run_sandbox_tests_with_agent(agent, mock_manifest_data["manifest_path"], duration_seconds=10)
    
    # Check the results
    assert results["experiment_name"] == "test-experiment"
    assert results["duration_seconds"] == 10
    assert "initial_metrics" in results
    assert "final_metrics" in results
    assert mock_agent.run.called
