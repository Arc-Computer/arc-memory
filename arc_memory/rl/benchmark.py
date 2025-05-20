"""
Benchmark script for the reinforcement learning pipeline.

This script provides utilities to benchmark the RL pipeline on
different datasets and configurations.
"""

import logging
import os
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np

from arc_memory.sdk.core import Arc
from arc_memory.rl.environment import ArcEnvironment
from arc_memory.rl.agent import RandomAgent, QTableAgent
from arc_memory.rl.reward import BinaryBlastRadiusReward
from arc_memory.rl.training import RLTrainer
from arc_memory.rl.data_provider import GitHubDataProvider
from arc_memory.rl.run import initialize_pipeline, setup_logging

logger = logging.getLogger(__name__)

class BlastRadiusBenchmark:
    """
    Benchmark for blast radius prediction using the RL pipeline.
    
    This class provides methods to benchmark the RL pipeline for blast radius 
    prediction on different datasets and configurations.
    """
    
    def __init__(self, github_token: str, repo_owner: str = "tensorflow", 
                repo_name: str = "tensorflow", results_dir: str = "benchmark_results"):
        """
        Initialize the benchmark.
        
        Args:
            github_token: GitHub API token
            repo_owner: Repository owner
            repo_name: Repository name
            results_dir: Directory to save benchmark results
        """
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.results_dir = results_dir
        self.sdk = Arc()
        
        # Create results directory
        os.makedirs(results_dir, exist_ok=True)
        
        # Initialize GitHub data provider
        self.github_data_provider = GitHubDataProvider(github_token, repo_owner, repo_name)
        
    def _prepare_temporal_data(self, start_date: str, end_date: str) -> ArcEnvironment:
        """
        Prepare temporal data and environment.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            ArcEnvironment with temporal data loaded
        """
        logger.info(f"Preparing temporal data from {start_date} to {end_date}")
        
        # Create environment with GitHub data provider
        env = ArcEnvironment(self.sdk, self.github_data_provider)
        
        # Load temporal graph
        env.load_temporal_graph(start_date, end_date)
        
        return env
    
    def benchmark_different_timeframes(self, timeframes: List[Tuple[str, str]], 
                                       num_episodes: int = 100, 
                                       agent_type: str = "qtable",
                                       binary_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Benchmark the RL pipeline on different timeframes.
        
        Args:
            timeframes: List of (start_date, end_date) tuples
            num_episodes: Number of episodes to train for each timeframe
            agent_type: Type of agent to use
            binary_threshold: Threshold for binary reward function
            
        Returns:
            Benchmark results
        """
        results = {}
        
        for start_date, end_date in timeframes:
            timeframe_key = f"{start_date}_to_{end_date}"
            logger.info(f"Benchmarking timeframe {timeframe_key}")
            
            # Initialize pipeline with temporal data
            env, agent, reward_function = initialize_pipeline(
                sdk=self.sdk,
                agent_type=agent_type,
                reward_type="binary",
                github_token=self.github_token,
                repo_owner=self.repo_owner,
                repo_name=self.repo_name,
                use_temporal_data=True,
                start_date=start_date,
                end_date=end_date,
                binary_threshold=binary_threshold
            )
            
            # Create trainer
            save_dir = os.path.join(self.results_dir, f"models_{timeframe_key}")
            os.makedirs(save_dir, exist_ok=True)
            
            trainer = RLTrainer(env, agent, reward_function, save_dir)
            trainer.metrics["binary_rewards"] = []
            
            # Train the agent
            start_time = time.time()
            metrics = trainer.train(num_episodes=num_episodes)
            end_time = time.time()
            
            # Calculate training time
            training_time = end_time - start_time
            
            # Calculate metrics
            total_rewards = sum(metrics["episode_rewards"])
            avg_reward = total_rewards / num_episodes
            success_rate = metrics["binary_rewards"].count(1.0) / len(metrics["binary_rewards"]) if metrics["binary_rewards"] else 0
            
            # Store results
            results[timeframe_key] = {
                "start_date": start_date,
                "end_date": end_date,
                "num_episodes": num_episodes,
                "total_rewards": total_rewards,
                "avg_reward": avg_reward,
                "success_rate": success_rate,
                "training_time": training_time
            }
            
            # Plot metrics
            plot_dir = os.path.join(self.results_dir, f"plots_{timeframe_key}")
            os.makedirs(plot_dir, exist_ok=True)
            
            plt.figure(figsize=(10, 6))
            plt.plot(metrics["episode_rewards"])
            plt.title(f"Episode Rewards - {timeframe_key}")
            plt.xlabel("Episode")
            plt.ylabel("Reward")
            plt.savefig(os.path.join(plot_dir, "episode_rewards.png"))
            plt.close()
            
            # Plot binary reward distribution
            plt.figure(figsize=(10, 6))
            rewards = metrics["binary_rewards"]
            zero_count = rewards.count(0.0)
            one_count = rewards.count(1.0)
            plt.bar(["0.0", "1.0"], [zero_count, one_count])
            plt.title(f"Binary Reward Distribution - {timeframe_key}")
            plt.xlabel("Reward Value")
            plt.ylabel("Count")
            plt.savefig(os.path.join(plot_dir, "binary_rewards.png"))
            plt.close()
            
        return results
    
    def benchmark_threshold_sensitivity(self, thresholds: List[float], 
                                        start_date: str = "2020-01-01", 
                                        end_date: str = "2020-06-30",
                                        num_episodes: int = 50,
                                        agent_type: str = "qtable") -> Dict[str, Any]:
        """
        Benchmark the sensitivity to different binary reward thresholds.
        
        Args:
            thresholds: List of threshold values to test
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            num_episodes: Number of episodes to train for each threshold
            agent_type: Type of agent to use
            
        Returns:
            Benchmark results
        """
        results = {}
        
        for threshold in thresholds:
            threshold_key = f"threshold_{threshold}"
            logger.info(f"Benchmarking threshold {threshold}")
            
            # Initialize pipeline with temporal data
            env, agent, reward_function = initialize_pipeline(
                sdk=self.sdk,
                agent_type=agent_type,
                reward_type="binary",
                github_token=self.github_token,
                repo_owner=self.repo_owner,
                repo_name=self.repo_name,
                use_temporal_data=True,
                start_date=start_date,
                end_date=end_date,
                binary_threshold=threshold
            )
            
            # Create trainer
            save_dir = os.path.join(self.results_dir, f"models_{threshold_key}")
            os.makedirs(save_dir, exist_ok=True)
            
            trainer = RLTrainer(env, agent, reward_function, save_dir)
            trainer.metrics["binary_rewards"] = []
            
            # Train the agent
            start_time = time.time()
            metrics = trainer.train(num_episodes=num_episodes)
            end_time = time.time()
            
            # Calculate training time
            training_time = end_time - start_time
            
            # Calculate metrics
            total_rewards = sum(metrics["episode_rewards"])
            avg_reward = total_rewards / num_episodes
            success_rate = metrics["binary_rewards"].count(1.0) / len(metrics["binary_rewards"]) if metrics["binary_rewards"] else 0
            
            # Store results
            results[threshold_key] = {
                "threshold": threshold,
                "num_episodes": num_episodes,
                "total_rewards": total_rewards,
                "avg_reward": avg_reward,
                "success_rate": success_rate,
                "training_time": training_time
            }
            
        # Plot threshold sensitivity
        plt.figure(figsize=(10, 6))
        thresholds_vals = [results[f"threshold_{t}"]["threshold"] for t in thresholds]
        success_rates = [results[f"threshold_{t}"]["success_rate"] for t in thresholds]
        plt.plot(thresholds_vals, success_rates, marker='o')
        plt.title("Threshold Sensitivity")
        plt.xlabel("Threshold")
        plt.ylabel("Success Rate")
        plt.savefig(os.path.join(self.results_dir, "threshold_sensitivity.png"))
        plt.close()
        
        return results
    
    def compare_against_baselines(self, start_date: str = "2020-01-01", 
                                 end_date: str = "2020-06-30",
                                 num_episodes: int = 100) -> Dict[str, Any]:
        """
        Compare the RL agent against baselines.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            num_episodes: Number of episodes to train for
            
        Returns:
            Comparison results
        """
        results = {}
        
        # Models to compare
        models = [
            ("random", "Random Agent"),
            ("qtable", "Q-Table Agent")
        ]
        
        for model_key, model_name in models:
            logger.info(f"Benchmarking model {model_name}")
            
            # Initialize pipeline with temporal data
            env, agent, reward_function = initialize_pipeline(
                sdk=self.sdk,
                agent_type=model_key,
                reward_type="binary",
                github_token=self.github_token,
                repo_owner=self.repo_owner,
                repo_name=self.repo_name,
                use_temporal_data=True,
                start_date=start_date,
                end_date=end_date
            )
            
            # Create trainer
            save_dir = os.path.join(self.results_dir, f"models_{model_key}")
            os.makedirs(save_dir, exist_ok=True)
            
            trainer = RLTrainer(env, agent, reward_function, save_dir)
            trainer.metrics["binary_rewards"] = []
            
            # Train/evaluate the agent
            metrics = trainer.evaluate(num_episodes=num_episodes)
            
            # Calculate metrics
            success_rate = metrics["binary_rewards"].count(1.0) / len(metrics["binary_rewards"]) if metrics["binary_rewards"] else 0
            
            # Store results
            results[model_key] = {
                "model_name": model_name,
                "success_rate": success_rate,
                "avg_reward": metrics["avg_reward"]
            }
        
        # Plot comparison
        plt.figure(figsize=(10, 6))
        model_names = [results[m]["model_name"] for m, _ in models]
        success_rates = [results[m]["success_rate"] for m, _ in models]
        plt.bar(model_names, success_rates)
        plt.title("Model Comparison - Success Rate")
        plt.xlabel("Model")
        plt.ylabel("Success Rate")
        plt.savefig(os.path.join(self.results_dir, "model_comparison.png"))
        plt.close()
        
        return results
    
    def save_results(self, results: Dict[str, Any], name: str):
        """
        Save benchmark results to disk.
        
        Args:
            results: Benchmark results
            name: Name of the benchmark
        """
        # Save results as JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Saved benchmark results to {filepath}")


def main():
    """Main entry point."""
    # Set up logging
    setup_logging()
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark the RL pipeline")
    parser.add_argument("--github_token", type=str, required=True,
                      help="GitHub API token")
    parser.add_argument("--repo_owner", type=str, default="tensorflow",
                      help="GitHub repository owner")
    parser.add_argument("--repo_name", type=str, default="tensorflow",
                      help="GitHub repository name")
    parser.add_argument("--results_dir", type=str, default="benchmark_results",
                      help="Directory to save benchmark results")
    parser.add_argument("--benchmark", type=str, choices=["timeframes", "thresholds", "baselines", "all"],
                      default="all", help="Benchmark to run")
    
    args = parser.parse_args()
    
    # Create benchmark
    benchmark = BlastRadiusBenchmark(
        github_token=args.github_token,
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        results_dir=args.results_dir
    )
    
    # Run benchmarks
    if args.benchmark == "timeframes" or args.benchmark == "all":
        # Define timeframes to benchmark
        timeframes = [
            ("2020-01-01", "2020-03-31"),  # Q1 2020
            ("2020-04-01", "2020-06-30"),  # Q2 2020
            ("2020-01-01", "2020-06-30")   # Full period
        ]
        
        results = benchmark.benchmark_different_timeframes(timeframes)
        benchmark.save_results(results, "timeframes_benchmark")
    
    if args.benchmark == "thresholds" or args.benchmark == "all":
        # Define thresholds to benchmark
        thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
        
        results = benchmark.benchmark_threshold_sensitivity(thresholds)
        benchmark.save_results(results, "thresholds_benchmark")
    
    if args.benchmark == "baselines" or args.benchmark == "all":
        results = benchmark.compare_against_baselines()
        benchmark.save_results(results, "baselines_benchmark")


if __name__ == "__main__":
    main() 