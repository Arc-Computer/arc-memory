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
from arc_memory.rl.reward import MultiComponentReward, BinaryBlastRadiusReward
from arc_memory.rl.training import RLTrainer, ExperienceBuffer, collect_experiences, train_from_buffer
from arc_memory.rl.data_provider import GitHubDataProvider

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
    
    # Plot binary reward distribution (for BinaryBlastRadiusReward)
    if "binary_rewards" in metrics:
        plt.figure(figsize=(10, 6))
        rewards = metrics["binary_rewards"]
        zero_count = rewards.count(0.0)
        one_count = rewards.count(1.0)
        plt.bar(["0.0", "1.0"], [zero_count, one_count])
        plt.title("Binary Reward Distribution")
        plt.xlabel("Reward Value")
        plt.ylabel("Count")
        plt.savefig(os.path.join(save_dir, "binary_rewards.png"))
        plt.close()


def create_test_components(num_components: int = 5) -> List[ComponentNode]:
    """
    Create test components for RL training when no real components are available.
    
    Args:
        num_components: Number of test components to create
        
    Returns:
        List of ComponentNode objects
    """
    test_components = []
    
    # Common file extensions for simulating a real codebase
    file_extensions = [".py", ".c", ".cpp", ".h", ".js", ".ts", ".html", ".css", ".md", ".json"]
    
    for i in range(num_components):
        # Create a component with a realistic name
        component_name = f"test_component_{i}"
        
        # Generate realistic file paths for this component
        component_files = []
        # Each component has 3-7 files
        num_files = np.random.randint(3, 8)
        
        for j in range(num_files):
            # Pick a random file extension
            ext = np.random.choice(file_extensions)
            # Create a file path that mimics a real file structure
            file_path = f"{component_name}/src/{component_name}_{j}{ext}"
            component_files.append(file_path)
            
            # Some components might have test files
            if np.random.random() < 0.3:  # 30% chance
                test_file_path = f"{component_name}/tests/test_{component_name}_{j}{ext}"
                component_files.append(test_file_path)
                
        # Create the component with files
        component = ComponentNode(
            id=component_name,
            title=f"Test Component {i}",
            name=f"Test Component {i}",
            description=f"A test component for RL training {i}",
            service_id=None,
            files=component_files,
            responsibilities=[f"test_{i}"]
        )
        
        test_components.append(component)
        
    return test_components


def initialize_github_data_provider(github_token: str, repo_owner: str, repo_name: str) -> Optional[GitHubDataProvider]:
    """
    Initialize the GitHub data provider.
    
    Args:
        github_token: GitHub API token
        repo_owner: Repository owner
        repo_name: Repository name
        
    Returns:
        GitHubDataProvider instance or None if initialization fails
    """
    if not github_token:
        logger.warning("GitHub token not provided. GitHub data provider will not be initialized.")
        return None
        
    try:
        return GitHubDataProvider(github_token, repo_owner, repo_name)
    except Exception as e:
        logger.error(f"Failed to initialize GitHub data provider: {e}")
        return None


def initialize_pipeline(sdk: Arc, agent_type: str = "qtable", reward_type: str = "multi",
                       github_token: Optional[str] = None, repo_owner: str = "tensorflow",
                       repo_name: str = "tensorflow", use_temporal_data: bool = False,
                       start_date: str = "2020-01-01", end_date: str = "2020-06-30",
                       binary_threshold: float = 0.3) -> Tuple[ArcEnvironment, Any, Any]:
    """
    Initialize the RL pipeline.
    
    Args:
        sdk: Arc SDK instance
        agent_type: Type of agent to use (random or qtable)
        reward_type: Type of reward function to use (multi or binary)
        github_token: GitHub API token
        repo_owner: Repository owner
        repo_name: Repository name
        use_temporal_data: Whether to use temporal data
        start_date: Start date for temporal data
        end_date: End date for temporal data
        binary_threshold: Threshold for binary reward function
        
    Returns:
        Tuple of (environment, agent, reward_function)
    """
    # Initialize GitHub data provider if needed
    github_data_provider = None
    if use_temporal_data and github_token:
        github_data_provider = initialize_github_data_provider(github_token, repo_owner, repo_name)
    
    # Create the environment
    env = ArcEnvironment(sdk, github_data_provider)
    
    # Load temporal data if available
    if github_data_provider and use_temporal_data:
        env.load_temporal_graph(start_date, end_date)
    
    # Create the reward function
    if reward_type == "binary":
        reward_function = BinaryBlastRadiusReward(threshold=binary_threshold)
    else:
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
    # Since we are focusing on blast radius prediction only, we'll use only that action type
    action_types = ["predict_blast_radius"]
    
    if agent_type == "random":
        agent = RandomAgent(component_ids, action_types)
    elif agent_type == "qtable":
        agent = QTableAgent(component_ids, action_types)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    return env, agent, reward_function


def train_pipeline(sdk: Arc, num_episodes: int = 100, agent_type: str = "qtable",
                  reward_type: str = "multi", save_dir: str = "models", plot_dir: str = "plots",
                  github_token: Optional[str] = None, repo_owner: str = "tensorflow",
                  repo_name: str = "tensorflow", use_temporal_data: bool = False,
                  start_date: str = "2020-01-01", end_date: str = "2020-06-30",
                  binary_threshold: float = 0.7) -> Dict[str, Any]:
    """
    Train the RL pipeline.
    
    Args:
        sdk: Arc SDK instance
        num_episodes: Number of episodes to train for
        agent_type: Type of agent to use (random or qtable)
        reward_type: Type of reward function to use (multi or binary)
        save_dir: Directory to save models
        plot_dir: Directory to save plots
        github_token: GitHub API token
        repo_owner: Repository owner
        repo_name: Repository name
        use_temporal_data: Whether to use temporal data
        start_date: Start date for temporal data
        end_date: End date for temporal data
        binary_threshold: Threshold for binary reward function
        
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
            test_components = create_test_components(num_components=10)
            sdk.add_nodes_and_edges(test_components, [])
            components = test_components
    
    # Initialize the pipeline
    env, agent, reward_function = initialize_pipeline(
        sdk=sdk,
        agent_type=agent_type,
        reward_type=reward_type,
        github_token=github_token,
        repo_owner=repo_owner,
        repo_name=repo_name,
        use_temporal_data=use_temporal_data,
        start_date=start_date,
        end_date=end_date,
        binary_threshold=binary_threshold
    )
    
    # Create the trainer
    trainer = RLTrainer(env, agent, reward_function, save_dir)
    
    # Track binary rewards separately if using binary reward function
    if reward_type == "binary":
        trainer.metrics["binary_rewards"] = []
    
    # Train the agent
    metrics = trainer.train(num_episodes=num_episodes)
    
    # Plot metrics
    plot_training_metrics(metrics, plot_dir)
    
    return metrics


def evaluate_pipeline(sdk: Arc, agent_path: str, agent_type: str = "qtable",
                    reward_type: str = "multi", num_episodes: int = 10,
                    github_token: Optional[str] = None, repo_owner: str = "tensorflow",
                    repo_name: str = "tensorflow", use_temporal_data: bool = False,
                    start_date: str = "2020-01-01", end_date: str = "2020-06-30",
                    binary_threshold: float = 0.7) -> Dict[str, Any]:
    """
    Evaluate the RL pipeline.
    
    Args:
        sdk: Arc SDK instance
        agent_path: Path to the agent to load
        agent_type: Type of agent to use (random or qtable)
        reward_type: Type of reward function to use (multi or binary)
        num_episodes: Number of episodes to evaluate for
        github_token: GitHub API token
        repo_owner: Repository owner
        repo_name: Repository name
        use_temporal_data: Whether to use temporal data
        start_date: Start date for temporal data
        end_date: End date for temporal data
        binary_threshold: Threshold for binary reward function
        
    Returns:
        Evaluation metrics
    """
    # Initialize the pipeline
    env, agent, reward_function = initialize_pipeline(
        sdk=sdk,
        agent_type=agent_type,
        reward_type=reward_type,
        github_token=github_token,
        repo_owner=repo_owner,
        repo_name=repo_name,
        use_temporal_data=use_temporal_data,
        start_date=start_date,
        end_date=end_date,
        binary_threshold=binary_threshold
    )
    
    # Load the agent
    agent.load(agent_path)
    
    # Create the trainer for evaluation
    trainer = RLTrainer(env, agent, reward_function)
    
    # Evaluate the agent
    metrics = trainer.evaluate(num_episodes=num_episodes)
    
    return metrics


def demo_pipeline(sdk: Arc, agent_path: str, agent_type: str = "qtable",
                reward_type: str = "multi", num_steps: int = 10,
                github_token: Optional[str] = None, repo_owner: str = "tensorflow",
                repo_name: str = "tensorflow", use_temporal_data: bool = False,
                start_date: str = "2020-01-01", end_date: str = "2020-06-30",
                binary_threshold: float = 0.7) -> None:
    """
    Run a demo of the RL pipeline.
    
    Args:
        sdk: Arc SDK instance
        agent_path: Path to the agent to load
        agent_type: Type of agent to use (random or qtable)
        reward_type: Type of reward function to use (multi or binary)
        num_steps: Number of steps to run
        github_token: GitHub API token
        repo_owner: Repository owner
        repo_name: Repository name
        use_temporal_data: Whether to use temporal data
        start_date: Start date for temporal data
        end_date: End date for temporal data
        binary_threshold: Threshold for binary reward function
    """
    # Initialize the pipeline
    env, agent, reward_function = initialize_pipeline(
        sdk=sdk,
        agent_type=agent_type,
        reward_type=reward_type,
        github_token=github_token,
        repo_owner=repo_owner,
        repo_name=repo_name,
        use_temporal_data=use_temporal_data,
        start_date=start_date,
        end_date=end_date,
        binary_threshold=binary_threshold
    )
    
    # Load the agent
    agent.load(agent_path)
    
    # Run a demo
    state = env.observe()
    
    logger.info("Starting demo...")
    
    for step in range(num_steps):
        # Choose an action
        action = agent.act(state)
        
        # Print the action
        logger.info(f"Step {step + 1}/{num_steps}")
        logger.info(f"Action: {action}")
        
        # Take a step in the environment
        next_state, reward, done, info = env.step(action)
        
        # Calculate reward using the reward function
        reward = reward_function.calculate_reward(state, action, next_state, info)
        
        # Print the reward and info
        logger.info(f"Reward: {reward:.4f}")
        logger.info(f"Info: {info}")
        logger.info("---")
        
        # Update state
        state = next_state
        
        if done:
            break


def main():
    """Main entry point."""
    # Set up logging
    setup_logging()
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run the RL pipeline")
    parser.add_argument("--mode", type=str, choices=["train", "evaluate", "demo"], required=True,
                      help="Mode to run the pipeline in")
    parser.add_argument("--num_episodes", type=int, default=100,
                      help="Number of episodes to train/evaluate for")
    parser.add_argument("--num_steps", type=int, default=10,
                      help="Number of steps to run in demo mode")
    parser.add_argument("--agent_type", type=str, choices=["random", "qtable"], default="qtable",
                      help="Type of agent to use")
    parser.add_argument("--reward_type", type=str, choices=["multi", "binary"], default="binary",
                      help="Type of reward function to use")
    parser.add_argument("--agent_path", type=str, default=None,
                      help="Path to the agent to load (for evaluate/demo modes)")
    parser.add_argument("--save_dir", type=str, default="models",
                      help="Directory to save models")
    parser.add_argument("--plot_dir", type=str, default="plots",
                      help="Directory to save plots")
    parser.add_argument("--github_token", type=str, default=None,
                      help="GitHub API token")
    parser.add_argument("--repo_owner", type=str, default="tensorflow",
                      help="GitHub repository owner")
    parser.add_argument("--repo_name", type=str, default="tensorflow",
                      help="GitHub repository name")
    parser.add_argument("--use_temporal_data", action="store_true",
                      help="Whether to use temporal data")
    parser.add_argument("--start_date", type=str, default="2020-01-01",
                      help="Start date for temporal data (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default="2020-06-30",
                      help="End date for temporal data (YYYY-MM-DD)")
    parser.add_argument("--binary_threshold", type=float, default=0.7,
                      help="Threshold for binary reward function")
    parser.add_argument("--repo_path", type=str, default=".",
                      help="Path to the repository to analyze with Arc SDK")
    
    args = parser.parse_args()
    
    # Create Arc SDK
    sdk = Arc(repo_path=args.repo_path)
    
    if args.mode == "train":
        train_pipeline(
            sdk=sdk,
            num_episodes=args.num_episodes,
            agent_type=args.agent_type,
            reward_type=args.reward_type,
            save_dir=args.save_dir,
            plot_dir=args.plot_dir,
            github_token=args.github_token,
            repo_owner=args.repo_owner,
            repo_name=args.repo_name,
            use_temporal_data=args.use_temporal_data,
            start_date=args.start_date,
            end_date=args.end_date,
            binary_threshold=args.binary_threshold
        )
    
    elif args.mode == "evaluate":
        if not args.agent_path:
            logger.error("Agent path required for evaluate mode")
            return
        
        metrics = evaluate_pipeline(
            sdk=sdk,
            agent_path=args.agent_path,
            agent_type=args.agent_type,
            reward_type=args.reward_type,
            num_episodes=args.num_episodes,
            github_token=args.github_token,
            repo_owner=args.repo_owner,
            repo_name=args.repo_name,
            use_temporal_data=args.use_temporal_data,
            start_date=args.start_date,
            end_date=args.end_date,
            binary_threshold=args.binary_threshold
        )
        
        logger.info(f"Evaluation metrics: {metrics}")
    
    elif args.mode == "demo":
        if not args.agent_path:
            logger.error("Agent path required for demo mode")
            return
        
        demo_pipeline(
            sdk=sdk,
            agent_path=args.agent_path,
            agent_type=args.agent_type,
            reward_type=args.reward_type,
            num_steps=args.num_steps,
            github_token=args.github_token,
            repo_owner=args.repo_owner,
            repo_name=args.repo_name,
            use_temporal_data=args.use_temporal_data,
            start_date=args.start_date,
            end_date=args.end_date,
            binary_threshold=args.binary_threshold
        )


if __name__ == "__main__":
    main() 
