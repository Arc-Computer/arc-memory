"""Tests for the impact module."""

import unittest
from unittest.mock import MagicMock, patch

from arc_memory.sdk.impact import (
    analyze_component_impact,
    _analyze_direct_dependencies,
    _analyze_indirect_dependencies,
    _find_indirect_dependencies,
    _analyze_cochange_patterns
)
from arc_memory.sdk.models import ImpactResult


class TestImpact(unittest.TestCase):
    """Tests for the impact module."""

    def test_analyze_component_impact(self):
        """Test the analyze_component_impact function."""
        # Create a mock adapter
        mock_adapter = MagicMock()
        
        # Set up the mock adapter to return a node
        mock_adapter.get_node_by_id.return_value = {
            "id": "component:123",
            "type": "component",
            "title": "Login Component",
            "body": "Handles user authentication",
            "timestamp": "2023-01-01T12:00:00"
        }

        # Mock the dependency analysis functions
        with patch("arc_memory.sdk.impact._analyze_direct_dependencies") as mock_direct:
            with patch("arc_memory.sdk.impact._analyze_indirect_dependencies") as mock_indirect:
                with patch("arc_memory.sdk.impact._analyze_cochange_patterns") as mock_cochange:
                    # Set up the mocks to return some results
                    mock_direct.return_value = [
                        ImpactResult(
                            id="component:456",
                            type="component",
                            title="Auth Component",
                            body="Authentication service",
                            properties={},
                            related_entities=[],
                            impact_type="direct",
                            impact_score=0.9,
                            impact_path=["component:123", "component:456"]
                        )
                    ]
                    mock_indirect.return_value = [
                        ImpactResult(
                            id="component:789",
                            type="component",
                            title="User Component",
                            body="User management",
                            properties={},
                            related_entities=[],
                            impact_type="indirect",
                            impact_score=0.7,
                            impact_path=["component:123", "component:456", "component:789"]
                        )
                    ]
                    mock_cochange.return_value = [
                        ImpactResult(
                            id="component:012",
                            type="component",
                            title="Session Component",
                            body="Session management",
                            properties={},
                            related_entities=[],
                            impact_type="potential",
                            impact_score=0.5,
                            impact_path=["component:123", "component:012"]
                        )
                    ]

                    # Call the function
                    result = analyze_component_impact(
                        adapter=mock_adapter,
                        component_id="component:123",
                        impact_types=["direct", "indirect", "potential"],
                        max_depth=3
                    )

                    # Check the result
                    self.assertEqual(len(result), 3)
                    self.assertIsInstance(result[0], ImpactResult)
                    self.assertEqual(result[0].id, "component:456")
                    self.assertEqual(result[0].type, "component")
                    self.assertEqual(result[0].title, "Auth Component")
                    self.assertEqual(result[0].impact_type, "direct")
                    self.assertEqual(result[0].impact_score, 0.9)
                    self.assertEqual(result[0].impact_path, ["component:123", "component:456"])

                    self.assertIsInstance(result[1], ImpactResult)
                    self.assertEqual(result[1].id, "component:789")
                    self.assertEqual(result[1].type, "component")
                    self.assertEqual(result[1].title, "User Component")
                    self.assertEqual(result[1].impact_type, "indirect")
                    self.assertEqual(result[1].impact_score, 0.7)
                    self.assertEqual(result[1].impact_path, ["component:123", "component:456", "component:789"])

                    self.assertIsInstance(result[2], ImpactResult)
                    self.assertEqual(result[2].id, "component:012")
                    self.assertEqual(result[2].type, "component")
                    self.assertEqual(result[2].title, "Session Component")
                    self.assertEqual(result[2].impact_type, "potential")
                    self.assertEqual(result[2].impact_score, 0.5)
                    self.assertEqual(result[2].impact_path, ["component:123", "component:012"])

                    # Check that the adapter methods were called with the right arguments
                    mock_adapter.get_node_by_id.assert_called_once_with("component:123")
                    mock_direct.assert_called_once_with(mock_adapter, "component:123")
                    mock_indirect.assert_called_once_with(mock_adapter, "component:123", mock_direct.return_value, 3)
                    mock_cochange.assert_called_once_with(mock_adapter, "component:123")

    def test_analyze_direct_dependencies(self):
        """Test the _analyze_direct_dependencies function."""
        # Create a mock adapter
        mock_adapter = MagicMock()
        
        # Set up the mock adapter to return some edges and nodes
        mock_adapter.get_edges_by_src.return_value = [
            {"src": "component:123", "dst": "component:456", "rel": "DEPENDS_ON"},
            {"src": "component:123", "dst": "component:789", "rel": "IMPORTS"}
        ]
        mock_adapter.get_edges_by_dst.return_value = [
            {"src": "component:012", "dst": "component:123", "rel": "USES"}
        ]
        mock_adapter.get_node_by_id.side_effect = lambda id: {
            "component:456": {"id": "component:456", "type": "component", "title": "Auth Component"},
            "component:789": {"id": "component:789", "type": "component", "title": "User Component"},
            "component:012": {"id": "component:012", "type": "component", "title": "Session Component"}
        }.get(id)

        # Call the function
        result = _analyze_direct_dependencies(mock_adapter, "component:123")

        # Check the result
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], ImpactResult)
        self.assertEqual(result[0].id, "component:456")
        self.assertEqual(result[0].type, "component")
        self.assertEqual(result[0].title, "Auth Component")
        self.assertEqual(result[0].impact_type, "direct")
        self.assertEqual(result[0].impact_score, 0.9)
        self.assertEqual(result[0].impact_path, ["component:123", "component:456"])

        self.assertIsInstance(result[1], ImpactResult)
        self.assertEqual(result[1].id, "component:789")
        self.assertEqual(result[1].type, "component")
        self.assertEqual(result[1].title, "User Component")
        self.assertEqual(result[1].impact_type, "direct")
        self.assertEqual(result[1].impact_score, 0.9)
        self.assertEqual(result[1].impact_path, ["component:123", "component:789"])

        self.assertIsInstance(result[2], ImpactResult)
        self.assertEqual(result[2].id, "component:012")
        self.assertEqual(result[2].type, "component")
        self.assertEqual(result[2].title, "Session Component")
        self.assertEqual(result[2].impact_type, "direct")
        self.assertEqual(result[2].impact_score, 0.8)
        self.assertEqual(result[2].impact_path, ["component:123", "component:012"])


if __name__ == "__main__":
    unittest.main()
