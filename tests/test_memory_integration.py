"""Tests for memory integration in Arc Memory simulation.

This module tests the memory integration features of Arc Memory simulation,
including storing simulation results in memory and enhancing explanations with
historical context.
"""

import os
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from arc_memory.simulate.memory import (
    store_simulation_in_memory,
    get_relevant_simulations,
    enhance_explanation
)


@pytest.fixture
def mock_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
        yield temp_db.name


@pytest.fixture
def mock_attestation():
    """Create a mock attestation for testing."""
    return {
        "sim_id": "sim_test_1",
        "rev_range": "HEAD~1..HEAD",
        "scenario": "network_latency",
        "severity": 50,
        "risk_score": 25,
        "manifest_hash": "abc123",
        "commit_target": "abcdef123456",
        "diff_hash": "def456",
        "explanation": "Test explanation",
        "timestamp": "2023-01-01T12:00:00Z"
    }


@pytest.fixture
def mock_metrics():
    """Create mock metrics for testing."""
    return {
        "latency_ms": 500,
        "error_rate": 0.05,
        "cpu_usage": {
            "node1": 0.75
        },
        "memory_usage": {
            "node1": 0.5
        }
    }


@pytest.fixture
def mock_diff_data():
    """Create mock diff data for testing."""
    return {
        "files": [
            {
                "path": "src/api/server.py",
                "additions": 10,
                "deletions": 5
            },
            {
                "path": "src/auth/login.py",
                "additions": 3,
                "deletions": 2
            }
        ],
        "end_commit": "abcdef123456",
        "timestamp": "2023-01-01T12:00:00Z"
    }


@mock.patch("arc_memory.memory.integration.store_simulation_results")
def test_store_simulation_in_memory(mock_store, mock_db_path, mock_attestation, mock_metrics, mock_diff_data):
    """Test storing simulation results in memory."""
    # Mock the return value of store_simulation_results
    mock_sim_node = mock.MagicMock()
    mock_sim_node.sim_id = "sim_test_1"
    mock_store.return_value = (mock_sim_node, [])
    
    # Call the function
    result = store_simulation_in_memory(
        rev_range=mock_attestation["rev_range"],
        scenario=mock_attestation["scenario"],
        severity=mock_attestation["severity"],
        risk_score=mock_attestation["risk_score"],
        affected_services=["api-service", "auth-service"],
        metrics=mock_metrics,
        explanation=mock_attestation["explanation"],
        attestation=mock_attestation,
        diff_data=mock_diff_data,
        db_path=mock_db_path
    )
    
    # Check the result
    assert result is not None
    assert result.sim_id == "sim_test_1"
    
    # Check that store_simulation_results was called with the right arguments
    mock_store.assert_called_once()
    args, kwargs = mock_store.call_args
    assert kwargs["sim_id"] == "sim_test_1"
    assert kwargs["scenario"] == "network_latency"
    assert kwargs["severity"] == 50
    assert kwargs["risk_score"] == 25


@pytest.mark.skip(reason="Memory integration needs to be updated for Smol Agents")
@mock.patch("arc_memory.memory.integration.retrieve_relevant_simulations")
def test_get_relevant_simulations(mock_retrieve, mock_db_path):
    """Test retrieving relevant simulations."""
    # Mock the return value of retrieve_relevant_simulations
    mock_retrieve.return_value = [
        {
            "sim_id": "sim_test_1",
            "scenario": "network_latency",
            "severity": 50,
            "risk_score": 25,
            "affected_services": ["api-service"],
            "explanation": "Test explanation 1",
            "timestamp": "2023-01-01T12:00:00Z"
        },
        {
            "sim_id": "sim_test_2",
            "scenario": "network_latency",
            "severity": 60,
            "risk_score": 30,
            "affected_services": ["api-service", "auth-service"],
            "explanation": "Test explanation 2",
            "timestamp": "2023-01-02T12:00:00Z"
        }
    ]
    
    # Call the function
    result = get_relevant_simulations(
        affected_services=["api-service"],
        scenario="network_latency",
        severity=50,
        limit=5,
        db_path=mock_db_path
    )
    
    # Check the result
    assert len(result) == 2
    assert result[0]["sim_id"] == "sim_test_1"
    assert result[1]["sim_id"] == "sim_test_2"
    
    # Check that retrieve_relevant_simulations was called with the right arguments
    mock_retrieve.assert_called_once_with(
        db_path=mock_db_path,
        affected_services=["api-service"],
        scenario="network_latency",
        severity_range=(30, 70),
        limit=5
    )


@pytest.mark.skip(reason="Memory integration needs to be updated for Smol Agents")
@mock.patch("arc_memory.memory.integration.retrieve_relevant_simulations")
def test_enhance_explanation(mock_retrieve, mock_db_path):
    """Test enhancing explanation with historical context."""
    # Mock the return value of retrieve_relevant_simulations
    mock_retrieve.return_value = [
        {
            "sim_id": "sim_test_1",
            "scenario": "network_latency",
            "severity": 50,
            "risk_score": 25,
            "affected_services": ["api-service"],
            "explanation": "Test explanation 1",
            "timestamp": "2023-01-01T12:00:00Z"
        },
        {
            "sim_id": "sim_test_2",
            "scenario": "network_latency",
            "severity": 60,
            "risk_score": 30,
            "affected_services": ["api-service", "auth-service"],
            "explanation": "Test explanation 2",
            "timestamp": "2023-01-02T12:00:00Z"
        }
    ]
    
    # Call the function
    original_explanation = "This is a test explanation."
    result = enhance_explanation(
        explanation=original_explanation,
        affected_services=["api-service"],
        scenario="network_latency",
        severity=50,
        risk_score=40,
        db_path=mock_db_path
    )
    
    # Check the result
    assert result != original_explanation
    assert "Historical Context" in result
    assert "higher risk (40) than similar changes in the past" in result
    assert "Simulation sim_test_1" in result
    assert "Simulation sim_test_2" in result
    
    # Check that retrieve_relevant_simulations was called with the right arguments
    mock_retrieve.assert_called_once_with(
        db_path=mock_db_path,
        affected_services=["api-service"],
        scenario="network_latency",
        severity=50
    )


@pytest.mark.skip(reason="Memory integration needs to be updated for Smol Agents")
def test_enhance_explanation_no_relevant_simulations():
    """Test enhancing explanation with no relevant simulations."""
    # Call the function with a mock that returns an empty list
    with mock.patch("arc_memory.memory.integration.retrieve_relevant_simulations", return_value=[]):
        original_explanation = "This is a test explanation."
        result = enhance_explanation(
            explanation=original_explanation,
            affected_services=["api-service"],
            scenario="network_latency",
            severity=50,
            risk_score=40,
            db_path="mock_db_path"
        )
        
        # Check that the original explanation is returned unchanged
        assert result == original_explanation
