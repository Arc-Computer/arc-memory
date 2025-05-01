"""Tests for the memory query module."""

import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from arc_memory.memory.query import (
    _node_to_simulation,
    _node_to_metric,
    get_simulation_by_id,
    get_simulations_by_service,
    get_simulations_by_file,
    get_similar_simulations,
    get_simulation_metrics,
)
from arc_memory.schema.models import (
    NodeType,
    EdgeRel,
    SimulationNode,
    MetricNode,
)
from arc_memory.sql.db import init_db


class TestMemoryQuery(unittest.TestCase):
    """Tests for the memory query module."""

    def setUp(self):
        """Set up test environment."""
        # Initialize a test database
        self.conn = init_db(test_mode=True)

    def test_node_to_simulation(self):
        """Test converting a node dictionary to a SimulationNode."""
        # Create a node dictionary
        node_data = {
            "id": "simulation:sim_test",
            "type": NodeType.SIMULATION.value,
            "title": "Test Simulation",
            "body": "Test explanation",
            "extra": {
                "ts": "2023-01-01T00:00:00",
                "sim_id": "sim_test",
                "rev_range": "HEAD~1..HEAD",
                "scenario": "network_latency",
                "severity": 50,
                "risk_score": 35,
                "manifest_hash": "abc123",
                "commit_target": "def456",
                "diff_hash": "ghi789",
                "affected_services": ["api-service", "auth-service"],
            },
        }

        # Convert to a SimulationNode
        sim_node = _node_to_simulation(node_data)

        # Check that the conversion was successful
        self.assertIsNotNone(sim_node)
        self.assertEqual(sim_node.id, "simulation:sim_test")
        self.assertEqual(sim_node.type, NodeType.SIMULATION)
        self.assertEqual(sim_node.title, "Test Simulation")
        self.assertEqual(sim_node.body, "Test explanation")
        self.assertEqual(sim_node.sim_id, "sim_test")
        self.assertEqual(sim_node.rev_range, "HEAD~1..HEAD")
        self.assertEqual(sim_node.scenario, "network_latency")
        self.assertEqual(sim_node.severity, 50)
        self.assertEqual(sim_node.risk_score, 35)
        self.assertEqual(sim_node.manifest_hash, "abc123")
        self.assertEqual(sim_node.commit_target, "def456")
        self.assertEqual(sim_node.diff_hash, "ghi789")
        self.assertEqual(sim_node.affected_services, ["api-service", "auth-service"])

        # Test with a non-simulation node
        node_data["type"] = NodeType.COMMIT.value
        sim_node = _node_to_simulation(node_data)
        self.assertIsNone(sim_node)

    def test_node_to_metric(self):
        """Test converting a node dictionary to a MetricNode."""
        # Create a node dictionary
        node_data = {
            "id": "metric:sim_test:latency_ms",
            "type": NodeType.METRIC.value,
            "title": "Latency: 250ms",
            "body": "Metric collected during simulation sim_test",
            "extra": {
                "ts": "2023-01-01T00:00:00",
                "name": "latency_ms",
                "value": 250.0,
                "unit": "ms",
                "timestamp": "2023-01-01T00:00:00",
                "service": "api-service",
            },
        }

        # Convert to a MetricNode
        metric_node = _node_to_metric(node_data)

        # Check that the conversion was successful
        self.assertIsNotNone(metric_node)
        self.assertEqual(metric_node.id, "metric:sim_test:latency_ms")
        self.assertEqual(metric_node.type, NodeType.METRIC)
        self.assertEqual(metric_node.title, "Latency: 250ms")
        self.assertEqual(metric_node.body, "Metric collected during simulation sim_test")
        self.assertEqual(metric_node.name, "latency_ms")
        self.assertEqual(metric_node.value, 250.0)
        self.assertEqual(metric_node.unit, "ms")
        self.assertEqual(metric_node.service, "api-service")

        # Test with a non-metric node
        node_data["type"] = NodeType.COMMIT.value
        metric_node = _node_to_metric(node_data)
        self.assertIsNone(metric_node)

    def test_get_simulation_by_id(self):
        """Test getting a simulation by ID."""
        # Mock get_node_by_id
        with patch("arc_memory.memory.query.get_node_by_id") as mock_get_node:
            # Set up the mock to return a simulation node
            mock_get_node.return_value = {
                "id": "simulation:sim_test",
                "type": NodeType.SIMULATION.value,
                "title": "Test Simulation",
                "body": "Test explanation",
                "extra": {
                    "sim_id": "sim_test",
                    "rev_range": "HEAD~1..HEAD",
                    "scenario": "network_latency",
                    "severity": 50,
                    "risk_score": 35,
                    "manifest_hash": "abc123",
                    "commit_target": "def456",
                    "diff_hash": "ghi789",
                    "affected_services": ["api-service", "auth-service"],
                },
            }

            # Get the simulation
            sim_node = get_simulation_by_id(self.conn, "sim_test")

            # Check that get_node_by_id was called with the correct arguments
            mock_get_node.assert_called_once_with(self.conn, "simulation:sim_test")

            # Check that the simulation was returned
            self.assertIsNotNone(sim_node)
            self.assertEqual(sim_node.id, "simulation:sim_test")
            self.assertEqual(sim_node.sim_id, "sim_test")

            # Test with a full node ID
            mock_get_node.reset_mock()
            sim_node = get_simulation_by_id(self.conn, "simulation:sim_test")
            mock_get_node.assert_called_once_with(self.conn, "simulation:sim_test")

            # Test with a non-existent simulation
            mock_get_node.reset_mock()
            mock_get_node.return_value = None
            sim_node = get_simulation_by_id(self.conn, "non_existent")
            mock_get_node.assert_called_once_with(self.conn, "simulation:non_existent")
            self.assertIsNone(sim_node)

    def test_get_simulations_by_service(self):
        """Test getting simulations by service."""
        # Mock get_edges_by_dst and get_node_by_id
        with patch("arc_memory.memory.query.get_edges_by_dst") as mock_get_edges, \
             patch("arc_memory.memory.query.get_node_by_id") as mock_get_node:
            # Set up the mocks
            mock_get_edges.return_value = [
                {"src": "simulation:sim1", "dst": "service:api-service", "rel": EdgeRel.AFFECTS.value},
                {"src": "simulation:sim2", "dst": "service:api-service", "rel": EdgeRel.AFFECTS.value},
            ]

            mock_get_node.side_effect = lambda conn, node_id: {
                "simulation:sim1": {
                    "id": "simulation:sim1",
                    "type": NodeType.SIMULATION.value,
                    "title": "Simulation 1",
                    "extra": {"sim_id": "sim1", "affected_services": ["api-service"]},
                },
                "simulation:sim2": {
                    "id": "simulation:sim2",
                    "type": NodeType.SIMULATION.value,
                    "title": "Simulation 2",
                    "extra": {"sim_id": "sim2", "affected_services": ["api-service"]},
                },
            }.get(node_id)

            # Get simulations by service
            sims = get_simulations_by_service(self.conn, "api-service")

            # Check that get_edges_by_dst was called with the correct arguments
            mock_get_edges.assert_called_once_with(
                self.conn, "service:api-service", rel_type=EdgeRel.AFFECTS
            )

            # Check that get_node_by_id was called for each edge
            self.assertEqual(mock_get_node.call_count, 2)

            # Check that the simulations were returned
            self.assertEqual(len(sims), 2)
            self.assertEqual(sims[0].id, "simulation:sim1")
            self.assertEqual(sims[1].id, "simulation:sim2")

    def test_get_simulations_by_file(self):
        """Test getting simulations by file."""
        # Mock get_edges_by_dst and get_node_by_id
        with patch("arc_memory.memory.query.get_edges_by_dst") as mock_get_edges, \
             patch("arc_memory.memory.query.get_node_by_id") as mock_get_node:
            # Set up the mocks
            mock_get_edges.return_value = [
                {"src": "simulation:sim1", "dst": "file:src/api.py", "rel": EdgeRel.AFFECTS.value},
                {"src": "simulation:sim2", "dst": "file:src/api.py", "rel": EdgeRel.AFFECTS.value},
            ]

            mock_get_node.side_effect = lambda conn, node_id: {
                "simulation:sim1": {
                    "id": "simulation:sim1",
                    "type": NodeType.SIMULATION.value,
                    "title": "Simulation 1",
                    "extra": {"sim_id": "sim1"},
                },
                "simulation:sim2": {
                    "id": "simulation:sim2",
                    "type": NodeType.SIMULATION.value,
                    "title": "Simulation 2",
                    "extra": {"sim_id": "sim2"},
                },
            }.get(node_id)

            # Get simulations by file
            sims = get_simulations_by_file(self.conn, "src/api.py")

            # Check that get_edges_by_dst was called with the correct arguments
            mock_get_edges.assert_called_once_with(
                self.conn, "file:src/api.py", rel_type=EdgeRel.AFFECTS
            )

            # Check that get_node_by_id was called for each edge
            self.assertEqual(mock_get_node.call_count, 2)

            # Check that the simulations were returned
            self.assertEqual(len(sims), 2)
            self.assertEqual(sims[0].id, "simulation:sim1")
            self.assertEqual(sims[1].id, "simulation:sim2")



    def test_get_simulation_metrics(self):
        """Test getting metrics for a simulation."""
        # Mock get_edges_by_src and get_node_by_id
        with patch("arc_memory.memory.query.get_edges_by_src") as mock_get_edges, \
             patch("arc_memory.memory.query.get_node_by_id") as mock_get_node:
            # Set up the mocks
            mock_get_edges.return_value = [
                {"src": "simulation:sim_test", "dst": "metric:sim_test:latency_ms", "rel": EdgeRel.MEASURES.value},
                {"src": "simulation:sim_test", "dst": "metric:sim_test:error_rate", "rel": EdgeRel.MEASURES.value},
            ]

            mock_get_node.side_effect = lambda conn, node_id: {
                "metric:sim_test:latency_ms": {
                    "id": "metric:sim_test:latency_ms",
                    "type": NodeType.METRIC.value,
                    "title": "Latency: 250ms",
                    "extra": {"name": "latency_ms", "value": 250.0, "unit": "ms"},
                },
                "metric:sim_test:error_rate": {
                    "id": "metric:sim_test:error_rate",
                    "type": NodeType.METRIC.value,
                    "title": "Error Rate: 0.05%",
                    "extra": {"name": "error_rate", "value": 0.05, "unit": "%"},
                },
            }.get(node_id)

            # Get metrics for a simulation
            metrics = get_simulation_metrics(self.conn, "sim_test")

            # Check that get_edges_by_src was called with the correct arguments
            mock_get_edges.assert_called_once_with(
                self.conn, "simulation:sim_test", rel_type=EdgeRel.MEASURES
            )

            # Check that get_node_by_id was called for each edge
            self.assertEqual(mock_get_node.call_count, 2)

            # Check that the metrics were returned
            self.assertEqual(len(metrics), 2)
            self.assertEqual(metrics[0].id, "metric:sim_test:latency_ms")
            self.assertEqual(metrics[0].name, "latency_ms")
            self.assertEqual(metrics[0].value, 250.0)
            self.assertEqual(metrics[1].id, "metric:sim_test:error_rate")
            self.assertEqual(metrics[1].name, "error_rate")
            self.assertEqual(metrics[1].value, 0.05)


if __name__ == "__main__":
    unittest.main()
