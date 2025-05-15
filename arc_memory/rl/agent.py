"""
Agent for the reinforcement learning pipeline.

This module implements the agent that interacts with the environment,
learns from experiences, and makes predictions.
"""

import logging
import random
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

class BaseAgent:
    """
    Base class for RL agents.
    """
    
    def __init__(self):
        """Initialize the base agent."""
        pass
    
    def act(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Choose an action based on the current state.
        
        Args:
            state: The current state
            
        Returns:
            The action to take
        """
        raise NotImplementedError("Subclasses must implement act()")
    
    def learn(self, state: Dict[str, Any], action: Dict[str, Any], 
              reward: float, next_state: Dict[str, Any], done: bool) -> None:
        """
        Learn from an experience tuple.
        
        Args:
            state: The current state
            action: The action taken
            reward: The reward received
            next_state: The next state
            done: Whether the episode is done
        """
        raise NotImplementedError("Subclasses must implement learn()")
    
    def save(self, path: str) -> None:
        """
        Save the agent to disk.
        
        Args:
            path: The path to save to
        """
        raise NotImplementedError("Subclasses must implement save()")
    
    def load(self, path: str) -> None:
        """
        Load the agent from disk.
        
        Args:
            path: The path to load from
        """
        raise NotImplementedError("Subclasses must implement load()")


class RandomAgent(BaseAgent):
    """
    A simple agent that takes random actions.
    
    This is a baseline agent that can be used for comparison.
    """
    
    def __init__(self, component_ids: List[str], action_types: List[str]):
        """
        Initialize the random agent.
        
        Args:
            component_ids: List of component IDs in the knowledge graph
            action_types: List of action types the agent can take
        """
        super().__init__()
        self.component_ids = component_ids
        self.action_types = action_types
        
    def act(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Choose a random action.
        
        Args:
            state: The current state
            
        Returns:
            A random action
        """
        action_type = random.choice(self.action_types)
        component_id = random.choice(self.component_ids)
        
        if action_type == "predict_blast_radius":
            # Random blast radius prediction
            # In a real system, this would be more sophisticated
            radius_size = random.randint(1, 5)
            radius = random.sample(self.component_ids, min(radius_size, len(self.component_ids)))
            
            return {
                "type": action_type,
                "component_id": component_id,
                "radius": radius
            }
        
        elif action_type == "predict_vulnerability":
            # Random vulnerability prediction
            vulnerability_types = ["sql_injection", "xss", "buffer_overflow", "null_pointer"]
            vulnerability_type = random.choice(vulnerability_types)
            confidence = random.random()
            
            return {
                "type": action_type,
                "component_id": component_id,
                "vulnerability_type": vulnerability_type,
                "confidence": confidence
            }
        
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return {"type": "unknown"}
    
    def learn(self, state: Dict[str, Any], action: Dict[str, Any], 
              reward: float, next_state: Dict[str, Any], done: bool) -> None:
        """
        The random agent doesn't learn, so this is a no-op.
        
        Args:
            state: The current state
            action: The action taken
            reward: The reward received
            next_state: The next state
            done: Whether the episode is done
        """
        pass
    
    def save(self, path: str) -> None:
        """
        The random agent has no state to save.
        
        Args:
            path: The path to save to
        """
        pass
    
    def load(self, path: str) -> None:
        """
        The random agent has no state to load.
        
        Args:
            path: The path to load from
        """
        pass


class QTableAgent(BaseAgent):
    """
    A simple Q-table based agent.
    
    This agent uses a Q-table to store the value of each state-action pair
    and uses an epsilon-greedy policy to balance exploration and exploitation.
    """
    
    def __init__(self, component_ids: List[str], action_types: List[str], 
                 learning_rate: float = 0.1, discount_factor: float = 0.99, 
                 epsilon: float = 0.1):
        """
        Initialize the Q-table agent.
        
        Args:
            component_ids: List of component IDs in the knowledge graph
            action_types: List of action types the agent can take
            learning_rate: The learning rate
            discount_factor: The discount factor
            epsilon: The epsilon value for epsilon-greedy policy
        """
        super().__init__()
        self.component_ids = component_ids
        self.action_types = action_types
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        
        # Initialize Q-table
        # In a real system, we would use a more sophisticated state representation
        # For this baseline, we'll use a simple dictionary-based Q-table
        self.q_table = {}
        
        # Initialize action space
        self.action_space = self._create_action_space()
        
    def _create_action_space(self) -> List[Dict[str, Any]]:
        """
        Create the action space.
        
        Returns:
            List of possible actions
        """
        actions = []
        
        # Add blast radius prediction actions
        for component_id in self.component_ids:
            actions.append({
                "type": "predict_blast_radius",
                "component_id": component_id,
                "radius": []  # Will be filled during act()
            })
            
        # Add vulnerability prediction actions
        vulnerability_types = ["sql_injection", "xss", "buffer_overflow", "null_pointer"]
        for component_id in self.component_ids:
            for vulnerability_type in vulnerability_types:
                actions.append({
                    "type": "predict_vulnerability",
                    "component_id": component_id,
                    "vulnerability_type": vulnerability_type,
                    "confidence": 0.5  # Will be updated during act()
                })
                
        return actions
    
    def _state_to_key(self, state: Dict[str, Any]) -> str:
        """
        Convert a state to a string key for the Q-table.
        
        Args:
            state: The state
            
        Returns:
            A string key
        """
        # In a real system, we would use a more sophisticated state representation
        # For this baseline, we'll use a simple string representation
        return f"nodes:{state['total_nodes']},edges:{state['total_edges']}"
    
    def _action_to_key(self, action: Dict[str, Any]) -> str:
        """
        Convert an action to a string key for the Q-table.
        
        Args:
            action: The action
            
        Returns:
            A string key
        """
        # In a real system, we would use a more sophisticated action representation
        # For this baseline, we'll use a simple string representation
        action_type = action["type"]
        component_id = action["component_id"]
        
        if action_type == "predict_blast_radius":
            return f"{action_type}:{component_id}"
        
        elif action_type == "predict_vulnerability":
            vulnerability_type = action["vulnerability_type"]
            return f"{action_type}:{component_id}:{vulnerability_type}"
        
        else:
            return str(action)
    
    def _get_q_value(self, state: Dict[str, Any], action: Dict[str, Any]) -> float:
        """
        Get the Q-value for a state-action pair.
        
        Args:
            state: The state
            action: The action
            
        Returns:
            The Q-value
        """
        state_key = self._state_to_key(state)
        action_key = self._action_to_key(action)
        
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        
        if action_key not in self.q_table[state_key]:
            self.q_table[state_key][action_key] = 0.0
        
        return self.q_table[state_key][action_key]
    
    def _set_q_value(self, state: Dict[str, Any], action: Dict[str, Any], value: float) -> None:
        """
        Set the Q-value for a state-action pair.
        
        Args:
            state: The state
            action: The action
            value: The Q-value
        """
        state_key = self._state_to_key(state)
        action_key = self._action_to_key(action)
        
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        
        self.q_table[state_key][action_key] = value
    
    def act(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Choose an action using epsilon-greedy policy.
        
        Args:
            state: The current state
            
        Returns:
            The action to take
        """
        # With probability epsilon, choose a random action
        if random.random() < self.epsilon:
            action_template = random.choice(self.action_space)
            
            # Fill in the details
            if action_template["type"] == "predict_blast_radius":
                # Random blast radius prediction
                radius_size = random.randint(1, 5)
                radius = random.sample(self.component_ids, min(radius_size, len(self.component_ids)))
                
                return {
                    "type": action_template["type"],
                    "component_id": action_template["component_id"],
                    "radius": radius
                }
            
            elif action_template["type"] == "predict_vulnerability":
                # Random vulnerability prediction
                confidence = random.random()
                
                return {
                    "type": action_template["type"],
                    "component_id": action_template["component_id"],
                    "vulnerability_type": action_template["vulnerability_type"],
                    "confidence": confidence
                }
            
            else:
                return action_template
        
        # Otherwise, choose the action with the highest Q-value
        state_key = self._state_to_key(state)
        
        # If we haven't seen this state before, choose a random action
        if state_key not in self.q_table:
            action_template = random.choice(self.action_space)
            
            # Fill in the details
            if action_template["type"] == "predict_blast_radius":
                # Random blast radius prediction
                radius_size = random.randint(1, 5)
                radius = random.sample(self.component_ids, min(radius_size, len(self.component_ids)))
                
                return {
                    "type": action_template["type"],
                    "component_id": action_template["component_id"],
                    "radius": radius
                }
            
            elif action_template["type"] == "predict_vulnerability":
                # Random vulnerability prediction
                confidence = random.random()
                
                return {
                    "type": action_template["type"],
                    "component_id": action_template["component_id"],
                    "vulnerability_type": action_template["vulnerability_type"],
                    "confidence": confidence
                }
            
            else:
                return action_template
        
        # Find the action with the highest Q-value
        best_action_key = max(self.q_table[state_key], key=self.q_table[state_key].get)
        best_action_parts = best_action_key.split(":")
        
        action_type = best_action_parts[0]
        component_id = best_action_parts[1]
        
        if action_type == "predict_blast_radius":
            # Use learned Q-values to determine the blast radius
            # In a real system, this would be more sophisticated
            radius_size = max(1, int(self._get_q_value(state, {"type": action_type, "component_id": component_id}) * 10))
            radius = random.sample(self.component_ids, min(radius_size, len(self.component_ids)))
            
            return {
                "type": action_type,
                "component_id": component_id,
                "radius": radius
            }
        
        elif action_type == "predict_vulnerability":
            vulnerability_type = best_action_parts[2]
            # Use learned Q-values to determine the confidence
            confidence = max(0.1, min(0.9, self._get_q_value(state, {
                "type": action_type, 
                "component_id": component_id, 
                "vulnerability_type": vulnerability_type
            }) + 0.5))
            
            return {
                "type": action_type,
                "component_id": component_id,
                "vulnerability_type": vulnerability_type,
                "confidence": confidence
            }
        
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return {"type": "unknown"}
    
    def learn(self, state: Dict[str, Any], action: Dict[str, Any], 
              reward: float, next_state: Dict[str, Any], done: bool) -> None:
        """
        Update the Q-table based on the experience.
        
        Args:
            state: The current state
            action: The action taken
            reward: The reward received
            next_state: The next state
            done: Whether the episode is done
        """
        # Get the current Q-value
        current_q = self._get_q_value(state, action)
        
        # Find the maximum Q-value for the next state
        next_state_key = self._state_to_key(next_state)
        
        if next_state_key in self.q_table and self.q_table[next_state_key]:
            max_next_q = max(self.q_table[next_state_key].values())
        else:
            max_next_q = 0.0
        
        # Calculate the new Q-value
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        # Update the Q-table
        self._set_q_value(state, action, new_q)
    
    def save(self, path: str) -> None:
        """
        Save the Q-table to disk.
        
        Args:
            path: The path to save to
        """
        import json
        
        # Convert the Q-table to a serializable format
        serializable_q_table = {}
        for state_key, actions in self.q_table.items():
            serializable_q_table[state_key] = {str(action_key): value for action_key, value in actions.items()}
        
        # Save to disk
        with open(path, "w") as f:
            json.dump({
                "q_table": serializable_q_table,
                "learning_rate": self.learning_rate,
                "discount_factor": self.discount_factor,
                "epsilon": self.epsilon,
            }, f, indent=2)
    
    def load(self, path: str) -> None:
        """
        Load the Q-table from disk.
        
        Args:
            path: The path to load from
        """
        import json
        
        # Load from disk
        with open(path, "r") as f:
            data = json.load(f)
        
        # Convert the serializable format back to the Q-table
        self.q_table = {}
        for state_key, actions in data["q_table"].items():
            self.q_table[state_key] = {action_key: value for action_key, value in actions.items()}
        
        self.learning_rate = data["learning_rate"]
        self.discount_factor = data["discount_factor"]
        self.epsilon = data["epsilon"] 
