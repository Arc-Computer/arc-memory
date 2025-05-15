"""
Environment for the reinforcement learning pipeline.

This module implements the environment that represents the codebase state
and provides an interface for agents to interact with.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

from arc_memory.schema.models import Node, Edge, NodeType
from arc_memory.sdk.core import Arc

logger = logging.getLogger(__name__)

class ArcEnvironment:
    """
    Represents the environment for the RL agent to interact with.
    
    The environment encapsulates the state of the codebase through the Arc 
    knowledge graph. It provides methods to observe the state, take actions,
    and receive rewards.
    """
    
    def __init__(self, sdk: Arc):
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
        
    def reset(self):
        """Reset the environment to an initial state and return the state."""
        self._reset()
        return self.current_state
        
    def _get_current_state(self) -> Dict[str, Any]:
        """
        Get the current state representation from the knowledge graph.
        
        Returns:
            A dictionary containing the current state representation
        """
        # Get repository ID
        repo_id = self.sdk.ensure_repository()
        
        # Get basic metrics
        total_nodes = self.sdk.get_node_count()
        total_edges = self.sdk.get_edge_count()
        
        # Get architecture components for different types
        components = self.sdk.get_architecture_components()
        
        # Count component types
        component_type_counts = {}
        for component in components:
            comp_type = component.get("type", "unknown")
            if comp_type in component_type_counts:
                component_type_counts[comp_type] += 1
            else:
                component_type_counts[comp_type] = 1
        
        # Create state representation
        state = {
            "repo_id": repo_id,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "component_counts": component_type_counts,
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
        component_id = action.get("component_id")
        predicted_radius = action.get("radius", [])
        
        try:
            # Get actual impact analysis
            impact_results = self.sdk.analyze_component_impact(
                component_id=component_id,
                max_depth=3
            )
            
            # Extract actual impacted components
            actual_radius = [result.component_id for result in impact_results]
            
            # Calculate reward based on prediction accuracy
            correct_predictions = set(predicted_radius).intersection(actual_radius)
            
            # Calculate precision with improved readability
            precision = 0
            if predicted_radius:
                precision = len(correct_predictions) / len(predicted_radius)
                
            recall = len(correct_predictions) / len(actual_radius) if actual_radius else 0
            
            # F1 score as reward
            if precision + recall > 0:
                reward = 2 * precision * recall / (precision + recall)
            else:
                reward = 0.0
                
        except Exception as e:
            logger.warning(f"Error analyzing component impact: {e}")
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
        component_id = action.get("component_id")
        vulnerability_type = action.get("vulnerability_type")
        confidence = action.get("confidence", 0.5)
        
        try:
            # Get component details
            details = self.sdk.get_entity_details(component_id)
            
            # Check for security-related properties or relationships
            has_security_concerns = any(
                "security" in str(prop).lower() or 
                "vulnerability" in str(prop).lower() or 
                "risk" in str(prop).lower()
                for prop in details.properties.values()
            )
            
            # Calculate reward based on prediction
            if has_security_concerns:
                # True positive
                reward = confidence
            else:
                # False positive
                reward = -confidence
                
        except Exception as e:
            logger.warning(f"Error getting entity details: {e}")
            reward = 0.0
            
        return reward
