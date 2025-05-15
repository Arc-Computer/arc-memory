"""
Script to run and test the reinforcement learning pipeline.

This script provides utilities to run the RL pipeline for both
training and inference.
"""

import argparse
import logging
import os
import time
from typing import Dict, List, Any, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from arc_memory.sdk.core import Arc
from arc_memory.schema.models import ComponentNode
from arc_memory.rl.environment import ArcEnvironment
from arc_memory.rl.agent import RandomAgent, QTableAgent
from arc_memory.rl.reward import MultiComponentReward
from arc_memory.rl.training import RLTrainer, ExperienceBuffer, collect_experiences, train_from_buffer

logger = logging.getLogger(__name__)


def setup_logging():
    """Set up logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("rl_pipeline.log")
        ]
    )


def plot_training_metrics(metrics: Dict[str, Any], save_dir: str):
    """
    Plot training metrics.
    
    Args:
        metrics: Training metrics
        save_dir: Directory to save plots
    """
    os.makedirs(save_dir, exist_ok=True)
    
    # Plot episode rewards
    plt.figure(figsize=(10, 6))
    plt.plot(metrics["episode_rewards"])
    plt.title("Episode Rewards")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.savefig(os.path.join(save_dir, "episode_rewards.png"))
    plt.close()
    
    # Plot episode lengths
    plt.figure(figsize=(10, 6))
    plt.plot(metrics["episode_lengths"])
    plt.title("Episode Lengths")
    plt.xlabel("Episode")
    plt.ylabel("Length")
    plt.savefig(os.path.join(save_dir, "episode_lengths.png"))
    plt.close()
    
    # Plot action counts
    plt.figure(figsize=(10, 6))
    for action_type, counts in metrics["action_counts"].items():
        plt.plot(counts, label=action_type)
    plt.title("Action Counts")
    plt.xlabel("Episode")
    plt.ylabel("Count")
    plt.legend()
    plt.savefig(os.path.join(save_dir, "action_counts.png"))
    plt.close()
    
    # Plot reward components
    plt.figure(figsize=(10, 6))
    for component, values in metrics["reward_components"].items():
        if values:  # Check if the list is not empty
            plt.plot(values, label=component)
    plt.title("Reward Components")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.legend()
    plt.savefig(os.path.join(save_dir, "reward_components.png"))
    plt.close()


def create_test_components(num_components: int = 5) -> List[ComponentNode]:
    """
    Create test components for RL training when no real components are available.
    
    Args:
        num_components: Number of test components to create
        
    Returns:
        List of ComponentNode objects
    """
    return [
        ComponentNode(
            id=f"test_component_{i}",
            title=f"Test Component {i}",
            name=f"Test Component {i}",
            description=f"A test component for RL training {i}",
            service_id=None,
            files=[],
            responsibilities=[f"test_{i}"]
        )
        for i in range(num_components)
    ]


def initialize_pipeline(sdk: Arc, agent_type: str = "qtable") -> Tuple[ArcEnvironment, Any, MultiComponentReward]:
    """
    Initialize the RL pipeline.
    
    Args:
        sdk: Arc SDK instance
        agent_type: Type of agent to use (random or qtable)
        
    Returns:
        Tuple of (environment, agent, reward_function)
    """
    # Create the environment
    env = ArcEnvironment(sdk)
    
    # Create the reward function
    reward_function = MultiComponentReward()
    
    # Get all components as potential action targets
    components = sdk.get_architecture_components()
    
    # If no components found, create test components
    if not components:
        logger.info("No components found. Creating test components...")
        test_components = create_test_components()
        for comp in test_components:
            sdk.add_nodes_and_edges([comp], [])
        components = test_components
    
    component_ids = [comp.id if hasattr(comp, 'id') else comp["id"] for comp in components]
    logger.info(f"Using {len(component_ids)} components for actions")
    
    # Create the agent
    action_types = ["predict_blast_radius", "predict_vulnerability"]
    
    if agent_type == "random":
        agent = RandomAgent(component_ids, action_types)
    elif agent_type == "qtable":
        agent = QTableAgent(component_ids, action_types)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    return env, agent, reward_function


def train_pipeline(sdk: Arc, num_episodes: int = 100, agent_type: str = "qtable",
                  save_dir: str = "models", plot_dir: str = "plots") -> Dict[str, Any]:
    """
    Train the RL pipeline.
    
    Args:
        sdk: Arc SDK instance
        num_episodes: Number of episodes to train for
        agent_type: Type of agent to use (random or qtable)
        save_dir: Directory to save models
        plot_dir: Directory to save plots
        
    Returns:
        Training metrics
    """
    # Build the knowledge graph if empty
    components = sdk.get_architecture_components()
    if not components:
        logger.info("Building knowledge graph...")
        try:
            sdk.build(include_github=True, include_architecture=True, use_llm=False)
            components = sdk.get_architecture_components()
        except Exception as e:
            logger.warning(f"Failed to build knowledge graph with error: {e}")
            logger.info("Continuing with basic repository structure...")
            
        if not components:
            # Create test components
            test_components = create_test_components(num_components=1)
            sdk.add_nodes_and_edges(test_components, [])
            components = test_components
    
    # Initialize the pipeline
    env, agent, reward_function = initialize_pipeline(sdk, agent_type)
    
    # Create the trainer
    trainer = RLTrainer(env, agent, reward_function, save_dir)
    
    # Train the agent
    metrics = trainer.train(num_episodes=num_episodes)
    
    # Plot metrics
    plot_training_metrics(metrics, plot_dir)
    
    return metrics


def evaluate_pipeline(sdk: Arc, agent_path: str, agent_type: str = "qtable",
                    num_episodes: int = 10) -> Dict[str, Any]:
    """
    Evaluate the RL pipeline.
    
    Args:
        sdk: Arc SDK instance
        agent_path: Path to the agent
        agent_type: Type of agent to use (random or qtable)
        num_episodes: Number of episodes to evaluate for
        
    Returns:
        Evaluation metrics
    """
    # Initialize the pipeline
    env, agent, reward_function = initialize_pipeline(sdk, agent_type)
    
    # Load the agent
    agent.load(agent_path)
    
    # Create the trainer
    trainer = RLTrainer(env, agent, reward_function)
    
    # Evaluate the agent
    metrics = trainer.evaluate(num_episodes=num_episodes)
    
    return metrics


def collect_and_train_offline(sdk: Arc, num_collection_episodes: int = 10,
                             num_training_epochs: int = 10, agent_type: str = "qtable",
                             save_dir: str = "models", buffer_path: Optional[str] = None) -> None:
    """
    Collect experiences and train offline.
    
    Args:
        sdk: Arc SDK instance
        num_collection_episodes: Number of episodes to collect experiences for
        num_training_epochs: Number of epochs to train for
        agent_type: Type of agent to use (random or qtable)
        save_dir: Directory to save models
        buffer_path: Path to load the buffer from (optional)
    """
    # Initialize the pipeline
    env, agent, reward_function = initialize_pipeline(sdk, agent_type)
    
    # Load or collect experiences
    if buffer_path and os.path.exists(buffer_path):
        buffer = ExperienceBuffer()
        buffer.load(buffer_path)
        logger.info(f"Loaded buffer from {buffer_path}")
    else:
        # Use random agent for collection to ensure exploration
        collection_env, collection_agent, collection_reward = initialize_pipeline(sdk, "random")
        buffer = collect_experiences(collection_env, collection_agent, collection_reward,
                                   num_episodes=num_collection_episodes)
        
        # Save the buffer
        if buffer_path:
            buffer.save(buffer_path)
            logger.info(f"Saved buffer to {buffer_path}")
    
    # Train from buffer
    train_from_buffer(agent, buffer, num_epochs=num_training_epochs)
    
    # Save the agent
    os.makedirs(save_dir, exist_ok=True)
    agent.save(os.path.join(save_dir, f"offline_trained_agent.json"))
    logger.info(f"Saved agent to {save_dir}")


def demo_pipeline(sdk: Arc, agent_path: str, agent_type: str = "qtable",
                 num_steps: int = 10) -> None:
    """
    Run a demo of the RL pipeline.
    
    Args:
        sdk: Arc SDK instance
        agent_path: Path to the agent
        agent_type: Type of agent to use (random or qtable)
        num_steps: Number of steps to run for
    """
    # Initialize the pipeline
    env, agent, reward_function = initialize_pipeline(sdk, agent_type)
    
    # Load the agent
    agent.load(agent_path)
    
    # Run the demo
    state = env.reset()
    total_reward = 0
    
    for step in range(num_steps):
        # Get action from agent
        action = agent.act(state)
        
        # Take step in environment
        next_state, reward, done, info = env.step(action)
        
        # Update total reward
        total_reward += reward
        
        # Print step information
        print(f"\nStep {step + 1}:")
        print(f"Action: {action}")
        print(f"Reward: {reward}")
        print(f"Total Reward: {total_reward}")
        
        if done:
            print("\nEpisode finished early")
            break
        
        # Update state
        state = next_state
        
        # Small delay for readability
        time.sleep(1)


def main():
    """Run the RL pipeline."""
    setup_logging()
    
    parser = argparse.ArgumentParser(description="Run the RL pipeline")
    parser.add_argument("--mode", choices=["train", "evaluate", "collect", "demo"],
                      default="train", help="Mode to run the pipeline in")
    parser.add_argument("--num_episodes", type=int, default=100, help="Number of episodes")
    parser.add_argument("--agent_type", choices=["random", "qtable"], default="qtable",
                      help="Type of agent to use")
    parser.add_argument("--save_dir", default="models", help="Directory to save models")
    parser.add_argument("--plot_dir", default="plots", help="Directory to save plots")
    parser.add_argument("--agent_path", help="Path to the agent")
    parser.add_argument("--buffer_path", help="Path to the buffer")
    parser.add_argument("--num_training_epochs", type=int, default=10,
                      help="Number of epochs to train for in offline mode")
    parser.add_argument("--num_steps", type=int, default=10, help="Number of steps to run for in demo mode")
    parser.add_argument("--repo_path", default=".", help="Path to the repository to analyze")
    
    args = parser.parse_args()
    
    # Initialize the SDK with the repository path
    sdk = Arc(args.repo_path)
    
    if args.mode == "train":
        train_pipeline(sdk, num_episodes=args.num_episodes, agent_type=args.agent_type,
                     save_dir=args.save_dir, plot_dir=args.plot_dir)
    
    elif args.mode == "evaluate":
        if not args.agent_path:
            raise ValueError("agent_path is required for evaluate mode")
        
        metrics = evaluate_pipeline(sdk, args.agent_path, agent_type=args.agent_type,
                                  num_episodes=args.num_episodes)
        
        logger.info(f"Evaluation metrics: {metrics}")
    
    elif args.mode == "collect":
        collect_and_train_offline(sdk, num_collection_episodes=args.num_episodes,
                                num_training_epochs=args.num_training_epochs,
                                agent_type=args.agent_type, save_dir=args.save_dir,
                                buffer_path=args.buffer_path)
    
    elif args.mode == "demo":
        if not args.agent_path:
            raise ValueError("agent_path is required for demo mode")
        
        demo_pipeline(sdk, args.agent_path, agent_type=args.agent_type,
                    num_steps=args.num_steps)


if __name__ == "__main__":
    main() 
