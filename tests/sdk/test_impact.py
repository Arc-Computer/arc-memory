"""Tests for the impact module."""

import unittest
from unittest.mock import MagicMock, patch

from arc_memory.sdk.impact import (
    analyze_component_impact,
    _analyze_direct_dependencies,
    _analyze_cochange_patterns,
    _calculate_relationship_strength,
    _evaluate_component_importance,
    _evaluate_architectural_context,
    _find_cochange_patterns,
    _calculate_cochange_score
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
            {"src": "component:123", "dst": "component:456", "rel": "DEPENDS_ON", "properties": {}},
            {"src": "component:123", "dst": "component:789", "rel": "IMPORTS", "properties": {}}
        ]
        mock_adapter.get_edges_by_dst.return_value = [
            {"src": "component:012", "dst": "component:123", "rel": "USES", "properties": {}}
        ]

        # Set up the component being analyzed
        component = {"id": "component:123", "type": "component", "title": "Test Component"}

        # Set up the nodes that will be returned
        nodes = {
            "component:123": component,
            "component:456": {"id": "component:456", "type": "component", "title": "Auth Component", "extra": {}},
            "component:789": {"id": "component:789", "type": "component", "title": "User Component", "extra": {}},
            "component:012": {"id": "component:012", "type": "component", "title": "Session Component", "extra": {}}
        }

        mock_adapter.get_node_by_id.side_effect = lambda id: nodes.get(id)

        # Call the function
        result = _analyze_direct_dependencies(mock_adapter, "component:123")

        # Check the result
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], ImpactResult)
        self.assertEqual(result[0].id, "component:456")
        self.assertEqual(result[0].type, "component")
        self.assertEqual(result[0].title, "Auth Component")
        self.assertEqual(result[0].impact_type, "direct")
        # We don't check the exact score since it's dynamically calculated
        self.assertGreater(result[0].impact_score, 0)
        self.assertLessEqual(result[0].impact_score, 1.0)
        self.assertEqual(result[0].impact_path, ["component:123", "component:456"])
        # Check that the properties contain the scoring factors
        self.assertIn("relationship_strength", result[0].properties)
        self.assertIn("component_importance", result[0].properties)
        self.assertIn("architectural_context", result[0].properties)

        self.assertIsInstance(result[1], ImpactResult)
        self.assertEqual(result[1].id, "component:789")
        self.assertEqual(result[1].type, "component")
        self.assertEqual(result[1].title, "User Component")
        self.assertEqual(result[1].impact_type, "direct")
        self.assertGreater(result[1].impact_score, 0)
        self.assertLessEqual(result[1].impact_score, 1.0)
        self.assertEqual(result[1].impact_path, ["component:123", "component:789"])

        # DEPENDS_ON should have a higher score than IMPORTS
        self.assertGreater(result[0].properties["relationship_strength"], result[1].properties["relationship_strength"])

        self.assertIsInstance(result[2], ImpactResult)
        self.assertEqual(result[2].id, "component:012")
        self.assertEqual(result[2].type, "component")
        self.assertEqual(result[2].title, "Session Component")
        self.assertEqual(result[2].impact_type, "direct")
        self.assertGreater(result[2].impact_score, 0)
        self.assertLessEqual(result[2].impact_score, 1.0)
        self.assertEqual(result[2].impact_path, ["component:123", "component:012"])

        # Test with a critical component
        # First, save the original score
        original_score = result[0].impact_score

        # Now modify the node to be critical
        nodes["component:456"]["extra"] = {"critical": True}

        # Reset the mock to ensure it's called again
        mock_adapter.get_node_by_id.reset_mock()
        mock_adapter.get_node_by_id.side_effect = lambda id: nodes.get(id)

        # Call the function again
        result_with_critical = _analyze_direct_dependencies(mock_adapter, "component:123")

        # Critical component should have a higher score
        # If the score is already at maximum (1.0), we can't test for greater
        if original_score < 1.0:
            self.assertGreater(
                result_with_critical[0].impact_score,
                original_score
            )
        else:
            # If the score is already at maximum, just check it's still at maximum
            self.assertEqual(result_with_critical[0].impact_score, 1.0)


    def test_calculate_relationship_strength(self):
        """Test the _calculate_relationship_strength function."""
        # Test with different relationship types
        edge_depends_on = {"rel": "DEPENDS_ON", "properties": {}}
        edge_mentions = {"rel": "MENTIONS", "properties": {}}  # MENTIONS has a much lower score (0.6)

        # Test with empty source and target
        source = {}
        target = {}

        # Check that relationship type affects score
        depends_on_score = _calculate_relationship_strength(edge_depends_on, source, target)
        mentions_score = _calculate_relationship_strength(edge_mentions, source, target)
        self.assertGreater(depends_on_score, mentions_score)

        # Test with other relationship types
        edge_imports = {"rel": "IMPORTS", "properties": {}}
        edge_references = {"rel": "REFERENCES", "properties": {}}  # REFERENCES has a lower score (0.7)

        # Check that IMPORTS has a higher score than REFERENCES
        imports_score = _calculate_relationship_strength(edge_imports, source, target)
        references_score = _calculate_relationship_strength(edge_references, source, target)
        self.assertGreater(imports_score, references_score)

        # Test with frequency property
        edge_with_frequency = {"rel": "DEPENDS_ON", "properties": {"frequency": 50}}
        with_frequency_score = _calculate_relationship_strength(edge_with_frequency, source, target)
        without_frequency_score = _calculate_relationship_strength(edge_depends_on, source, target)
        self.assertGreater(with_frequency_score, without_frequency_score)

        # Test with confidence property
        edge_with_confidence = {"rel": "DEPENDS_ON", "properties": {"confidence": 0.5}}
        self.assertLess(
            _calculate_relationship_strength(edge_with_confidence, source, target),
            _calculate_relationship_strength(edge_depends_on, source, target)
        )

        # Test with source and target node types
        source_system = {"type": "system", "extra": {}}
        target_system = {"type": "system", "extra": {}}

        # Get the score with system nodes
        system_score = _calculate_relationship_strength(edge_depends_on, source_system, target_system)

        # Get the score with empty nodes
        empty_score = _calculate_relationship_strength(edge_depends_on, source, target)

        # Check that system nodes get a higher score
        self.assertGreaterEqual(system_score, empty_score)

        # Test with critical components
        source_critical = {"type": "component", "extra": {"critical": True}}

        # Get the score with a critical component
        critical_score = _calculate_relationship_strength(edge_depends_on, source_critical, target)

        # Get the score with a non-critical component
        source_normal = {"type": "component", "extra": {}}
        normal_score = _calculate_relationship_strength(edge_depends_on, source_normal, target)

        # Check that critical components get a higher score
        self.assertGreaterEqual(critical_score, normal_score)

    def test_evaluate_component_importance(self):
        """Test the _evaluate_component_importance function."""
        # Create a mock adapter
        mock_adapter = MagicMock()

        # Set up the mock adapter to return edges
        mock_adapter.get_edges_by_dst.return_value = [{"id": 1}, {"id": 2}]
        mock_adapter.get_edges_by_src.return_value = [{"id": 3}]

        # Use fixed timestamps for deterministic tests
        current_time = "2023-01-15T12:00:00"

        # Test with different node types
        node_adr = {"id": "adr:1", "type": "adr", "timestamp": current_time}
        node_file = {"id": "file:1", "type": "file", "timestamp": current_time}
        node_issue = {"id": "issue:1", "type": "issue", "timestamp": current_time}

        # Check that node type affects importance
        self.assertGreater(
            _evaluate_component_importance(node_adr, mock_adapter),
            _evaluate_component_importance(node_issue, mock_adapter)
        )

        # Test with different connection counts
        mock_adapter_many_connections = MagicMock()
        mock_adapter_many_connections.get_edges_by_dst.return_value = [{"id": i} for i in range(10)]
        mock_adapter_many_connections.get_edges_by_src.return_value = [{"id": i} for i in range(10)]

        mock_adapter_few_connections = MagicMock()
        mock_adapter_few_connections.get_edges_by_dst.return_value = [{"id": 1}]
        mock_adapter_few_connections.get_edges_by_src.return_value = [{"id": 2}]

        # Check that more connections increase importance
        self.assertGreater(
            _evaluate_component_importance(node_file, mock_adapter_many_connections),
            _evaluate_component_importance(node_file, mock_adapter_few_connections)
        )

        # Test with older timestamp
        old_node = {"id": "file:old", "type": "file", "timestamp": "2020-01-01T00:00:00"}
        new_node = {"id": "file:new", "type": "file", "timestamp": current_time}

        # Check that older components might be more important
        self.assertGreater(
            _evaluate_component_importance(old_node, mock_adapter),
            _evaluate_component_importance(new_node, mock_adapter)
        )

    def test_evaluate_architectural_context(self):
        """Test the _evaluate_architectural_context function."""
        # Create a mock adapter
        mock_adapter = MagicMock()

        # Set up the mock adapter to return nodes and edges
        def get_node_by_id(id):
            nodes = {
                "system:1": {"id": "system:1", "type": "system"},
                "system:2": {"id": "system:2", "type": "system"},
                "service:1": {"id": "service:1", "type": "service"},
                "service:2": {"id": "service:2", "type": "service"},
                "component:1": {"id": "component:1", "type": "component", "extra": {"critical": True}},
                "component:2": {"id": "component:2", "type": "component"},
                "file:1": {"id": "file:1", "type": "file"}
            }
            return nodes.get(id)

        mock_adapter.get_node_by_id.side_effect = get_node_by_id

        # Set up edges for system boundary detection
        def get_edges_by_dst(id):
            if id == "service:1":
                return [{"src": "system:1", "rel": "CONTAINS"}]
            elif id == "service:2":
                return [{"src": "system:2", "rel": "CONTAINS"}]
            elif id == "component:1":
                return [{"src": "service:1", "rel": "CONTAINS"}]
            elif id == "component:2":
                return [{"src": "service:2", "rel": "CONTAINS"}]
            return []

        mock_adapter.get_edges_by_dst.side_effect = get_edges_by_dst

        # Test with critical component
        node_critical = {"id": "component:1", "type": "component", "extra": {"critical": True}}
        node_normal = {"id": "component:2", "type": "component", "extra": {}}

        # Check that critical components get a bonus
        self.assertGreater(
            _evaluate_architectural_context(node_critical, ["file:1", "component:1"], mock_adapter),
            _evaluate_architectural_context(node_normal, ["file:1", "component:2"], mock_adapter)
        )

        # Test with system boundary crossing
        path_same_system = ["system:1", "service:1", "component:1"]
        path_cross_system = ["system:1", "service:1", "component:1", "system:2", "service:2", "component:2"]

        # Check that crossing system boundaries applies a penalty
        self.assertLess(
            _evaluate_architectural_context(node_normal, path_cross_system, mock_adapter),
            _evaluate_architectural_context(node_normal, path_same_system, mock_adapter)
        )

    def test_find_cochange_patterns(self):
        """Test the _find_cochange_patterns function."""
        # Create a mock adapter
        mock_adapter = MagicMock()

        # Set up the mock adapter to return edges and nodes
        commit1 = {"id": "commit:1", "timestamp": "2023-01-01T00:00:00"}
        commit2 = {"id": "commit:2", "timestamp": "2023-01-02T00:00:00"}
        commit3 = {"id": "commit:3", "timestamp": "2023-01-03T00:00:00"}

        # Set up edges for file modifications
        def _mock_get_edges_by_dst(node_id, rel_type=None):
            edges = {
                "file:target": [
                    {"src": "commit:1", "rel": "MODIFIES"},
                    {"src": "commit:2", "rel": "MODIFIES"}
                ],
                "file:cochange1": [
                    {"src": "commit:1", "rel": "MODIFIES"},
                    {"src": "commit:3", "rel": "MODIFIES"}
                ],
                "file:cochange2": [
                    {"src": "commit:1", "rel": "MODIFIES"},
                    {"src": "commit:2", "rel": "MODIFIES"}
                ]
            }
            return edges.get(node_id, []) if rel_type == "MODIFIES" or rel_type is None else []

        mock_adapter.get_edges_by_dst.side_effect = _mock_get_edges_by_dst

        def _mock_get_edges_by_src(node_id, rel_type=None):
            edges = {
                "commit:1": [
                    {"dst": "file:target", "rel": "MODIFIES"},
                    {"dst": "file:cochange1", "rel": "MODIFIES"},
                    {"dst": "file:cochange2", "rel": "MODIFIES"}
                ],
                "commit:2": [
                    {"dst": "file:target", "rel": "MODIFIES"},
                    {"dst": "file:cochange2", "rel": "MODIFIES"}
                ],
                "commit:3": [
                    {"dst": "file:cochange1", "rel": "MODIFIES"}
                ]
            }
            return edges.get(node_id, []) if rel_type == "MODIFIES" or rel_type is None else []

        mock_adapter.get_edges_by_src.side_effect = _mock_get_edges_by_src

        mock_adapter.get_node_by_id.side_effect = lambda node_id: {
            "commit:1": commit1,
            "commit:2": commit2,
            "commit:3": commit3,
            "file:target": {"id": "file:target", "type": "file", "title": "Target File"},
            "file:cochange1": {"id": "file:cochange1", "type": "file", "title": "Co-change File 1"},
            "file:cochange2": {"id": "file:cochange2", "type": "file", "title": "Co-change File 2"}
        }.get(node_id)

        # Call the function
        patterns = _find_cochange_patterns(mock_adapter, "file:target")

        # Check the result
        self.assertEqual(len(patterns), 1)  # Only file:cochange2 changed together with target at least twice
        self.assertEqual(patterns[0]["component_id"], "file:cochange2")
        self.assertEqual(patterns[0]["frequency"], 2)
        self.assertGreater(patterns[0]["consistency"], 0)

    def test_analyze_cochange_patterns(self):
        """Test the _analyze_cochange_patterns function."""
        # Create a mock adapter
        mock_adapter = MagicMock()

        # Set up mock for _find_cochange_patterns
        with patch("arc_memory.sdk.impact._find_cochange_patterns") as mock_find_patterns:
            # Set up the mock to return some patterns
            mock_find_patterns.return_value = [
                {
                    "component_id": "file:cochange",
                    "frequency": 5,
                    "recency": "2023-01-02T00:00:00",
                    "consistency": 0.8
                }
            ]

            # Set up the mock adapter to return nodes
            mock_adapter.get_node_by_id.side_effect = lambda node_id: {
                "file:cochange": {"id": "file:cochange", "type": "file", "title": "Co-change File"}
            }.get(node_id)

            # Call the function
            results = _analyze_cochange_patterns(mock_adapter, "file:target")

            # Check that _find_cochange_patterns was called with the right arguments
            mock_find_patterns.assert_called_once_with(mock_adapter, "file:target")

            # Check the result
            self.assertEqual(len(results), 1)
            self.assertIsInstance(results[0], ImpactResult)
            self.assertEqual(results[0].id, "file:cochange")
            self.assertEqual(results[0].type, "file")
            self.assertEqual(results[0].title, "Co-change File")
            self.assertEqual(results[0].impact_type, "potential")
            self.assertGreater(results[0].impact_score, 0)
            self.assertEqual(results[0].impact_path, ["file:target", "file:cochange"])

            # Check that the properties contain the co-change metrics
            self.assertIn("frequency", results[0].properties)
            self.assertEqual(results[0].properties["frequency"], 5)
            self.assertIn("consistency", results[0].properties)
            self.assertEqual(results[0].properties["consistency"], 0.8)

    def test_calculate_cochange_score(self):
        """Test the _calculate_cochange_score function."""
        # Use fixed timestamps for deterministic tests
        recent_time = "2023-01-15T12:00:00"

        # Create test patterns
        patterns = [
            {
                "component_id": "file:1",
                "frequency": 5,
                "recency": recent_time,
                "consistency": 0.8
            },
            {
                "component_id": "file:2",
                "frequency": 2,
                "recency": "2023-01-01T00:00:00",
                "consistency": 0.4
            }
        ]

        # Test with different target IDs
        score1 = _calculate_cochange_score("file:source", "file:1", patterns)
        score2 = _calculate_cochange_score("file:source", "file:2", patterns)

        # Check that frequency, recency, and consistency affect the score
        self.assertGreater(score1, score2)

        # Test with non-existent target
        score_none = _calculate_cochange_score("file:source", "file:nonexistent", patterns)
        self.assertEqual(score_none, 0.0)

        # Test with different frequencies
        patterns_high_freq = [
            {
                "component_id": "file:1",
                "frequency": 20,
                "recency": recent_time,
                "consistency": 0.8
            }
        ]

        score_high_freq = _calculate_cochange_score("file:source", "file:1", patterns_high_freq)
        self.assertGreater(score_high_freq, score1)


if __name__ == "__main__":
    unittest.main()
