"""
Tests for the reward module.
"""

import unittest
from unittest.mock import MagicMock, patch

from arc_memory.rl.reward import RewardFunction, MultiComponentReward


class TestRewardFunction(unittest.TestCase):
    """Test the RewardFunction class."""
    
    def test_init(self):
        """Test the __init__ method."""
        # Create a reward function
        reward_function = RewardFunction()
        
        # Check that the reward function is created
        self.assertIsNotNone(reward_function)
    
    def test_calculate_reward(self):
        """Test that calculate_reward raises NotImplementedError."""
        # Create a reward function
        reward_function = RewardFunction()
        
        # Check that calculate_reward raises NotImplementedError
        with self.assertRaises(NotImplementedError):
            reward_function.calculate_reward({}, {}, {}, {})


class TestMultiComponentReward(unittest.TestCase):
    """Test the MultiComponentReward class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a multi-component reward function
        self.reward_function = MultiComponentReward()
    
    def test_init_default_weights(self):
        """Test the __init__ method with default weights."""
        # Check that the reward function has the expected weights
        self.assertEqual(self.reward_function.weights["correctness"], 1.0)
        self.assertEqual(self.reward_function.weights["completion"], 1.0)
        self.assertEqual(self.reward_function.weights["reasoning"], 1.0)
        self.assertEqual(self.reward_function.weights["tool_use"], 1.0)
        self.assertEqual(self.reward_function.weights["kg_enrichment"], 1.0)
        self.assertEqual(self.reward_function.weights["coordination"], 1.0)
    
    def test_init_custom_weights(self):
        """Test the __init__ method with custom weights."""
        # Create a reward function with custom weights
        weights = {
            "correctness": 2.0,
            "completion": 0.5,
            "reasoning": 1.5,
            "tool_use": 0.8,
            "kg_enrichment": 1.2,
            "coordination": 0.7,
        }
        
        reward_function = MultiComponentReward(weights=weights)
        
        # Check that the reward function has the expected weights
        self.assertEqual(reward_function.weights["correctness"], 2.0)
        self.assertEqual(reward_function.weights["completion"], 0.5)
        self.assertEqual(reward_function.weights["reasoning"], 1.5)
        self.assertEqual(reward_function.weights["tool_use"], 0.8)
        self.assertEqual(reward_function.weights["kg_enrichment"], 1.2)
        self.assertEqual(reward_function.weights["coordination"], 0.7)
    
    def test_calculate_reward(self):
        """Test the calculate_reward method."""
        # Mock the component methods
        mock_values = {
            "_calculate_correctness_reward": 0.8,
            "_calculate_completion_reward": 0.6,
            "_calculate_reasoning_reward": 0.7,
            "_calculate_tool_use_reward": 0.9,
            "_calculate_kg_enrichment_reward": 0.5,
            "_calculate_coordination_reward": 0.4
        }
        
        with patch.multiple(
            self.reward_function,
            **{name: MagicMock(return_value=value) for name, value in mock_values.items()}
        ):
            # Calculate reward
            reward = self.reward_function.calculate_reward({}, {}, {}, {})
            
            # Check that the reward is the sum of the components
            expected_reward = sum(mock_values.values())
            self.assertEqual(reward, expected_reward)
    
    def test_calculate_reward_weighted(self):
        """Test the calculate_reward method with weights."""
        # Create a reward function with custom weights
        weights = {
            "correctness": 2.0,
            "completion": 0.5,
            "reasoning": 1.5,
            "tool_use": 0.8,
            "kg_enrichment": 1.2,
            "coordination": 0.7,
        }
        
        reward_function = MultiComponentReward(weights=weights)
        
        # Mock the component methods
        mock_values = {
            "_calculate_correctness_reward": 0.8,
            "_calculate_completion_reward": 0.6,
            "_calculate_reasoning_reward": 0.7,
            "_calculate_tool_use_reward": 0.9,
            "_calculate_kg_enrichment_reward": 0.5,
            "_calculate_coordination_reward": 0.4
        }
        
        with patch.multiple(
            reward_function,
            **{name: MagicMock(return_value=value) for name, value in mock_values.items()}
        ):
            # Calculate reward
            reward = reward_function.calculate_reward({}, {}, {}, {})
            
            # Check that the reward is the weighted sum of the components
            expected_reward = (
                mock_values["_calculate_correctness_reward"] * weights["correctness"] +
                mock_values["_calculate_completion_reward"] * weights["completion"] +
                mock_values["_calculate_reasoning_reward"] * weights["reasoning"] +
                mock_values["_calculate_tool_use_reward"] * weights["tool_use"] +
                mock_values["_calculate_kg_enrichment_reward"] * weights["kg_enrichment"] +
                mock_values["_calculate_coordination_reward"] * weights["coordination"]
            )
            self.assertEqual(reward, expected_reward)
    
    def test_calculate_correctness_reward_blast_radius(self):
        """Test the _calculate_correctness_reward method for blast radius prediction."""
        # Define the state, action, next state, and info
        state = {}
        action = {
            "type": "predict_blast_radius",
            "node_id": "node1",
            "radius": ["node2", "node3"],
        }
        next_state = {}
        info = {
            "blast_radius_precision": 0.8,
        }
        
        # Calculate reward
        reward = self.reward_function._calculate_correctness_reward(state, action, next_state, info)
        
        # Check that the reward is the precision
        self.assertEqual(reward, 0.8)
    
    def test_calculate_correctness_reward_vulnerability_correct(self):
        """Test the _calculate_correctness_reward method for correct vulnerability prediction."""
        # Define the state, action, next state, and info
        state = {}
        action = {
            "type": "predict_vulnerability",
            "node_id": "node1",
            "vulnerability_type": "sql_injection",
            "confidence": 0.8,
        }
        next_state = {}
        info = {
            "vulnerability_prediction_correct": True,
        }
        
        # Calculate reward
        reward = self.reward_function._calculate_correctness_reward(state, action, next_state, info)
        
        # Check that the reward is the confidence
        self.assertEqual(reward, 0.8)
    
    def test_calculate_correctness_reward_vulnerability_incorrect(self):
        """Test the _calculate_correctness_reward method for incorrect vulnerability prediction."""
        # Define the state, action, next state, and info
        state = {}
        action = {
            "type": "predict_vulnerability",
            "node_id": "node1",
            "vulnerability_type": "sql_injection",
            "confidence": 0.8,
        }
        next_state = {}
        info = {
            "vulnerability_prediction_correct": False,
        }
        
        # Calculate reward
        reward = self.reward_function._calculate_correctness_reward(state, action, next_state, info)
        
        # Check that the reward is the negative confidence
        self.assertEqual(reward, -0.8)
    
    def test_calculate_completion_reward(self):
        """Test the _calculate_completion_reward method."""
        # Define the state, action, next state, and info
        state = {}
        action = {}
        next_state = {}
        info = {
            "action_count": 5,
        }
        
        # Calculate reward
        reward = self.reward_function._calculate_completion_reward(state, action, next_state, info)
        
        # Check that the reward is calculated correctly
        # reward = min(1.0, 1.0 / (1.0 + 0.1 * action_count))
        expected_reward = min(1.0, 1.0 / (1.0 + 0.1 * 5))
        self.assertEqual(reward, expected_reward)
    
    def test_calculate_reasoning_reward_no_explanation(self):
        """Test the _calculate_reasoning_reward method with no explanation."""
        # Define the state, action, next state, and info
        state = {}
        action = {}
        next_state = {}
        info = {}
        
        # Calculate reward
        reward = self.reward_function._calculate_reasoning_reward(state, action, next_state, info)
        
        # Check that the reward is 0.0 (no explanation)
        self.assertEqual(reward, 0.0)
    
    def test_calculate_reasoning_reward_good_explanation(self):
        """Test the _calculate_reasoning_reward method with a good explanation."""
        # Define the state, action, next state, and info
        state = {}
        action = {
            "explanation": "This is a good explanation.",
        }
        next_state = {}
        info = {}
        
        # Calculate reward
        reward = self.reward_function._calculate_reasoning_reward(state, action, next_state, info)
        
        # Check that the reward is 1.0 (good explanation)
        self.assertEqual(reward, 1.0)
    
    def test_calculate_reasoning_reward_too_short_explanation(self):
        """Test the _calculate_reasoning_reward method with a too short explanation."""
        # Define the state, action, next state, and info
        state = {}
        action = {
            "explanation": "Too short.",
        }
        next_state = {}
        info = {}
        
        # Calculate reward
        reward = self.reward_function._calculate_reasoning_reward(state, action, next_state, info)
        
        # Check that the reward is less than 1.0 (explanation too short)
        self.assertLess(reward, 1.0)
    
    def test_calculate_reasoning_reward_too_long_explanation(self):
        """Test the _calculate_reasoning_reward method with a too long explanation."""
        # Define the state, action, next state, and info
        state = {}
        action = {
            "explanation": "This is a very long explanation that is more than twenty words and should therefore receive a lower reward because it is too verbose and not concise enough.",
        }
        next_state = {}
        info = {}
        
        # Calculate reward
        reward = self.reward_function._calculate_reasoning_reward(state, action, next_state, info)
        
        # Check that the reward is less than 1.0 (explanation too long)
        self.assertLess(reward, 1.0)
    
    def test_calculate_tool_use_reward_blast_radius_high_impact(self):
        """Test the _calculate_tool_use_reward method for blast radius prediction of a high-impact node."""
        # Define the state, action, next state, and info
        state = {}
        action = {
            "type": "predict_blast_radius",
            "node_id": "node1",
        }
        next_state = {}
        info = {
            "node_is_high_impact": True,
        }
        
        # Calculate reward
        reward = self.reward_function._calculate_tool_use_reward(state, action, next_state, info)
        
        # Check that the reward is 1.0 (high-impact node)
        self.assertEqual(reward, 1.0)
    
    def test_calculate_tool_use_reward_blast_radius_low_impact(self):
        """Test the _calculate_tool_use_reward method for blast radius prediction of a low-impact node."""
        # Define the state, action, next state, and info
        state = {}
        action = {
            "type": "predict_blast_radius",
            "node_id": "node1",
        }
        next_state = {}
        info = {
            "node_is_high_impact": False,
        }
        
        # Calculate reward
        reward = self.reward_function._calculate_tool_use_reward(state, action, next_state, info)
        
        # Check that the reward is 0.2 (low-impact node)
        self.assertEqual(reward, 0.2)
    
    def test_calculate_tool_use_reward_vulnerability_security_concerns(self):
        """Test the _calculate_tool_use_reward method for vulnerability prediction of a node with security concerns."""
        # Define the state, action, next state, and info
        state = {}
        action = {
            "type": "predict_vulnerability",
            "node_id": "node1",
        }
        next_state = {}
        info = {
            "node_has_security_concerns": True,
        }
        
        # Calculate reward
        reward = self.reward_function._calculate_tool_use_reward(state, action, next_state, info)
        
        # Check that the reward is 1.0 (node with security concerns)
        self.assertEqual(reward, 1.0)
    
    def test_calculate_tool_use_reward_vulnerability_no_security_concerns(self):
        """Test the _calculate_tool_use_reward method for vulnerability prediction of a node without security concerns."""
        # Define the state, action, next state, and info
        state = {}
        action = {
            "type": "predict_vulnerability",
            "node_id": "node1",
        }
        next_state = {}
        info = {
            "node_has_security_concerns": False,
        }
        
        # Calculate reward
        reward = self.reward_function._calculate_tool_use_reward(state, action, next_state, info)
        
        # Check that the reward is 0.2 (node without security concerns)
        self.assertEqual(reward, 0.2)
    
    def test_calculate_kg_enrichment_reward(self):
        """Test the _calculate_kg_enrichment_reward method."""
        # Define the state, action, next state, and info
        state = {
            "total_nodes": 3,
            "total_edges": 2,
        }
        action = {}
        next_state = {
            "total_nodes": 4,
            "total_edges": 3,
        }
        info = {}
        
        # Calculate reward
        reward = self.reward_function._calculate_kg_enrichment_reward(state, action, next_state, info)
        
        # Check that the reward is calculated correctly
        # nodes_reward = min(1.0, kg_nodes_delta * 0.1)
        # edges_reward = min(1.0, kg_edges_delta * 0.1)
        expected_reward = min(1.0, 1 * 0.1) + min(1.0, 1 * 0.1)
        self.assertEqual(reward, expected_reward)
    
    def test_calculate_coordination_reward(self):
        """Test the _calculate_coordination_reward method."""
        # Define the state, action, next state, and info
        state = {}
        action = {}
        next_state = {}
        info = {
            "unblocked_agents": 3,
        }
        
        # Calculate reward
        reward = self.reward_function._calculate_coordination_reward(state, action, next_state, info)
        
        # Check that the reward is calculated correctly
        # reward = min(1.0, unblocked_agents * 0.5)
        expected_reward = min(1.0, 3 * 0.5)
        self.assertEqual(reward, expected_reward)


if __name__ == "__main__":
    unittest.main() 
