"""Tests for the memory integration schema models."""

import unittest
from datetime import datetime

from arc_memory.schema.models import (
    NodeType,
    EdgeRel,
    Node,
    SimulationNode,
    MetricNode,
    Edge,
)


class TestMemoryModels(unittest.TestCase):
    """Tests for the memory integration schema models."""

    def test_node_types(self):
        """Test that the new node types are defined correctly."""
        self.assertEqual(NodeType.SIMULATION.value, "simulation")
        self.assertEqual(NodeType.METRIC.value, "metric")

    def test_edge_relations(self):
        """Test that the new edge relations are defined correctly."""
        self.assertEqual(EdgeRel.SIMULATES.value, "SIMULATES")
        self.assertEqual(EdgeRel.AFFECTS.value, "AFFECTS")
        self.assertEqual(EdgeRel.MEASURES.value, "MEASURES")
        self.assertEqual(EdgeRel.PREDICTS.value, "PREDICTS")

    def test_simulation_node(self):
        """Test creating a simulation node."""
        # Create a simulation node
        now = datetime.now()
        sim_node = SimulationNode(
            id="simulation:123",
            title="Test Simulation",
            body="This is a test simulation",
            ts=now,
            sim_id="sim_HEAD~1_HEAD",
            rev_range="HEAD~1..HEAD",
            scenario="network_latency",
            severity=50,
            risk_score=35,
            manifest_hash="abc123",
            commit_target="def456",
            diff_hash="ghi789",
            affected_services=["api-service", "auth-service"],
        )

        # Check that the node was created correctly
        self.assertEqual(sim_node.id, "simulation:123")
        self.assertEqual(sim_node.type, NodeType.SIMULATION)
        self.assertEqual(sim_node.title, "Test Simulation")
        self.assertEqual(sim_node.body, "This is a test simulation")
        self.assertEqual(sim_node.ts, now)
        self.assertEqual(sim_node.sim_id, "sim_HEAD~1_HEAD")
        self.assertEqual(sim_node.rev_range, "HEAD~1..HEAD")
        self.assertEqual(sim_node.scenario, "network_latency")
        self.assertEqual(sim_node.severity, 50)
        self.assertEqual(sim_node.risk_score, 35)
        self.assertEqual(sim_node.manifest_hash, "abc123")
        self.assertEqual(sim_node.commit_target, "def456")
        self.assertEqual(sim_node.diff_hash, "ghi789")
        self.assertEqual(sim_node.affected_services, ["api-service", "auth-service"])

    def test_metric_node(self):
        """Test creating a metric node."""
        # Create a metric node
        now = datetime.now()
        metric_node = MetricNode(
            id="metric:123",
            title="Latency Metric",
            body="This is a latency metric",
            ts=now,
            name="latency_ms",
            value=250.0,
            unit="ms",
            timestamp=now,
            service="api-service",
        )

        # Check that the node was created correctly
        self.assertEqual(metric_node.id, "metric:123")
        self.assertEqual(metric_node.type, NodeType.METRIC)
        self.assertEqual(metric_node.title, "Latency Metric")
        self.assertEqual(metric_node.body, "This is a latency metric")
        self.assertEqual(metric_node.ts, now)
        self.assertEqual(metric_node.name, "latency_ms")
        self.assertEqual(metric_node.value, 250.0)
        self.assertEqual(metric_node.unit, "ms")
        self.assertEqual(metric_node.timestamp, now)
        self.assertEqual(metric_node.service, "api-service")

    def test_edge_creation(self):
        """Test creating edges with the new edge relations."""
        # Create edges
        simulates_edge = Edge(
            src="simulation:123",
            dst="commit:abc123",
            rel=EdgeRel.SIMULATES,
            properties={"timestamp": "2023-01-01T00:00:00Z"},
        )

        affects_edge = Edge(
            src="simulation:123",
            dst="service:api-service",
            rel=EdgeRel.AFFECTS,
            properties={"impact_level": "high"},
        )

        measures_edge = Edge(
            src="simulation:123",
            dst="metric:123",
            rel=EdgeRel.MEASURES,
            properties={"timestamp": "2023-01-01T00:00:00Z"},
        )

        predicts_edge = Edge(
            src="simulation:123",
            dst="service:api-service",
            rel=EdgeRel.PREDICTS,
            properties={"prediction": "latency increase"},
        )

        # Check that the edges were created correctly
        self.assertEqual(simulates_edge.src, "simulation:123")
        self.assertEqual(simulates_edge.dst, "commit:abc123")
        self.assertEqual(simulates_edge.rel, EdgeRel.SIMULATES)
        self.assertEqual(simulates_edge.properties, {"timestamp": "2023-01-01T00:00:00Z"})

        self.assertEqual(affects_edge.src, "simulation:123")
        self.assertEqual(affects_edge.dst, "service:api-service")
        self.assertEqual(affects_edge.rel, EdgeRel.AFFECTS)
        self.assertEqual(affects_edge.properties, {"impact_level": "high"})

        self.assertEqual(measures_edge.src, "simulation:123")
        self.assertEqual(measures_edge.dst, "metric:123")
        self.assertEqual(measures_edge.rel, EdgeRel.MEASURES)
        self.assertEqual(measures_edge.properties, {"timestamp": "2023-01-01T00:00:00Z"})

        self.assertEqual(predicts_edge.src, "simulation:123")
        self.assertEqual(predicts_edge.dst, "service:api-service")
        self.assertEqual(predicts_edge.rel, EdgeRel.PREDICTS)
        self.assertEqual(predicts_edge.properties, {"prediction": "latency increase"})


if __name__ == "__main__":
    unittest.main()
