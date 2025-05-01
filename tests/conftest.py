"""Pytest configuration file."""

import os
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# For CI environments, we need to handle the case when there's no .env file
# GitHub Actions sets GITHUB_TOKEN automatically, so we can use that
if "GITHUB_TOKEN" not in os.environ and "GITHUB_ACTIONS" in os.environ:
    # In GitHub Actions, the GITHUB_TOKEN is available as a secret
    # and is automatically set in the environment
    print("Running in GitHub Actions environment, using GITHUB_TOKEN from secrets")

    # If we're in CI and there's no GITHUB_TOKEN, we can skip GitHub tests
    if "GITHUB_TOKEN" not in os.environ:
        print("No GITHUB_TOKEN found in environment, GitHub tests will be skipped")

        # We can also set a dummy token to avoid errors in tests that expect a token
        # but will be skipped due to the pytestmark
        os.environ["GITHUB_TOKEN"] = "dummy_token_for_skipped_tests"


# Simulation test fixtures

@pytest.fixture
def sample_diff():
    """Return a sample diff for testing."""
    return {
        "files": [
            {"path": "file1.py", "additions": 10, "deletions": 5, "content": "def hello():\n    return 'world'"},
            {"path": "file2.py", "additions": 20, "deletions": 15, "content": "def goodbye():\n    return 'farewell'"}
        ],
        "end_commit": "abc123",
        "timestamp": "2023-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_causal_graph():
    """Return a sample causal graph for testing."""
    return {
        "nodes": ["service1", "service2", "service3"],
        "edges": [
            {"source": "service1", "target": "service2"},
            {"source": "service2", "target": "service3"}
        ]
    }


@pytest.fixture
def sample_manifest():
    """Return a sample manifest for testing."""
    return {
        "kind": "NetworkChaos",
        "metadata": {
            "name": "test-experiment",
            "annotations": {
                "arc-memory.io/manifest-hash": "abc123"
            }
        },
        "spec": {
            "selector": {
                "namespaces": ["default"],
                "labelSelectors": {
                    "app": "service1"
                }
            },
            "mode": "one",
            "action": "delay",
            "delay": {
                "latency": "500ms",
                "correlation": "100",
                "jitter": "0ms"
            },
            "duration": "60s"
        }
    }


@pytest.fixture
def sample_metrics():
    """Return a sample metrics dictionary for testing."""
    return {
        "latency_ms": 500,
        "error_rate": 0.05,
        "node_count": 1,
        "pod_count": 5,
        "service_count": 3,
        "cpu_usage": {
            "service1": 0.5,
            "service2": 0.7,
            "service3": 0.3
        },
        "memory_usage": {
            "service1": 200,
            "service2": 300,
            "service3": 100
        }
    }


@pytest.fixture
def sample_simulation_results():
    """Return a sample simulation results dictionary for testing."""
    return {
        "experiment_name": "test-experiment",
        "duration_seconds": 60,
        "initial_metrics": {
            "node_count": 1,
            "pod_count": 5,
            "service_count": 3
        },
        "final_metrics": {
            "node_count": 1,
            "pod_count": 5,
            "service_count": 3,
            "cpu_usage": {
                "service1": 0.5,
                "service2": 0.7,
                "service3": 0.3
            },
            "memory_usage": {
                "service1": 200,
                "service2": 300,
                "service3": 100
            },
            "latency_ms": 500,
            "error_rate": 0.05
        },
        "metrics_history": [
            {
                "timestamp": "2023-01-01T00:00:00Z",
                "cpu_usage": {
                    "service1": 0.3,
                    "service2": 0.4,
                    "service3": 0.2
                },
                "memory_usage": {
                    "service1": 150,
                    "service2": 200,
                    "service3": 80
                }
            },
            {
                "timestamp": "2023-01-01T00:00:30Z",
                "cpu_usage": {
                    "service1": 0.5,
                    "service2": 0.7,
                    "service3": 0.3
                },
                "memory_usage": {
                    "service1": 200,
                    "service2": 300,
                    "service3": 100
                }
            }
        ]
    }


@pytest.fixture
def sample_attestation():
    """Return a sample attestation for testing."""
    return {
        "sim_id": "sim_test",
        "version": "1.0",
        "rev_range": "HEAD~1..HEAD",
        "scenario": "network_latency",
        "severity": 50,
        "affected_services": ["service1", "service2"],
        "metrics": {
            "latency_ms": 500,
            "error_rate": 0.05
        },
        "risk_score": 25,
        "explanation": "Test explanation",
        "manifest_hash": "abc123",
        "commit_target": "def456",
        "timestamp": "2023-01-01T00:00:00Z",
        "diff_hash": "ghi789",
        "signature": {
            "algorithm": "hmac-sha256",
            "value": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "timestamp": "2023-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def temp_diff_file(request):
    """Create a temporary diff file for testing."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)

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
    temp_file.close()

    # Register cleanup as a finalizer
    file_path = temp_file.name
    def cleanup():
        if os.path.exists(file_path):
            os.unlink(file_path)
    request.addfinalizer(cleanup)

    return Path(file_path)


@pytest.fixture
def mock_e2b_handle():
    """Create a mock E2B handle for testing."""
    with mock.patch("arc_memory.simulate.code_interpreter.E2BCodeInterpreter") as mock_e2b:
        mock_instance = mock.MagicMock()
        mock_instance.run_command.return_value = {
            "exit_code": 0,
            "stdout": "Test output",
            "stderr": ""
        }
        mock_instance.write_file.return_value = None
        mock_instance.read_file.return_value = "Test file content"
        mock_instance.file_exists.return_value = True
        mock_instance.list_files.return_value = ["/path/to/file1.txt", "/path/to/file2.txt"]
        mock_instance.create_directory.return_value = None
        mock_instance.close.return_value = None

        mock_e2b.return_value = mock_instance
        yield mock_instance
