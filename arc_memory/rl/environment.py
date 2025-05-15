"""
Environment for the reinforcement learning pipeline.

This module implements the environment that represents the codebase state
and provides an interface for agents to interact with.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

from arc_memory.schema.models import Node, Edge, NodeType
from arc_memory.sdk.core import ArcSDK

logger = logging.getLogger(__name__)

class ArcEnvironment:
    """
    Represents the environment for the RL agent to interact with.
    
    The environment encapsulates the state of the codebase through the Arc 
    knowledge graph. It provides methods to observe the state, take actions,
    and receive rewards.
    """
    
    def __init__(self, sdk: ArcSDK):
        """
        Initialize the environment.
        
        Args:
            sdk: Arc SDK instance connected to the knowledge graph
        """
        self.sdk = sdk
        self.current_state = None
        self._reset()
    
    def _reset(self):
        """Reset the environment to an initial state."""
        self.current_state = self._get_current_state()
        
    def _get_current_state(self) -> Dict[str, Any]:
        """
        Get the current state representation from the knowledge graph.
        
        Returns:
            A dictionary containing the current state representation
        """
        # This is a simplified state representation
        # In a more complex implementation, we would include more features
        
        # Get all code-related nodes
        code_nodes = self.sdk.get_nodes_by_type(NodeType.FILE)
        code_nodes.extend(self.sdk.get_nodes_by_type(NodeType.FUNCTION))
        code_nodes.extend(self.sdk.get_nodes_by_type(NodeType.CLASS))
        
        # Count node types
        node_type_counts = {}
        for node in code_nodes:
            node_type = node.node_type
            if node_type in node_type_counts:
                node_type_counts[node_type] += 1
            else:
                node_type_counts[node_type] = 1
        
        # Get edges to represent dependencies
        edges = self.sdk.get_edges_for_nodes([node.id for node in code_nodes])
        
        # Count edge types
        edge_type_counts = {}
        for edge in edges:
            edge_type = edge.edge_type
            if edge_type in edge_type_counts:
                edge_type_counts[edge_type] += 1
            else:
                edge_type_counts[edge_type] = 1
        
        # Create a simple state representation
        state = {
            "node_counts": node_type_counts,
            "edge_counts": edge_type_counts,
            "total_nodes": len(code_nodes),
            "total_edges": len(edges),
        }
        
        return state
    
    def observe(self) -> Dict[str, Any]:
        """
        Get the current observation of the environment.
        
        Returns:
            A dictionary containing the observation
        """
        return self.current_state
    
    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Take a step in the environment based on the action.
        
        Args:
            action: The action to take, represented as a dictionary
            
        Returns:
            A tuple of (next_state, reward, done, info)
        """
        # Process the action based on its type
        action_type = action.get("type")
        
        if action_type == "predict_blast_radius":
            reward = self._handle_blast_radius_prediction(action)
        elif action_type == "predict_vulnerability":
            reward = self._handle_vulnerability_prediction(action)
        else:
            logger.warning(f"Unknown action type: {action_type}")
            reward = 0.0
        
        # Update the current state
        self.current_state = self._get_current_state()
        
        # For now, episodes don't end
        done = False
        
        # Additional info
        info = {
            "action_processed": action_type,
        }
        
        return self.current_state, reward, done, info
    
    def _handle_blast_radius_prediction(self, action: Dict[str, Any]) -> float:
        """
        Handle a blast radius prediction action.
        
        Args:
            action: The action containing the prediction
            
        Returns:
            The reward for the action
        """
        # Extract prediction details
        node_id = action.get("node_id")
        predicted_radius = action.get("radius", [])
        
        # In a real implementation, we would compare with actual outcomes
        # For this baseline, we'll use a simple heuristic
        
        # Get actual connected nodes (simplified "ground truth")
        connected_nodes = self._get_connected_nodes(node_id)
        
        # Calculate reward based on prediction accuracy
        # This is a simplified reward calculation
        correct_predictions = set(predicted_radius).intersection(connected_nodes)
        precision = len(correct_predictions) / len(predicted_radius) if predicted_radius else 0
        recall = len(correct_predictions) / len(connected_nodes) if connected_nodes else 0
        
        # F1 score as reward
        if precision + recall > 0:
            reward = 2 * precision * recall / (precision + recall)
        else:
            reward = 0.0
            
        return reward
    
    def _handle_vulnerability_prediction(self, action: Dict[str, Any]) -> float:
        """
        Handle a vulnerability prediction action.
        
        Args:
            action: The action containing the prediction
            
        Returns:
            The reward for the action
        """
        # Extract prediction details
        node_id = action.get("node_id")
        vulnerability_type = action.get("vulnerability_type")
        confidence = action.get("confidence", 0.5)
        
        # In a real implementation, we would compare with actual outcomes
        # For this baseline, we'll use a simple heuristic
        
        # Simulate ground truth (in a real system, this would come from actual data)
        is_vulnerable = self._simulate_vulnerability(node_id, vulnerability_type)
        
        # Calculate reward based on prediction accuracy
        if is_vulnerable:
            # True positive
            reward = confidence
        else:
            # False positive
            reward = -confidence
            
        return reward
    
    def _get_connected_nodes(self, node_id: str) -> List[str]:
        """
        Get the nodes connected to the given node.
        
        Args:
            node_id: The ID of the node
            
        Returns:
            A list of connected node IDs
        """
        # Get edges for the node
        edges = self.sdk.get_edges_for_node(node_id)
        
        # Extract connected nodes
        connected_nodes = []
        for edge in edges:
            if edge.source_id == node_id:
                connected_nodes.append(edge.target_id)
            else:
                connected_nodes.append(edge.source_id)
                
        return connected_nodes
    
    def _simulate_vulnerability(self, node_id: str, vulnerability_type: str) -> bool:
        """
        Simulate whether a node has a specific vulnerability.
        
        Args:
            node_id: The ID of the node
            vulnerability_type: The type of vulnerability
            
        Returns:
            True if the node is vulnerable, False otherwise
        """
        # In a real system, this would be based on actual data
        # For this baseline, we'll use a random value with a low probability
        return np.random.random() < 0.1  # 10% chance of vulnerability 