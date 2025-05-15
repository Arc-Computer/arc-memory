"""
Tests for the agent module.
"""

import unittest
import tempfile
import os
from unittest.mock import MagicMock, patch

import numpy as np

from arc_memory.rl.agent import BaseAgent, RandomAgent, QTableAgent


class TestBaseAgent(unittest.TestCase):
    """Test the BaseAgent class."""
    
    def test_init(self):
        """Test the __init__ method."""
        # Create a base agent
        agent = BaseAgent()
        
        # Check that the agent is created
        self.assertIsNotNone(agent)
    
    def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError."""
        # Create a base agent
        agent = BaseAgent()
        
        # Check that abstract methods raise NotImplementedError
        with self.assertRaises(NotImplementedError):
            agent.act({})
        
        with self.assertRaises(NotImplementedError):
            agent.learn({}, {}, 0.0, {}, False)
        
        with self.assertRaises(NotImplementedError):
            agent.save("")
        
        with self.assertRaises(NotImplementedError):
            agent.load("")


class TestRandomAgent(unittest.TestCase):
    """Test the RandomAgent class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a random agent
        self.node_ids = ["node1", "node2", "node3"]
        self.action_types = ["predict_blast_radius", "predict_vulnerability"]
        self.agent = RandomAgent(self.node_ids, self.action_types)
    
    def test_init(self):
        """Test the __init__ method."""
        # Check that the agent has the expected attributes
        self.assertEqual(self.agent.node_ids, self.node_ids)
        self.assertEqual(self.agent.action_types, self.action_types)
    
    def test_act_blast_radius(self):
        """Test the act method with a blast radius prediction action."""
        # Use a fixed seed for reproducibility
        with patch("random.choice", side_effect=["predict_blast_radius", "node1"]):
            with patch("random.randint", return_value=2):
                with patch("random.sample", return_value=["node2", "node3"]):
                    # Act
                    action = self.agent.act({})
                    
                    # Check that the action has the expected keys
                    self.assertIn("type", action)
                    self.assertIn("node_id", action)
                    self.assertIn("radius", action)
                    
                    # Check that the action has the expected values
                    self.assertEqual(action["type"], "predict_blast_radius")
                    self.assertEqual(action["node_id"], "node1")
                    self.assertEqual(action["radius"], ["node2", "node3"])
    
    def test_act_vulnerability(self):
        """Test the act method with a vulnerability prediction action."""
        # Use a fixed seed for reproducibility
        with patch("random.choice", side_effect=["predict_vulnerability", "node1", "sql_injection"]):
            with patch("random.random", return_value=0.8):
                # Act
                action = self.agent.act({})
                
                # Check that the action has the expected keys
                self.assertIn("type", action)
                self.assertIn("node_id", action)
                self.assertIn("vulnerability_type", action)
                self.assertIn("confidence", action)
                
                # Check that the action has the expected values
                self.assertEqual(action["type"], "predict_vulnerability")
                self.assertEqual(action["node_id"], "node1")
                self.assertEqual(action["vulnerability_type"], "sql_injection")
                self.assertEqual(action["confidence"], 0.8)
    
    def test_learn(self):
        """Test the learn method."""
        # The random agent doesn't learn, so this should be a no-op
        # Just check that it doesn't raise an exception
        self.agent.learn({}, {}, 0.0, {}, False)
    
    def test_save_load(self):
        """Test the save and load methods."""
        # The random agent doesn't save or load state, so these should be no-ops
        # Just check that they don't raise exceptions
        self.agent.save("")
        self.agent.load("")


class TestQTableAgent(unittest.TestCase):
    """Test the QTableAgent class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a Q-table agent
        self.node_ids = ["node1", "node2", "node3"]
        self.action_types = ["predict_blast_radius", "predict_vulnerability"]
        self.agent = QTableAgent(self.node_ids, self.action_types)
    
    def test_init(self):
        """Test the __init__ method."""
        # Check that the agent has the expected attributes
        self.assertEqual(self.agent.node_ids, self.node_ids)
        self.assertEqual(self.agent.action_types, self.action_types)
        self.assertEqual(self.agent.learning_rate, 0.1)
        self.assertEqual(self.agent.discount_factor, 0.99)
        self.assertEqual(self.agent.epsilon, 0.1)
        self.assertEqual(self.agent.q_table, {})
    
    def test_create_action_space(self):
        """Test the _create_action_space method."""
        # Create the action space
        action_space = self.agent._create_action_space()
        
        # Check that the action space has the expected length
        expected_length = len(self.node_ids) + len(self.node_ids) * 4  # 4 vulnerability types
        self.assertEqual(len(action_space), expected_length)
        
        # Check that the action space has the expected types
        action_types = set(action["type"] for action in action_space)
        self.assertEqual(action_types, set(self.action_types))
    
    def test_state_to_key(self):
        """Test the _state_to_key method."""
        # Define a state
        state = {"total_nodes": 3, "total_edges": 2}
        
        # Convert to key
        key = self.agent._state_to_key(state)
        
        # Check that the key has the expected format
        self.assertEqual(key, "nodes:3,edges:2")
    
    def test_action_to_key(self):
        """Test the _action_to_key method."""
        # Define actions
        blast_radius_action = {
            "type": "predict_blast_radius",
            "node_id": "node1",
            "radius": ["node2", "node3"],
        }
        
        vulnerability_action = {
            "type": "predict_vulnerability",
            "node_id": "node1",
            "vulnerability_type": "sql_injection",
            "confidence": 0.8,
        }
        
        # Convert to keys
        blast_radius_key = self.agent._action_to_key(blast_radius_action)
        vulnerability_key = self.agent._action_to_key(vulnerability_action)
        
        # Check that the keys have the expected format
        self.assertEqual(blast_radius_key, "predict_blast_radius:node1")
        self.assertEqual(vulnerability_key, "predict_vulnerability:node1:sql_injection")
    
    def test_get_q_value(self):
        """Test the _get_q_value method."""
        # Define a state and action
        state = {"total_nodes": 3, "total_edges": 2}
        action = {
            "type": "predict_blast_radius",
            "node_id": "node1",
            "radius": ["node2", "node3"],
        }
        
        # Get the Q-value (should be 0.0 initially)
        q_value = self.agent._get_q_value(state, action)
        
        # Check that the Q-value is 0.0
        self.assertEqual(q_value, 0.0)
        
        # Check that the state and action are added to the Q-table
        state_key = self.agent._state_to_key(state)
        action_key = self.agent._action_to_key(action)
        
        self.assertIn(state_key, self.agent.q_table)
        self.assertIn(action_key, self.agent.q_table[state_key])
    
    def test_set_q_value(self):
        """Test the _set_q_value method."""
        # Define a state and action
        state = {"total_nodes": 3, "total_edges": 2}
        action = {
            "type": "predict_blast_radius",
            "node_id": "node1",
            "radius": ["node2", "node3"],
        }
        
        # Set the Q-value
        self.agent._set_q_value(state, action, 0.5)
        
        # Check that the Q-value is set
        state_key = self.agent._state_to_key(state)
        action_key = self.agent._action_to_key(action)
        
        self.assertEqual(self.agent.q_table[state_key][action_key], 0.5)
    
    def test_act_random(self):
        """Test the act method when choosing a random action."""
        # Use a fixed seed for reproducibility
        with patch("random.random", return_value=0.05):  # 5% chance of random action
            with patch("random.choice", return_value={
                "type": "predict_blast_radius",
                "node_id": "node1",
            }):
                with patch("random.randint", return_value=2):
                    with patch("random.sample", return_value=["node2", "node3"]):
                        # Act
                        action = self.agent.act({})
                        
                        # Check that the action has the expected keys
                        self.assertIn("type", action)
                        self.assertIn("node_id", action)
                        self.assertIn("radius", action)
                        
                        # Check that the action has the expected values
                        self.assertEqual(action["type"], "predict_blast_radius")
                        self.assertEqual(action["node_id"], "node1")
                        self.assertEqual(action["radius"], ["node2", "node3"])
    
    def test_act_best(self):
        """Test the act method when choosing the best action."""
        # Set up a Q-table with some values
        state = {"total_nodes": 3, "total_edges": 2}
        state_key = self.agent._state_to_key(state)
        
        self.agent.q_table[state_key] = {
            "predict_blast_radius:node1": 0.1,
            "predict_blast_radius:node2": 0.3,  # Best action
            "predict_vulnerability:node1:sql_injection": 0.2,
        }
        
        # Use a fixed seed for reproducibility
        with patch("random.random", return_value=0.5):  # 50% chance of best action
            with patch("random.sample", return_value=["node3"]):
                # Act
                action = self.agent.act(state)
                
                # Check that the action has the expected keys
                self.assertIn("type", action)
                self.assertIn("node_id", action)
                self.assertIn("radius", action)
                
                # Check that the action has the expected values
                self.assertEqual(action["type"], "predict_blast_radius")
                self.assertEqual(action["node_id"], "node2")
    
    def test_learn(self):
        """Test the learn method."""
        # Define a state, action, and next state
        state = {"total_nodes": 3, "total_edges": 2}
        action = {
            "type": "predict_blast_radius",
            "node_id": "node1",
            "radius": ["node2", "node3"],
        }
        next_state = {"total_nodes": 3, "total_edges": 3}
        reward = 0.5
        
        # Learn
        self.agent.learn(state, action, reward, next_state, False)
        
        # Check that the Q-value is updated
        state_key = self.agent._state_to_key(state)
        action_key = self.agent._action_to_key(action)
        
        # Expected Q-value after update
        # Q(s,a) = Q(s,a) + learning_rate * (reward + discount_factor * max_next_q - Q(s,a))
        # Q(s,a) = 0.0 + 0.1 * (0.5 + 0.99 * 0.0 - 0.0) = 0.05
        self.assertAlmostEqual(self.agent.q_table[state_key][action_key], 0.05)
    
    def test_save_load(self):
        """Test the save and load methods."""
        # Set up a Q-table with some values
        state = {"total_nodes": 3, "total_edges": 2}
        action = {
            "type": "predict_blast_radius",
            "node_id": "node1",
            "radius": ["node2", "node3"],
        }
        
        self.agent._set_q_value(state, action, 0.5)
        
        # Create a temporary file for saving
        with tempfile.NamedTemporaryFile(delete=False) as f:
            try:
                # Save the agent
                self.agent.save(f.name)
                
                # Create a new agent
                new_agent = QTableAgent(self.node_ids, self.action_types)
                
                # Load the agent
                new_agent.load(f.name)
                
                # Check that the Q-table is loaded
                state_key = new_agent._state_to_key(state)
                action_key = new_agent._action_to_key(action)
                
                self.assertEqual(new_agent.q_table[state_key][action_key], 0.5)
                
                # Check that the other parameters are loaded
                self.assertEqual(new_agent.learning_rate, self.agent.learning_rate)
                self.assertEqual(new_agent.discount_factor, self.agent.discount_factor)
                self.assertEqual(new_agent.epsilon, self.agent.epsilon)
            finally:
                # Clean up
                os.unlink(f.name)


if __name__ == "__main__":
    unittest.main() 
