"""Tests for the memory storage module."""

import unittest
from datetime import datetime
from unittest.mock import patch

from arc_memory.memory.storage import (
    create_simulation_node,
    create_metric_nodes,
    create_simulation_edges,
    store_simulation_results,
)
from arc_memory.schema.models import (
    NodeType,
    EdgeRel,
    SimulationNode,
    MetricNode,
    Edge,
)
from arc_memory.sql.db import init_db


class TestMemoryStorage(unittest.TestCase):
    """Tests for the memory storage module."""

    def setUp(self):
        """Set up test environment."""
        # Initialize a test database
        self.conn = init_db(test_mode=True)

    def test_create_simulation_node(self):
        """Test creating a simulation node."""
        # Create a simulation node
        sim_node = create_simulation_node(
            sim_id="sim_test",
            rev_range="HEAD~1..HEAD",
            scenario="network_latency",
            severity=50,
            risk_score=35,
            manifest_hash="abc123",
            commit_target="def456",
            diff_hash="ghi789",
            affected_services=["api-service", "auth-service"],
            explanation="Test explanation",
        )

        # Check that the node was created correctly
        self.assertEqual(sim_node.id, "simulation:sim_test")
        self.assertEqual(sim_node.type, NodeType.SIMULATION)
        self.assertEqual(sim_node.sim_id, "sim_test")
        self.assertEqual(sim_node.rev_range, "HEAD~1..HEAD")
        self.assertEqual(sim_node.scenario, "network_latency")
        self.assertEqual(sim_node.severity, 50)
        self.assertEqual(sim_node.risk_score, 35)
        self.assertEqual(sim_node.manifest_hash, "abc123")
        self.assertEqual(sim_node.commit_target, "def456")
        self.assertEqual(sim_node.diff_hash, "ghi789")
        self.assertEqual(sim_node.affected_services, ["api-service", "auth-service"])
        self.assertEqual(sim_node.body, "Test explanation")

    def test_create_metric_nodes(self):
        """Test creating metric nodes."""
        # Create metric nodes
        metrics = {
            "latency_ms": 250,
            "error_rate": 0.05,
            "cpu_usage": 75.5,
            "non_numeric": "value",  # This should be skipped
        }

        metric_nodes = create_metric_nodes(
            sim_id="sim_test",
            metrics=metrics,
        )

        # Check that the nodes were created correctly
        self.assertEqual(len(metric_nodes), 3)  # non_numeric should be skipped

        # Check the first metric node (latency_ms)
        latency_node = next(node for node in metric_nodes if node.name == "latency_ms")
        self.assertEqual(latency_node.id, "metric:sim_test:latency_ms")
        self.assertEqual(latency_node.type, NodeType.METRIC)
        self.assertEqual(latency_node.value, 250.0)
        self.assertEqual(latency_node.unit, "ms")

        # Check the second metric node (error_rate)
        error_node = next(node for node in metric_nodes if node.name == "error_rate")
        self.assertEqual(error_node.id, "metric:sim_test:error_rate")
        self.assertEqual(error_node.type, NodeType.METRIC)
        self.assertEqual(error_node.value, 0.05)
        self.assertEqual(error_node.unit, "%")

        # Check the third metric node (cpu_usage)
        cpu_node = next(node for node in metric_nodes if node.name == "cpu_usage")
        self.assertEqual(cpu_node.id, "metric:sim_test:cpu_usage")
        self.assertEqual(cpu_node.type, NodeType.METRIC)
        self.assertEqual(cpu_node.value, 75.5)
        self.assertEqual(cpu_node.unit, None)

    def test_create_simulation_edges(self):
        """Test creating simulation edges."""
        # Create a simulation node
        sim_node = create_simulation_node(
            sim_id="sim_test",
            rev_range="HEAD~1..HEAD",
            scenario="network_latency",
            severity=50,
            risk_score=35,
            manifest_hash="abc123",
            commit_target="def456",
            diff_hash="ghi789",
            affected_services=["api-service", "auth-service"],
        )

        # Create metric nodes
        metrics = {
            "latency_ms": 250,
            "error_rate": 0.05,
        }

        metric_nodes = create_metric_nodes(
            sim_id="sim_test",
            metrics=metrics,
        )

        # Create edges
        edges = create_simulation_edges(
            sim_node=sim_node,
            metric_nodes=metric_nodes,
            commit_id="commit:abc123",
            pr_id="pr:42",
            file_ids=["file:src/api.py", "file:src/auth.py"],
        )

        # Check that the edges were created correctly
        self.assertEqual(len(edges), 10)  # 2 metrics + 1 commit + 1 PR + 2 files + 4 services (2 AFFECTS + 2 PREDICTS)

        # Check the MEASURES edges
        measures_edges = [edge for edge in edges if edge.rel == EdgeRel.MEASURES]
        self.assertEqual(len(measures_edges), 2)
        self.assertEqual(measures_edges[0].src, "simulation:sim_test")
        self.assertEqual(measures_edges[0].rel, EdgeRel.MEASURES)

        # Check the SIMULATES edges
        simulates_edges = [edge for edge in edges if edge.rel == EdgeRel.SIMULATES]
        self.assertEqual(len(simulates_edges), 2)
        self.assertEqual(simulates_edges[0].src, "simulation:sim_test")
        self.assertEqual(simulates_edges[0].rel, EdgeRel.SIMULATES)
        self.assertIn(simulates_edges[0].dst, ["commit:abc123", "pr:42"])

        # Check the AFFECTS edges
        affects_edges = [edge for edge in edges if edge.rel == EdgeRel.AFFECTS]
        self.assertEqual(len(affects_edges), 4)  # 2 files + 2 services
        self.assertEqual(affects_edges[0].src, "simulation:sim_test")
        self.assertEqual(affects_edges[0].rel, EdgeRel.AFFECTS)

        # Check the PREDICTS edges
        predicts_edges = [edge for edge in edges if edge.rel == EdgeRel.PREDICTS]
        self.assertEqual(len(predicts_edges), 2)  # 2 services
        self.assertEqual(predicts_edges[0].src, "simulation:sim_test")
        self.assertEqual(predicts_edges[0].rel, EdgeRel.PREDICTS)
        self.assertIn(predicts_edges[0].dst, ["service:api-service", "service:auth-service"])

    def test_store_simulation_results(self):
        """Test storing simulation results."""
        # Mock add_nodes_and_edges
        with patch("arc_memory.memory.storage.add_nodes_and_edges") as mock_add:
            # Store simulation results
            sim_node, metric_nodes = store_simulation_results(
                conn_or_path=self.conn,
                sim_id="sim_test",
                rev_range="HEAD~1..HEAD",
                scenario="network_latency",
                severity=50,
                risk_score=35,
                manifest_hash="abc123",
                commit_target="def456",
                diff_hash="ghi789",
                affected_services=["api-service", "auth-service"],
                metrics={
                    "latency_ms": 250,
                    "error_rate": 0.05,
                },
                explanation="Test explanation",
                commit_id="commit:abc123",
                pr_id="pr:42",
                file_ids=["file:src/api.py", "file:src/auth.py"],
            )

            # Check that add_nodes_and_edges was called
            mock_add.assert_called_once()

            # Check the arguments
            args, _ = mock_add.call_args
            self.assertEqual(args[0], self.conn)

            # Check the nodes
            nodes = args[1]
            self.assertEqual(len(nodes), 3)  # 1 simulation + 2 metrics
            self.assertIsInstance(nodes[0], SimulationNode)
            self.assertIsInstance(nodes[1], MetricNode)
            self.assertIsInstance(nodes[2], MetricNode)

            # Check the edges
            edges = args[2]
            self.assertGreater(len(edges), 0)
            self.assertIsInstance(edges[0], Edge)

            # Check the return values
            self.assertIsInstance(sim_node, SimulationNode)
            self.assertEqual(len(metric_nodes), 2)
            self.assertIsInstance(metric_nodes[0], MetricNode)


if __name__ == "__main__":
    unittest.main()
