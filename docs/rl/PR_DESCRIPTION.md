# Add Reinforcement Learning (RL) Pipeline to Arc Memory

This PR adds a baseline reinforcement learning (RL) pipeline to Arc Memory, implementing the planned RL approach described in the roadmap documents.

## Overview

The RL pipeline implements a basic reinforcement learning system for predicting and evaluating code changes, blast radius, and vulnerability predictions. It follows the multi-component reward structure outlined in the roadmap:

```
R = Rcorr + Rcomp + Rreas + Rtool + Rkg + Rcausal
```

Where:
- Rcorr (Correctness): Rewards for code changes passing tests and static analysis
- Rcomp (Completion): Progress toward overall goal (e.g., % of services migrated)
- Rreas (Reasoning Quality): Quality of intermediate reasoning or planning steps
- Rtool (Tool Use): Efficiency in selecting and using appropriate tools
- Rkg (KG Enrichment): Adding valuable provenance to the knowledge graph
- Rcausal (Coordination): Successfully unblocking other agents' operations

## Key Components

1. **Environment** (`environment.py`): Represents the codebase state through the Arc knowledge graph
2. **Agent** (`agent.py`): Implements agents that interact with the environment:
   - `RandomAgent`: Baseline agent that takes random actions
   - `QTableAgent`: Q-learning agent with epsilon-greedy exploration
3. **Reward Function** (`reward.py`): Implements the multi-component reward function
4. **Training** (`training.py`): Handles training, evaluation, and experience collection
5. **Runner** (`run.py`): Provides high-level functions to run the pipeline
6. **CLI** (`cli/rl.py`): Command-line interface for the RL pipeline

## Usage

The RL pipeline can be used in four modes:

1. **Training**:
```bash
arc rl run --mode train --num-episodes 100 --agent-type qtable
```

2. **Evaluation**:
```bash
arc rl run --mode evaluate --agent-path models/agent_episode_100.json --num-episodes 10
```

3. **Experience Collection**:
```bash
arc rl run --mode collect --num-episodes 10 --num-training-epochs 20 --buffer-path experiences.pkl
```

4. **Demo**:
```bash
arc rl run --mode demo --agent-path models/agent_episode_100.json --num-steps 10
```

## Tests

The PR includes tests for all major components:
- `test_environment.py`: Tests the environment interactions
- `test_agent.py`: Tests agent behavior and learning
- `test_reward.py`: Tests reward calculation

You can also run a simple test via the CLI:
```bash
arc rl test
```

## Future Work

This PR implements a baseline RL system that can be extended in several ways:
1. **Deep Q-Network (DQN)**: Replace the Q-table with a neural network for handling larger state spaces
2. **More sophisticated state representation**: Improve the state representation using graph embeddings
3. **Advanced agents**: Implement PPO, DDPG, or other state-of-the-art RL algorithms
4. **Multi-agent RL**: Extend to multiple agents that can coordinate

## Dependencies

The RL pipeline adds two dependencies:
- `numpy`: For numerical computations
- `matplotlib`: For plotting training metrics

These are added as optional dependencies under the `rl` extra. 