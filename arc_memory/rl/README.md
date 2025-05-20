# Reinforcement Learning Pipeline for Blast Radius Prediction

This module implements a reinforcement learning (RL) pipeline for predicting the blast radius of code changes. The pipeline uses temporal data from GitHub repositories to train an agent to accurately predict which components will be affected by changes to a specific component.

## Key Components

- **Binary Reward Function**: Implements a binary (0/1) reward system to train the agent based on prediction accuracy 
- **GitHub Data Integration**: Extracts temporal code change patterns from repositories to build a knowledge graph
- **TensorFlow Repository Training**: Uses TensorFlow repository data from January 2020 to June 2020 for initial training
- **Dynamic Repository Support**: Architecture supports training on any repository with GitHub data access

## Getting Started

### Prerequisites

- Python 3.8+
- GitHub API token with repository access
- Arc Memory SDK

### Installation

The RL pipeline is built into the Arc Memory package. No additional installation is required.

### Running the Pipeline

#### Basic Training

```bash
python -m arc_memory.rl.run --mode train \
  --num_episodes 100 \
  --agent_type qtable \
  --reward_type binary \
  --github_token YOUR_GITHUB_TOKEN \
  --repo_owner tensorflow \
  --repo_name tensorflow \
  --use_temporal_data \
  --start_date 2020-01-01 \
  --end_date 2020-06-30 \
  --binary_threshold 0.7
```

#### Evaluation

```bash
python -m arc_memory.rl.run --mode evaluate \
  --agent_path models/agent_episode_100.json \
  --agent_type qtable \
  --reward_type binary \
  --github_token YOUR_GITHUB_TOKEN \
  --use_temporal_data
```

#### Demo

```bash
python -m arc_memory.rl.run --mode demo \
  --agent_path models/agent_episode_100.json \
  --agent_type qtable \
  --reward_type binary \
  --github_token YOUR_GITHUB_TOKEN \
  --use_temporal_data \
  --num_steps 10
```

### Benchmarking

The pipeline includes a benchmarking tool to evaluate performance across different configurations:

```bash
python -m arc_memory.rl.benchmark \
  --github_token YOUR_GITHUB_TOKEN \
  --repo_owner tensorflow \
  --repo_name tensorflow \
  --benchmark all
```

## Architecture

### Reward System

The pipeline uses a binary reward system that gives a score of 1.0 when blast radius predictions meet a specified threshold of accuracy (default: 0.7) and 0.0 otherwise. This clear signal helps the agent learn more efficiently.

### Temporal Graph

The system builds a temporal graph of code changes by:
1. Fetching commits in a specified date range
2. Analyzing file changes in each commit
3. Identifying components and their relationships
4. Building a knowledge graph of component dependencies

### Training Pipeline

1. **Data Collection**: GitHub API fetches commits and change history
2. **Graph Construction**: Builds a temporal graph of code changes
3. **Agent Training**: Q-learning agent predicts blast radius
4. **Benchmark Evaluation**: Measures success rates and performance

## Benchmark Metrics

Benchmark metrics focus on:
- Success rate (% of predictions with reward of 1.0)
- Average reward
- Training time
- Performance across different thresholds
- Comparison against baseline methods

## Future Improvements

- Support for deep Q-networks (DQN) with neural network state representation
- Integration with other repository sources beyond GitHub
- Improved component grouping heuristics
- Enhanced impact prediction visualization 