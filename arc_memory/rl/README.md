# Arc Memory Reinforcement Learning Pipeline

This module implements a baseline reinforcement learning (RL) system for predicting and evaluating code changes, blast radius, and other properties based on the Arc Memory knowledge graph.

## Components

The RL pipeline consists of several components:

1. **Environment** (`environment.py`): Represents the codebase state through the Arc knowledge graph, providing methods to observe the state, take actions, and receive rewards.

2. **Agent** (`agent.py`): Interacts with the environment, learns from experiences, and makes predictions. Two agent types are implemented:
   - `RandomAgent`: A simple agent that takes random actions
   - `QTableAgent`: A Q-table based agent that uses an epsilon-greedy policy

3. **Reward Function** (`reward.py`): Calculates rewards for actions. Implements a multi-component reward function:
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

4. **Training** (`training.py`): Handles the training loop, evaluation, and saving/loading of agents, including offline training using an experience buffer.

5. **Run** (`run.py`): Provides utilities to run the RL pipeline for both training and inference, including visualization of training metrics.

## Usage

You can use the RL pipeline in different modes:

### Training

Train an RL agent from scratch:

```bash
python -m arc_memory.rl.run --mode train --num_episodes 100 --agent_type qtable --save_dir models --plot_dir plots
```

### Collecting Experiences and Offline Training

Collect experiences and train offline:

```bash
python -m arc_memory.rl.run --mode collect --num_episodes 10 --num_training_epochs 20 --agent_type qtable --save_dir models --buffer_path experiences.pkl
```

### Evaluation

Evaluate a trained agent:

```bash
python -m arc_memory.rl.run --mode evaluate --agent_path models/agent_episode_100.json --agent_type qtable --num_episodes 10
```

### Demo

Run a demonstration of a trained agent:

```bash
python -m arc_memory.rl.run --mode demo --agent_path models/agent_episode_100.json --agent_type qtable --num_steps 10
```

## Multi-Component Reward Function

The multi-component reward function is a key element of the RL system. It evaluates actions based on multiple criteria:

1. **Correctness (Rcorr)**: Rewards code changes that pass tests and static analysis.
2. **Completion (Rcomp)**: Rewards progress toward overall goals.
3. **Reasoning (Rreas)**: Rewards high-quality reasoning steps.
4. **Tool Use (Rtool)**: Rewards efficient selection and use of appropriate tools.
5. **Knowledge Graph Enrichment (Rkg)**: Rewards adding valuable provenance to the knowledge graph.
6. **Coordination (Rcausal)**: Rewards successfully unblocking other agents' operations.

You can adjust the weights of these components by modifying the `weights` parameter of the `MultiComponentReward` class:

```python
reward_function = MultiComponentReward(weights={
    "correctness": 1.5,  # Increase weight of correctness
    "completion": 1.0,
    "reasoning": 1.0,
    "tool_use": 0.8,
    "kg_enrichment": 1.2,
    "coordination": 0.9,
})
```

## Adding Custom Agent Types

You can extend the system with custom agent types by implementing the `BaseAgent` class:

```python
from arc_memory.rl.agent import BaseAgent

class MyCustomAgent(BaseAgent):
    def __init__(self, node_ids, action_types):
        super().__init__()
        self.node_ids = node_ids
        self.action_types = action_types
        # Initialize your agent's state

    def act(self, state):
        # Implement action selection logic
        pass

    def learn(self, state, action, reward, next_state, done):
        # Implement learning logic
        pass

    def save(self, path):
        # Implement saving logic
        pass

    def load(self, path):
        # Implement loading logic
        pass
```

Then, update the `initialize_pipeline` function in `run.py` to include your custom agent:

```python
def initialize_pipeline(sdk, agent_type="qtable"):
    # ...
    if agent_type == "random":
        agent = RandomAgent(node_ids, action_types)
    elif agent_type == "qtable":
        agent = QTableAgent(node_ids, action_types)
    elif agent_type == "custom":
        agent = MyCustomAgent(node_ids, action_types)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
    # ...
```

## Extending the System

This baseline implementation provides a foundation for more advanced RL approaches. Some potential extensions include:

1. **Deep Q-Network (DQN)**: Replace the Q-table with a neural network for handling larger state spaces.
2. **Proximal Policy Optimization (PPO)**: Implement a policy gradient method for improved sample efficiency.
3. **Multi-Agent Reinforcement Learning (MARL)**: Extend to multiple agents that can collaborate.
4. **Hierarchical Reinforcement Learning**: Implement hierarchical approaches for complex tasks.
5. **Intrinsic Motivation**: Add curiosity-driven exploration for better exploitation of the knowledge graph.

## Testing

To test the pipeline, you can run a simple training session with a random agent:

```bash
python -m arc_memory.rl.run --mode train --num_episodes 5 --agent_type random
```

This will train a random agent for 5 episodes and save the results in the `models` and `plots` directories. 