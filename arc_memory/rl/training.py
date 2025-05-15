"""
Training module for the reinforcement learning pipeline.

This module implements the training pipeline for the RL agent.
"""

import logging
import os
import time
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

from arc_memory.rl.environment import ArcEnvironment
from arc_memory.rl.agent import BaseAgent, RandomAgent, QTableAgent
from arc_memory.rl.reward import RewardFunction, MultiComponentReward

logger = logging.getLogger(__name__)

class RLTrainer:
    """
    Trainer for reinforcement learning agents.
    
    This class handles the training loop, evaluation, and saving/loading of agents.
    """
    
    def __init__(self, env: ArcEnvironment, agent: BaseAgent, reward_function: RewardFunction,
                 save_dir: str = "models"):
        """
        Initialize the trainer.
        
        Args:
            env: The environment
            agent: The agent
            reward_function: The reward function
            save_dir: Directory to save models
        """
        self.env = env
        self.agent = agent
        self.reward_function = reward_function
        self.save_dir = save_dir
        
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Initialize metrics
        self.metrics = {
            "episode_rewards": [],
            "episode_lengths": [],
            "action_counts": {},
            "reward_components": {
                "correctness": [],
                "completion": [],
                "reasoning": [],
                "tool_use": [],
                "kg_enrichment": [],
                "coordination": [],
            }
        }
    
    def train(self, num_episodes: int = 100, max_steps_per_episode: int = 100,
              eval_interval: int = 10, save_interval: int = 10) -> Dict[str, Any]:
        """
        Train the agent.
        
        Args:
            num_episodes: Number of episodes to train for
            max_steps_per_episode: Maximum number of steps per episode
            eval_interval: Number of episodes between evaluations
            save_interval: Number of episodes between saving the agent
            
        Returns:
            Training metrics
        """
        logger.info(f"Starting training for {num_episodes} episodes")
        
        for episode in range(num_episodes):
            # Reset the environment
            state = self.env.observe()
            
            episode_reward = 0
            episode_reward_components = {
                "correctness": 0,
                "completion": 0,
                "reasoning": 0,
                "tool_use": 0,
                "kg_enrichment": 0,
                "coordination": 0,
            }
            
            # Action counts for this episode
            action_counts = {}
            
            for step in range(max_steps_per_episode):
                # Choose an action
                action = self.agent.act(state)
                
                # Count actions by type
                action_type = action.get("type", "unknown")
                if action_type in action_counts:
                    action_counts[action_type] += 1
                else:
                    action_counts[action_type] = 1
                
                # Take a step in the environment
                next_state, env_reward, done, info = self.env.step(action)
                
                # Update info with action count
                info["action_count"] = step + 1
                
                # Calculate reward
                reward = self.reward_function.calculate_reward(state, action, next_state, info)
                
                # Record reward components if using MultiComponentReward
                if isinstance(self.reward_function, MultiComponentReward):
                    # Calculate individual components and record them
                    r_corr = self.reward_function._calculate_correctness_reward(state, action, next_state, info)
                    r_comp = self.reward_function._calculate_completion_reward(state, action, next_state, info)
                    r_reas = self.reward_function._calculate_reasoning_reward(state, action, next_state, info)
                    r_tool = self.reward_function._calculate_tool_use_reward(state, action, next_state, info)
                    r_kg = self.reward_function._calculate_kg_enrichment_reward(state, action, next_state, info)
                    r_causal = self.reward_function._calculate_coordination_reward(state, action, next_state, info)
                    
                    # Record components
                    episode_reward_components["correctness"] += r_corr
                    episode_reward_components["completion"] += r_comp
                    episode_reward_components["reasoning"] += r_reas
                    episode_reward_components["tool_use"] += r_tool
                    episode_reward_components["kg_enrichment"] += r_kg
                    episode_reward_components["coordination"] += r_causal
                
                # Learn from the experience
                self.agent.learn(state, action, reward, next_state, done)
                
                # Update state and reward
                state = next_state
                episode_reward += reward
                
                if done:
                    break
            
            # Record metrics
            self.metrics["episode_rewards"].append(episode_reward)
            self.metrics["episode_lengths"].append(step + 1)
            
            # Record action counts
            for action_type, count in action_counts.items():
                if action_type not in self.metrics["action_counts"]:
                    self.metrics["action_counts"][action_type] = []
                self.metrics["action_counts"][action_type].append(count)
            
            # Record reward components if using MultiComponentReward
            if isinstance(self.reward_function, MultiComponentReward):
                for component, value in episode_reward_components.items():
                    self.metrics["reward_components"][component].append(value)
            
            # Log progress
            if (episode + 1) % 10 == 0:
                logger.info(f"Episode {episode + 1}/{num_episodes}, Reward: {episode_reward:.2f}")
            
            # Save the agent periodically
            if (episode + 1) % save_interval == 0:
                save_path = os.path.join(self.save_dir, f"agent_episode_{episode + 1}.json")
                self.agent.save(save_path)
                logger.info(f"Saved agent to {save_path}")
            
            # Evaluate the agent periodically
            if (episode + 1) % eval_interval == 0:
                eval_metrics = self.evaluate(num_episodes=5)
                logger.info(f"Evaluation metrics: {eval_metrics}")
        
        logger.info("Training completed")
        
        return self.metrics
    
    def evaluate(self, num_episodes: int = 10, max_steps_per_episode: int = 100) -> Dict[str, Any]:
        """
        Evaluate the agent.
        
        Args:
            num_episodes: Number of episodes to evaluate for
            max_steps_per_episode: Maximum number of steps per episode
            
        Returns:
            Evaluation metrics
        """
        logger.info(f"Evaluating agent for {num_episodes} episodes")
        
        rewards = []
        lengths = []
        
        for episode in range(num_episodes):
            # Reset the environment
            state = self.env.observe()
            
            episode_reward = 0
            
            for step in range(max_steps_per_episode):
                # Choose an action
                action = self.agent.act(state)
                
                # Take a step in the environment
                next_state, env_reward, done, info = self.env.step(action)
                
                # Update info with action count
                info["action_count"] = step + 1
                
                # Calculate reward
                reward = self.reward_function.calculate_reward(state, action, next_state, info)
                
                # Update state and reward
                state = next_state
                episode_reward += reward
                
                if done:
                    break
            
            rewards.append(episode_reward)
            lengths.append(step + 1)
        
        # Calculate metrics
        avg_reward = np.mean(rewards)
        avg_length = np.mean(lengths)
        
        eval_metrics = {
            "avg_reward": avg_reward,
            "avg_length": avg_length,
            "rewards": rewards,
            "lengths": lengths,
        }
        
        return eval_metrics
    
    def save_agent(self, name: str) -> str:
        """
        Save the agent.
        
        Args:
            name: Name of the agent
            
        Returns:
            Path to the saved agent
        """
        path = os.path.join(self.save_dir, f"{name}.json")
        self.agent.save(path)
        return path
    
    def load_agent(self, path: str) -> None:
        """
        Load the agent.
        
        Args:
            path: Path to the agent
        """
        self.agent.load(path)


class ExperienceBuffer:
    """
    Buffer to store experiences for offline RL training.
    
    This class implements a simple experience buffer to store experiences
    (state, action, reward, next_state, done) for offline RL training.
    """
    
    def __init__(self, capacity: int = 10000):
        """
        Initialize the experience buffer.
        
        Args:
            capacity: Maximum number of experiences to store
        """
        self.capacity = capacity
        self.buffer = []
        self.position = 0
    
    def add(self, state: Dict[str, Any], action: Dict[str, Any], reward: float,
            next_state: Dict[str, Any], done: bool, info: Dict[str, Any]) -> None:
        """
        Add an experience to the buffer.
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether the episode is done
            info: Additional information
        """
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        
        self.buffer[self.position] = (state, action, reward, next_state, done, info)
        self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size: int) -> List[Tuple[Dict[str, Any], Dict[str, Any], float, Dict[str, Any], bool, Dict[str, Any]]]:
        """
        Sample a batch of experiences from the buffer.
        
        Args:
            batch_size: Number of experiences to sample
            
        Returns:
            A batch of experiences
        """
        if len(self.buffer) == 0:
            return []
            
        batch_size = min(batch_size, len(self.buffer))
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        
        return [self.buffer[i] for i in indices]
    
    def save(self, path: str) -> None:
        """
        Save the buffer to disk.
        
        Args:
            path: Path to save to
        """
        import pickle
        
        with open(path, "wb") as f:
            pickle.dump(self.buffer, f)
    
    def load(self, path: str) -> None:
        """
        Load the buffer from disk.
        
        Args:
            path: Path to load from
        """
        import pickle
        
        with open(path, "rb") as f:
            self.buffer = pickle.load(f)
        
        self.position = len(self.buffer) % self.capacity


def collect_experiences(env: ArcEnvironment, agent: BaseAgent, reward_function: RewardFunction,
                       num_episodes: int = 10, max_steps_per_episode: int = 100) -> ExperienceBuffer:
    """
    Collect experiences using the agent.
    
    Args:
        env: The environment
        agent: The agent
        reward_function: The reward function
        num_episodes: Number of episodes to collect
        max_steps_per_episode: Maximum number of steps per episode
        
    Returns:
        The experience buffer
    """
    buffer = ExperienceBuffer()
    
    for episode in range(num_episodes):
        # Reset the environment
        state = env.observe()
        
        for step in range(max_steps_per_episode):
            # Choose an action
            action = agent.act(state)
            
            # Take a step in the environment
            next_state, env_reward, done, info = env.step(action)
            
            # Update info with action count
            info["action_count"] = step + 1
            
            # Calculate reward
            reward = reward_function.calculate_reward(state, action, next_state, info)
            
            # Add to buffer
            buffer.add(state, action, reward, next_state, done, info)
            
            # Update state
            state = next_state
            
            if done:
                break
    
    return buffer


def train_from_buffer(agent: BaseAgent, buffer: ExperienceBuffer, num_epochs: int = 10, batch_size: int = 32) -> None:
    """
    Train the agent from the experience buffer.
    
    Args:
        agent: The agent
        buffer: The experience buffer
        num_epochs: Number of epochs to train for
        batch_size: Batch size
    """
    logger.info(f"Training agent from buffer for {num_epochs} epochs")
    
    for epoch in range(num_epochs):
        # Sample a batch from the buffer
        batch = buffer.sample(batch_size)
        
        # Train on each experience
        for state, action, reward, next_state, done, info in batch:
            agent.learn(state, action, reward, next_state, done)
        
        if (epoch + 1) % 10 == 0:
            logger.info(f"Epoch {epoch + 1}/{num_epochs}")
    
    logger.info("Buffer training completed") 
