"""Tests for memory integration with the simulation workflow."""

import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
from pathlib import Path

from arc_memory.simulate.langgraph_flow import (
    run_sim,
    retrieve_memory,
    store_in_memory,
    SimulationState,
)


class TestMemoryIntegration(unittest.TestCase):
    """Tests for memory integration with the simulation workflow."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for the test
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")

        # Create a sample state
        self.state = {
            "rev_range": "HEAD~1..HEAD",
            "scenario": "network_latency",
            "severity": 50,
            "timeout": 60,
            "repo_path": self.temp_dir.name,
            "db_path": self.db_path,
            "use_memory": True,
            "diff_data": {
                "files": [{"path": "src/api.py"}],
                "end_commit": "abc123",
            },
            "affected_services": ["api-service", "auth-service"],
            "metrics": {
                "latency_ms": 250,
                "error_rate": 0.05,
            },
            "risk_score": 35,
            "attestation": {
                "sim_id": "sim_test",
                "rev_range": "HEAD~1..HEAD",
                "scenario": "network_latency",
                "severity": 50,
                "risk_score": 35,
                "manifest_hash": "abc123",
                "commit_target": "def456",
                "diff_hash": "ghi789",
                "explanation": "Test explanation",
            },
            "explanation": "Test explanation",
            "status": "in_progress",
        }

    def tearDown(self):
        """Clean up after the test."""
        self.temp_dir.cleanup()

    def test_retrieve_memory(self):
        """Test retrieving memory in the simulation workflow."""
        # Mock the retrieve_relevant_simulations function
        with patch("arc_memory.simulate.langgraph_flow.retrieve_relevant_simulations") as mock_retrieve:
            # Set up the mock to return some simulations
            mock_retrieve.return_value = [
                {
                    "sim_id": "sim1",
                    "scenario": "network_latency",
                    "severity": 50,
                    "risk_score": 35,
                    "affected_services": ["api-service", "auth-service"],
                    "explanation": "This simulation showed moderate impact on API latency.",
                    "timestamp": "2023-01-01T00:00:00",
                },
                {
                    "sim_id": "sim2",
                    "scenario": "network_latency",
                    "severity": 60,
                    "risk_score": 45,
                    "affected_services": ["api-service", "db-service"],
                    "explanation": "This simulation showed significant impact on database performance.",
                    "timestamp": "2023-01-02T00:00:00",
                },
            ]

            # Call the retrieve_memory function
            result = retrieve_memory(self.state)

            # Check that retrieve_relevant_simulations was called with the correct arguments
            mock_retrieve.assert_called_once_with(
                db_path=self.db_path,
                affected_services=["api-service", "auth-service"],
                scenario="network_latency",
                severity=50,
                limit=5,
            )

            # Check that the state was updated correctly
            self.assertEqual(len(result["relevant_simulations"]), 2)
            self.assertEqual(result["relevant_simulations"][0]["sim_id"], "sim1")
            self.assertEqual(result["relevant_simulations"][1]["sim_id"], "sim2")

    def test_store_in_memory(self):
        """Test storing in memory in the simulation workflow."""
        # Mock the store_simulation_in_memory function
        with patch("arc_memory.simulate.langgraph_flow.store_simulation_in_memory") as mock_store:
            # Set up the mock to return a simulation node
            mock_sim_node = MagicMock()
            mock_sim_node.id = "simulation:sim_test"
            mock_sim_node.sim_id = "sim_test"
            mock_sim_node.risk_score = 35
            mock_sim_node.scenario = "network_latency"
            mock_sim_node.severity = 50
            mock_store.return_value = mock_sim_node

            # Call the store_in_memory function
            result = store_in_memory(self.state)

            # Check that store_simulation_in_memory was called with the correct arguments
            mock_store.assert_called_once_with(
                db_path=self.db_path,
                attestation=self.state["attestation"],
                metrics=self.state["metrics"],
                affected_services=self.state["affected_services"],
                diff_data=self.state["diff_data"],
            )

            # Check that the state was updated correctly
            self.assertIsNotNone(result["simulation_node"])
            self.assertEqual(result["simulation_node"]["id"], "simulation:sim_test")
            self.assertEqual(result["simulation_node"]["sim_id"], "sim_test")
            self.assertEqual(result["simulation_node"]["risk_score"], 35)

    def test_memory_disabled(self):
        """Test that memory integration is skipped when disabled."""
        # Disable memory integration
        self.state["use_memory"] = False

        # Mock the retrieve_relevant_simulations function
        with patch("arc_memory.simulate.langgraph_flow.retrieve_relevant_simulations") as mock_retrieve:
            # Call the retrieve_memory function
            result = retrieve_memory(self.state)

            # Check that retrieve_relevant_simulations was not called
            mock_retrieve.assert_not_called()

            # Check that the state was not updated
            self.assertNotIn("relevant_simulations", result)

        # Mock the store_simulation_in_memory function
        with patch("arc_memory.simulate.langgraph_flow.store_simulation_in_memory") as mock_store:
            # Call the store_in_memory function
            result = store_in_memory(self.state)

            # Check that store_simulation_in_memory was not called
            mock_store.assert_not_called()

            # Check that the state was not updated
            self.assertNotIn("simulation_node", result)

    @patch("arc_memory.simulate.langgraph_flow.create_workflow")
    def test_run_sim_with_memory(self, mock_create_workflow):
        """Test running a simulation with memory integration."""
        # Mock the workflow
        mock_workflow = MagicMock()
        mock_create_workflow.return_value = mock_workflow

        # Mock the final state
        mock_final_state = {
            "status": "completed",
            "use_memory": True,
            "attestation": {"sim_id": "sim_test"},
            "explanation": "Test explanation",
            "risk_score": 35,
            "metrics": {"latency_ms": 250},
            "affected_services": ["api-service"],
            "relevant_simulations": [{"sim_id": "sim1"}, {"sim_id": "sim2"}],
            "simulation_node": {"id": "simulation:sim_test"},
        }
        mock_workflow.invoke.return_value = mock_final_state

        # Run the simulation
        result = run_sim(
            rev_range="HEAD~1..HEAD",
            scenario="network_latency",
            severity=50,
            timeout=60,
            repo_path=self.temp_dir.name,
            db_path=self.db_path,
            use_memory=True,
        )

        # Check that the workflow was created and invoked
        mock_create_workflow.assert_called_once()
        mock_workflow.invoke.assert_called_once()

        # Check that the result includes memory information
        self.assertIn("memory", result)
        self.assertTrue(result["memory"]["memory_used"])
        self.assertEqual(result["memory"]["similar_simulations_count"], 2)
        self.assertTrue(result["memory"]["simulation_stored"])


if __name__ == "__main__":
    unittest.main()
