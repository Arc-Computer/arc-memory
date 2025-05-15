"""
Tests for the environment module.
"""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from arc_memory.rl.environment import ArcEnvironment
from arc_memory.schema.models import NodeType


class TestArcEnvironment(unittest.TestCase):
    """Test the ArcEnvironment class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock SDK
        self.mock_sdk = MagicMock()
        
        # Mock the get_nodes_by_type method
        self.mock_sdk.get_nodes_by_type.return_value = [
            MagicMock(id="node1", node_type=NodeType.FILE),
            MagicMock(id="node2", node_type=NodeType.FUNCTION),
            MagicMock(id="node3", node_type=NodeType.CLASS),
        ]
        
        # Mock the get_edges_for_nodes method
        self.mock_sdk.get_edges_for_nodes.return_value = [
            MagicMock(source_id="node1", target_id="node2", edge_type="IMPORT"),
            MagicMock(source_id="node2", target_id="node3", edge_type="CALLS"),
        ]
        
        # Mock the get_edges_for_node method
        self.mock_sdk.get_edges_for_node.return_value = [
            MagicMock(source_id="node1", target_id="node2", edge_type="IMPORT"),
        ]
        
        # Create the environment
        self.env = ArcEnvironment(self.mock_sdk)
    
    def test_get_current_state(self):
        """Test the _get_current_state method."""
        # Get the current state
        state = self.env._get_current_state()
        
        # Check that the state has the expected keys
        self.assertIn("node_counts", state)
        self.assertIn("edge_counts", state)
        self.assertIn("total_nodes", state)
        self.assertIn("total_edges", state)
        
        # Check that the state has the expected values
        self.assertEqual(state["total_nodes"], 3)
        self.assertEqual(state["total_edges"], 2)
    
    def test_observe(self):
        """Test the observe method."""
        # Observe the environment
        state = self.env.observe()
        
        # Check that the state has the expected keys
        self.assertIn("node_counts", state)
        self.assertIn("edge_counts", state)
        self.assertIn("total_nodes", state)
        self.assertIn("total_edges", state)
    
    def test_step_blast_radius(self):
        """Test the step method with a blast radius prediction action."""
        # Define the action
        action = {
            "type": "predict_blast_radius",
            "node_id": "node1",
            "radius": ["node2"],
        }
        
        # Take a step
        next_state, reward, done, info = self.env.step(action)
        
        # Check that the next state is returned
        self.assertIsNotNone(next_state)
        
        # Check that the episode is not done
        self.assertFalse(done)
        
        # Check that the info has the expected keys
        self.assertIn("action_processed", info)
        
        # Check that the info has the expected values
        self.assertEqual(info["action_processed"], "predict_blast_radius")
    
    def test_step_vulnerability(self):
        """Test the step method with a vulnerability prediction action."""
        # Define the action
        action = {
            "type": "predict_vulnerability",
            "node_id": "node1",
            "vulnerability_type": "sql_injection",
            "confidence": 0.8,
        }
        
        # Take a step
        # Use a fixed seed for reproducibility
        with patch("numpy.random.random", return_value=0.05):  # 5% chance of vulnerability
            next_state, reward, done, info = self.env.step(action)
        
        # Check that the next state is returned
        self.assertIsNotNone(next_state)
        
        # Check that the episode is not done
        self.assertFalse(done)
        
        # Check that the info has the expected keys
        self.assertIn("action_processed", info)
        
        # Check that the info has the expected values
        self.assertEqual(info["action_processed"], "predict_vulnerability")
    
    def test_get_connected_nodes(self):
        """Test the _get_connected_nodes method."""
        # Get connected nodes
        connected_nodes = self.env._get_connected_nodes("node1")
        
        # Check that the expected nodes are returned
        self.assertEqual(connected_nodes, ["node2"])
    
    def test_simulate_vulnerability(self):
        """Test the _simulate_vulnerability method."""
        # Use a fixed seed for reproducibility
        with patch("numpy.random.random", return_value=0.05):  # 5% chance of vulnerability
            # Simulate vulnerability
            is_vulnerable = self.env._simulate_vulnerability("node1", "sql_injection")
            
            # Check that the node is vulnerable
            self.assertTrue(is_vulnerable)
        
        # Use a fixed seed for reproducibility
        with patch("numpy.random.random", return_value=0.95):  # 95% chance of no vulnerability
            # Simulate vulnerability
            is_vulnerable = self.env._simulate_vulnerability("node1", "sql_injection")
            
            # Check that the node is not vulnerable
            self.assertFalse(is_vulnerable)


if __name__ == "__main__":
    unittest.main() 
