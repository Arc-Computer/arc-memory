"""
Environment for the reinforcement learning pipeline.

This module implements the environment that represents the codebase state
and provides an interface for agents to interact with.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

from arc_memory.schema.models import Node, Edge, NodeType, ComponentNode
from arc_memory.sdk.core import Arc
from arc_memory.rl.data_provider import GitHubDataProvider

logger = logging.getLogger(__name__)

class ArcEnvironment:
    """
    Represents the environment for the RL agent to interact with.
    
    The environment encapsulates the state of the codebase through the Arc 
    knowledge graph. It provides methods to observe the state, take actions,
    and receive rewards.
    """
    
    def __init__(self, sdk: Arc, github_data_provider: Optional[GitHubDataProvider] = None):
        """
        Initialize the environment.
        
        Args:
            sdk: Arc SDK instance connected to the knowledge graph
            github_data_provider: Optional GitHub data provider for external repository data
        """
        self.sdk = sdk
        self.github_data_provider = github_data_provider
        self.current_state = None
        self.temporal_graph = None
        self._reset()
    
    def _reset(self):
        """Reset the environment to an initial state."""
        self.current_state = self._get_current_state()
        
    def reset(self):
        """Reset the environment to an initial state and return the state."""
        self._reset()
        return self.current_state
    
    def load_temporal_graph(self, start_date: str, end_date: str):
        """
        Load temporal graph data from GitHub repository.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        if self.github_data_provider:
            logger.info(f"Loading temporal graph from {start_date} to {end_date}")
            self.temporal_graph = self.github_data_provider.build_temporal_graph(start_date, end_date)
            
            # Import the data into Arc's knowledge graph
            self._import_temporal_graph()
        else:
            logger.warning("GitHub data provider not configured")
    
    def _import_temporal_graph(self):
        """Import temporal graph data into Arc's knowledge graph."""
        if not self.temporal_graph:
            logger.warning("No temporal graph to import")
            return
        
        # Import nodes
        sdk_components = []
        
        # First, build a mapping of component_id -> file_paths
        component_files = {}
        for edge in self.temporal_graph["edges"]:
            if edge["type"] == "belongs_to":
                component_id = edge["target"]
                file_path = edge["source"]
                
                if component_id not in component_files:
                    component_files[component_id] = []
                
                component_files[component_id].append(file_path)
        
        for node_data in self.temporal_graph["nodes"]:
            if node_data["type"] == "component":
                # Get file paths for this component
                component_id = node_data["id"]
                files = component_files.get(component_id, [])
                
                # Convert dict to ComponentNode instance with associated files
                component_node_obj = ComponentNode(
                    id=component_id,
                    title=node_data["name"],
                    name=node_data["name"],
                    description=f"Component from temporal graph: {node_data['name']}",
                    files=files,  # Set the files attribute based on belongs_to edges
                )
                sdk_components.append(component_node_obj)
        
        # Add components to knowledge graph
        if sdk_components:
            try:
                self.sdk.add_nodes_and_edges(sdk_components, [])
                logger.info(f"Imported {len(sdk_components)} components from temporal graph into Arc SDK")
                # Log file associations for debugging
                for comp in sdk_components:
                    file_count = len(comp.files) if hasattr(comp, 'files') else 0
                    logger.info(f"Component {comp.id} has {file_count} associated files")
            except Exception as e:
                logger.error(f"Failed to import components into Arc SDK: {e}", exc_info=True)
        else:
            logger.info("No components of type 'component' found in temporal graph to import.")
        
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
        reward = 0.0
        info = {}
        
        if action_type == "predict_blast_radius":
            reward, info = self._handle_blast_radius_prediction(action)
        # Vulnerability handling is disabled - using a simple return path instead of calling the method
        elif action_type == "predict_vulnerability":
            logger.warning("Vulnerability prediction is disabled in this version.")
            info = {
                "action_processed": "predict_vulnerability",
                "status": "disabled",
                "message": "Vulnerability prediction is disabled in this version."
            }
        else:
            logger.warning(f"Unknown or unexpected action type received: {action_type}. Ignoring.")
            # Optionally, you could assign a negative reward for unexpected actions
            # reward = -1.0 
            info = {"action_processed": action_type, "status": "ignored_unexpected_action"}
        
        # Update the current state
        self.current_state = self._get_current_state()
        
        # For now, episodes don't end
        done = False
        
        return self.current_state, reward, done, info
    
    def _handle_blast_radius_prediction(self, action: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Handle a blast radius prediction action.
        
        Args:
            action: The action containing the prediction
            
        Returns:
            Tuple of (reward, info dictionary)
        """
        # Extract prediction details
        component_id = action.get("component_id")
        predicted_radius = action.get("radius", [])
        
        info = {"action_processed": "predict_blast_radius"}
        
        try:
            # First, check if we can use GitHub data for blast radius
            actual_radius = []
            if self.github_data_provider and self.temporal_graph:
                # Try to find the component in the temporal graph
                component_files = self._get_component_files(component_id)
                
                if component_files:
                    # Use GitHub data to infer blast radius
                    for file_path in component_files:
                        file_radius = self.github_data_provider.infer_blast_radius(file_path)
                        actual_radius.extend(file_radius)
                    
                    # Remove duplicates
                    actual_radius = list(set(actual_radius))
                else:
                    logger.warning(f"No files found for component {component_id}")
            
            # Fall back to Arc impact analysis if GitHub data is not available
            if not actual_radius:
                # Get actual impact analysis
                impact_results = self.sdk.analyze_component_impact(
                    component_id=component_id,
                    max_depth=3
                )
                
                # Extract actual impacted components
                actual_radius = [result.component_id for result in impact_results]
            
            # Calculate reward metrics
            correct_predictions = set(predicted_radius).intersection(actual_radius)
            
            # Calculate precision with improved readability
            precision = 0
            if predicted_radius:
                precision = len(correct_predictions) / len(predicted_radius)
                
            recall = len(correct_predictions) / len(actual_radius) if actual_radius else 0
            
            # Store metrics in info
            info["blast_radius_precision"] = precision
            info["blast_radius_recall"] = recall
            info["predicted_radius_size"] = len(predicted_radius)
            info["actual_radius_size"] = len(actual_radius)
            info["correct_predictions"] = len(correct_predictions)
            
            # F1 score as reward
            if precision + recall > 0:
                reward = 2 * precision * recall / (precision + recall)
            else:
                reward = 0.0
                
        except Exception as e:
            logger.warning(f"Error analyzing component impact: {e}")
            reward = 0.0
            
        return reward, info
    
    def _get_component_files(self, component_id: str) -> List[str]:
        """
        Get files associated with a component.
        
        Args:
            component_id: ID of the component
            
        Returns:
            List of file paths
        """
        if not self.temporal_graph:
            return []
            
        # Find component in temporal graph
        component_node = None
        for node in self.temporal_graph["nodes"]:
            if node["id"] == component_id and node["type"] == "component":
                component_node = node
                break
                
        if not component_node:
            return []
            
        # Find files belonging to this component
        files = []
        for edge in self.temporal_graph["edges"]:
            if edge["type"] == "belongs_to" and edge["target"] == component_id:
                files.append(edge["source"])
                
        return files
        
    def _handle_vulnerability_prediction(self, action: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Handle a vulnerability prediction action.
        
        Args:
            action: The action containing the prediction
            
        Returns:
            Tuple of (reward, info dictionary)
        """
        # Extract prediction details
        component_id = action.get("component_id")
        vulnerability_type = action.get("vulnerability_type")
        confidence = action.get("confidence", 0.5)
        
        info = {
            "action_processed": "predict_vulnerability",
            "vulnerability_prediction_correct": False
        }
        
        try:
            # Get component details
            details = self.sdk.get_entity_details(component_id)
            
            # Check if details is a string (error case) or doesn't have properties
            if isinstance(details, str) or not hasattr(details, 'properties'):
                logger.warning(f"Invalid component details for {component_id}: {details}")
                return 0.0, info
            
            # Check for security-related properties or relationships
            has_security_concerns = any(
                "security" in str(prop).lower() or 
                "vulnerability" in str(prop).lower() or 
                "risk" in str(prop).lower()
                for prop in details.properties.values()
            )
            
            # Calculate reward based on prediction
            if has_security_concerns:
                # Correct prediction
                reward = confidence
                info["vulnerability_prediction_correct"] = True
            else:
                # Incorrect prediction
                reward = -confidence
            
        except Exception as e:
            logger.warning(f"Error checking vulnerability: {e}")
            reward = 0.0
            
        return reward, info
