"""Tests for the memory integration module."""

import unittest
from datetime import datetime
from unittest.mock import patch

from arc_memory.memory.integration import (
    store_simulation_in_memory,
    retrieve_relevant_simulations,
    enhance_explanation_with_memory,
)
from arc_memory.schema.models import (
    NodeType,
    SimulationNode,
)
from arc_memory.sql.db import init_db


class TestMemoryIntegration(unittest.TestCase):
    """Tests for the memory integration module."""

    def setUp(self):
        """Set up test environment."""
        # Initialize a test database
        self.conn = init_db(test_mode=True)

        # Sample attestation data
        self.attestation = {
            "sim_id": "sim_test",
            "rev_range": "HEAD~1..HEAD",
            "scenario": "network_latency",
            "severity": 50,
            "risk_score": 35,
            "manifest_hash": "abc123",
            "commit_target": "def456",
            "diff_hash": "ghi789",
            "affected_services": ["api-service", "auth-service"],
            "explanation": "Test explanation",
            "timestamp": "2023-01-01T00:00:00Z",
        }

        # Sample metrics data
        self.metrics = {
            "latency_ms": 250,
            "error_rate": 0.05,
        }

        # Sample diff data
        self.diff_data = {
            "files": [
                {"path": "src/api.py"},
                {"path": "src/auth.py"},
            ],
            "end_commit": "def456",
        }

    def test_store_simulation_in_memory(self):
        """Test storing simulation results in memory."""
        # Mock get_connection and store_simulation_results
        with patch("arc_memory.memory.integration.get_connection") as mock_get_conn, \
             patch("arc_memory.memory.integration.store_simulation_results") as mock_store:
            # Set up the mocks
            mock_get_conn.return_value = self.conn
            mock_store.return_value = (
                SimulationNode(
                    id="simulation:sim_test",
                    type=NodeType.SIMULATION,
                    sim_id="sim_test",
                    rev_range="HEAD~1..HEAD",
                    scenario="network_latency",
                    severity=50,
                    risk_score=35,
                    manifest_hash="abc123",
                    commit_target="def456",
                    diff_hash="ghi789",
                    affected_services=["api-service", "auth-service"],
                ),
                []  # Metric nodes
            )

            # Store simulation in memory
            sim_node = store_simulation_in_memory(
                db_path="test.db",
                attestation=self.attestation,
                metrics=self.metrics,
                affected_services=["api-service", "auth-service"],
                diff_data=self.diff_data,
            )

            # Check that get_connection was called
            mock_get_conn.assert_called_once_with("test.db")

            # Check that store_simulation_results was called with the correct arguments
            mock_store.assert_called_once()
            kwargs = mock_store.call_args.kwargs
            self.assertEqual(kwargs["conn_or_path"], self.conn)
            self.assertEqual(kwargs["sim_id"], "sim_test")
            self.assertEqual(kwargs["rev_range"], "HEAD~1..HEAD")
            self.assertEqual(kwargs["scenario"], "network_latency")
            self.assertEqual(kwargs["severity"], 50)
            self.assertEqual(kwargs["risk_score"], 35)
            self.assertEqual(kwargs["manifest_hash"], "abc123")
            self.assertEqual(kwargs["commit_target"], "def456")
            self.assertEqual(kwargs["diff_hash"], "ghi789")
            self.assertEqual(kwargs["affected_services"], ["api-service", "auth-service"])
            self.assertEqual(kwargs["metrics"], self.metrics)
            self.assertEqual(kwargs["explanation"], "Test explanation")
            self.assertEqual(kwargs["commit_id"], "commit:def456")
            self.assertEqual(kwargs["file_ids"], ["file:src/api.py", "file:src/auth.py"])

            # Check that the simulation node was returned
            self.assertIsNotNone(sim_node)
            self.assertEqual(sim_node.id, "simulation:sim_test")
            self.assertEqual(sim_node.sim_id, "sim_test")

    def test_retrieve_relevant_simulations(self):
        """Test retrieving simulations relevant to current changes."""
        # Mock get_connection and get_similar_simulations
        with patch("arc_memory.memory.integration.get_connection") as mock_get_conn, \
             patch("arc_memory.memory.integration.get_similar_simulations") as mock_get_similar:
            # Set up the mocks
            mock_get_conn.return_value = self.conn
            mock_get_similar.return_value = [
                SimulationNode(
                    id="simulation:sim1",
                    type=NodeType.SIMULATION,
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
                    type=NodeType.SIMULATION,
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

            # Retrieve relevant simulations
            sims = retrieve_relevant_simulations(
                db_path="test.db",
                affected_services=["api-service", "auth-service"],
                scenario="network_latency",
                severity=50,
            )

            # Check that get_connection was called
            mock_get_conn.assert_called_once_with("test.db")

            # Check that get_similar_simulations was called with the correct arguments
            mock_get_similar.assert_called_once()
            kwargs = mock_get_similar.call_args.kwargs
            self.assertEqual(kwargs["conn_or_path"], self.conn)
            self.assertEqual(kwargs["affected_services"], ["api-service", "auth-service"])
            self.assertEqual(kwargs["scenario"], "network_latency")
            self.assertEqual(kwargs["severity_range"], (30, 70))  # ±20 points

            # Check that the simulations were returned
            self.assertEqual(len(sims), 2)
            self.assertEqual(sims[0]["sim_id"], "sim1")
            self.assertEqual(sims[0]["scenario"], "network_latency")
            self.assertEqual(sims[0]["severity"], 50)
            self.assertEqual(sims[0]["risk_score"], 35)
            self.assertEqual(sims[1]["sim_id"], "sim2")

    def test_enhance_explanation_with_memory(self):
        """Test enhancing explanation with historical context."""
        # Mock retrieve_relevant_simulations
        with patch("arc_memory.memory.integration.retrieve_relevant_simulations") as mock_retrieve:
            # Set up the mock
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

            # Original explanation
            original_explanation = "This change introduces network latency to the API service."

            # Enhance the explanation
            enhanced = enhance_explanation_with_memory(
                db_path="test.db",
                explanation=original_explanation,
                affected_services=["api-service", "auth-service"],
                scenario="network_latency",
                severity=50,
                risk_score=40,
            )

            # Check that retrieve_relevant_simulations was called with the correct arguments
            mock_retrieve.assert_called_once_with(
                db_path="test.db",
                affected_services=["api-service", "auth-service"],
                scenario="network_latency",
                severity=50,
            )

            # Check that the explanation was enhanced
            self.assertNotEqual(enhanced, original_explanation)
            self.assertTrue(original_explanation in enhanced)
            self.assertTrue("Historical Context" in enhanced)
            self.assertTrue("Simulation sim1" in enhanced)
            self.assertTrue("Simulation sim2" in enhanced)

            # Test with no relevant simulations
            mock_retrieve.reset_mock()
            mock_retrieve.return_value = []

            enhanced = enhance_explanation_with_memory(
                db_path="test.db",
                explanation=original_explanation,
                affected_services=["api-service", "auth-service"],
                scenario="network_latency",
                severity=50,
                risk_score=40,
            )

            # Check that the original explanation was returned unchanged
            self.assertEqual(enhanced, original_explanation)


if __name__ == "__main__":
    unittest.main()
