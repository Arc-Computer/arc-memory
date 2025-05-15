"""
Reward functions for the reinforcement learning pipeline.

This module implements various reward functions for the RL pipeline,
including the multi-component reward function described in the roadmap.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class RewardFunction:
    """
    Base class for reward functions.
    """
    
    def __init__(self):
        """Initialize the reward function."""
        pass
    
    def calculate_reward(self, state: Dict[str, Any], action: Dict[str, Any], 
                         next_state: Dict[str, Any], info: Dict[str, Any]) -> float:
        """
        Calculate the reward for a state-action-next_state tuple.
        
        Args:
            state: The current state
            action: The action taken
            next_state: The next state
            info: Additional information
            
        Returns:
            The calculated reward
        """
        raise NotImplementedError("Subclasses must implement calculate_reward()")


class MultiComponentReward(RewardFunction):
    """
    Multi-component reward function.
    
    R = Rcorr + Rcomp + Rreas + Rtool + Rkg + Rcausal
    
    Where:
    - Rcorr (Correctness): Rewards for code changes passing tests and static analysis
    - Rcomp (Completion): Progress toward overall goal (e.g., % of services migrated)
    - Rreas (Reasoning Quality): Quality of intermediate reasoning or planning steps
    - Rtool (Tool Use): Efficiency in selecting and using appropriate tools
    - Rkg (KG Enrichment): Adding valuable provenance to the knowledge graph
    - Rcausal (Coordination): Successfully unblocking other agents' operations
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize the multi-component reward function.
        
        Args:
            weights: Weights for each component, defaults to equal weights
        """
        super().__init__()
        
        # Default weights (equal for all components)
        self.weights = weights or {
            "correctness": 1.0,
            "completion": 1.0,
            "reasoning": 1.0,
            "tool_use": 1.0,
            "kg_enrichment": 1.0,
            "coordination": 1.0,
        }
    
    def calculate_reward(self, state: Dict[str, Any], action: Dict[str, Any], 
                         next_state: Dict[str, Any], info: Dict[str, Any]) -> float:
        """
        Calculate the multi-component reward.
        
        Args:
            state: The current state
            action: The action taken
            next_state: The next state
            info: Additional information
            
        Returns:
            The calculated reward
        """
        # Calculate individual components
        r_corr = self._calculate_correctness_reward(state, action, next_state, info)
        r_comp = self._calculate_completion_reward(state, action, next_state, info)
        r_reas = self._calculate_reasoning_reward(state, action, next_state, info)
        r_tool = self._calculate_tool_use_reward(state, action, next_state, info)
        r_kg = self._calculate_kg_enrichment_reward(state, action, next_state, info)
        r_causal = self._calculate_coordination_reward(state, action, next_state, info)
        
        # Apply weights and sum
        reward = (
            self.weights["correctness"] * r_corr +
            self.weights["completion"] * r_comp +
            self.weights["reasoning"] * r_reas +
            self.weights["tool_use"] * r_tool +
            self.weights["kg_enrichment"] * r_kg +
            self.weights["coordination"] * r_causal
        )
        
        return reward
    
    def _calculate_correctness_reward(self, state: Dict[str, Any], action: Dict[str, Any], 
                                     next_state: Dict[str, Any], info: Dict[str, Any]) -> float:
        """
        Calculate the correctness reward (Rcorr).
        
        Rewards for code changes passing tests and static analysis.
        
        Args:
            state: The current state
            action: The action taken
            next_state: The next state
            info: Additional information
            
        Returns:
            The correctness reward
        """
        # In a real implementation, we would check test results and static analysis
        # For this baseline, we'll use a simple heuristic based on the action
        
        action_type = action.get("type")
        
        if action_type == "predict_blast_radius":
            # For blast radius predictions, use the precision from info
            precision = info.get("blast_radius_precision", 0.0)
            return precision
        
        elif action_type == "predict_vulnerability":
            # For vulnerability predictions, use the outcome from info
            is_correct = info.get("vulnerability_prediction_correct", False)
            confidence = action.get("confidence", 0.5)
            
            if is_correct:
                return confidence
            else:
                return -confidence
        
        else:
            logger.warning(f"Unknown action type for correctness reward: {action_type}")
            return 0.0
    
    def _calculate_completion_reward(self, state: Dict[str, Any], action: Dict[str, Any], 
                                    next_state: Dict[str, Any], info: Dict[str, Any]) -> float:
        """
        Calculate the completion reward (Rcomp).
        
        Progress toward overall goal (e.g., % of services migrated).
        
        Args:
            state: The current state
            action: The action taken
            next_state: The next state
            info: Additional information
            
        Returns:
            The completion reward
        """
        # In a real implementation, we would check progress toward goals
        # For this baseline, we'll use a simple heuristic based on action count
        
        # Get the number of actions taken so far
        action_count = info.get("action_count", 0)
        
        # Simple progress metric based on action count
        # As more actions are taken, progress increases diminishingly
        if action_count == 0:
            return 0.0
        
        return min(1.0, 1.0 / (1.0 + 0.1 * action_count))
    
    def _calculate_reasoning_reward(self, state: Dict[str, Any], action: Dict[str, Any], 
                                   next_state: Dict[str, Any], info: Dict[str, Any]) -> float:
        """
        Calculate the reasoning quality reward (Rreas).
        
        Quality of intermediate reasoning or planning steps.
        
        Args:
            state: The current state
            action: The action taken
            next_state: The next state
            info: Additional information
            
        Returns:
            The reasoning quality reward
        """
        # In a real implementation, we would evaluate the quality of reasoning
        # For this baseline, we'll use a simple heuristic based on explanation quality
        
        # Check if action has an explanation
        has_explanation = "explanation" in action
        
        # Check explanation quality (in a real system, this would use NLP)
        explanation_quality = 0.0
        if has_explanation:
            explanation = action.get("explanation", "")
            explanation_length = len(explanation.split())
            
            # Simple quality metric based on length (5-20 words is ideal)
            if 5 <= explanation_length <= 20:
                explanation_quality = 1.0
            elif explanation_length < 5:
                explanation_quality = explanation_length / 5.0
            else:
                explanation_quality = max(0.0, 1.0 - (explanation_length - 20) / 30.0)
        
        return explanation_quality
    
    def _calculate_tool_use_reward(self, state: Dict[str, Any], action: Dict[str, Any], 
                                  next_state: Dict[str, Any], info: Dict[str, Any]) -> float:
        """
        Calculate the tool use reward (Rtool).
        
        Efficiency in selecting and using appropriate tools.
        
        Args:
            state: The current state
            action: The action taken
            next_state: The next state
            info: Additional information
            
        Returns:
            The tool use reward
        """
        # In a real implementation, we would evaluate the appropriateness of tools
        # For this baseline, we'll use a simple heuristic based on tool selection
        
        action_type = action.get("type")
        
        # Check if the action type is appropriate for the current state
        if action_type == "predict_blast_radius":
            # For blast radius predictions, check if the node is a high-impact node
            node_id = action.get("node_id", "")
            node_is_high_impact = info.get("node_is_high_impact", False)
            
            if node_is_high_impact:
                return 1.0
            else:
                return 0.2
        
        elif action_type == "predict_vulnerability":
            # For vulnerability predictions, check if the node has security concerns
            node_id = action.get("node_id", "")
            node_has_security_concerns = info.get("node_has_security_concerns", False)
            
            if node_has_security_concerns:
                return 1.0
            else:
                return 0.2
        
        else:
            logger.warning(f"Unknown action type for tool use reward: {action_type}")
            return 0.0
    
    def _calculate_kg_enrichment_reward(self, state: Dict[str, Any], action: Dict[str, Any], 
                                       next_state: Dict[str, Any], info: Dict[str, Any]) -> float:
        """
        Calculate the knowledge graph enrichment reward (Rkg).
        
        Adding valuable provenance to the knowledge graph.
        
        Args:
            state: The current state
            action: The action taken
            next_state: The next state
            info: Additional information
            
        Returns:
            The KG enrichment reward
        """
        # In a real implementation, we would evaluate the value of new KG entries
        # For this baseline, we'll use a simple heuristic based on new nodes/edges
        
        # Check if the action added nodes or edges to the KG
        kg_nodes_delta = next_state["total_nodes"] - state["total_nodes"]
        kg_edges_delta = next_state["total_edges"] - state["total_edges"]
        
        # Reward based on new nodes and edges
        nodes_reward = min(1.0, kg_nodes_delta * 0.1)
        edges_reward = min(1.0, kg_edges_delta * 0.1)
        
        return nodes_reward + edges_reward
    
    def _calculate_coordination_reward(self, state: Dict[str, Any], action: Dict[str, Any], 
                                      next_state: Dict[str, Any], info: Dict[str, Any]) -> float:
        """
        Calculate the coordination reward (Rcausal).
        
        Successfully unblocking other agents' operations.
        
        Args:
            state: The current state
            action: The action taken
            next_state: The next state
            info: Additional information
            
        Returns:
            The coordination reward
        """
        # In a real implementation, we would evaluate coordination with other agents
        # For this baseline, we'll use a simple heuristic
        
        # Check if the action unblocked other agents
        unblocked_agents = info.get("unblocked_agents", 0)
        
        # Reward based on unblocked agents
        return min(1.0, unblocked_agents * 0.5) 
