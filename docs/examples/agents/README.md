# Arc Memory Agent Examples

This directory contains example agents that demonstrate how to use Arc Memory's SDK to build intelligent agents that can answer questions about your codebase. These examples are designed to be educational and serve as starting points for building your own agents.

## Available Agents

### Code Review Assistant (`code_review_assistant.py`)

A simplified agent that helps with code reviews by providing context and impact analysis. This agent is designed to be a starting point for building your own code review assistant.

### Incident Response Navigator (`incident_response_navigator.py`)

An agent that helps with incident response by analyzing incidents and providing insights about component relationships, temporal changes, similar incidents, root cause predictions, and resolution recommendations.

### LLM-Powered Blast Radius (`llm_powered_blast_radius.py`)

An agent that analyzes the potential impact of changes to a file by visualizing the "blast radius" of those changes. This agent uses LLMs to provide intelligent analysis of the impact and recommendations for mitigating risks.

### OpenAI Integration (`openai_integration.py`)

A simple example showing how to integrate Arc Memory with OpenAI's API. This example demonstrates how to create an OpenAI agent with Arc Memory tools.

## Demo Agents vs. Example Agents

The agents in this directory are simplified examples designed for educational purposes. For more comprehensive implementations that are ready for use in demos, see the `/demo/agents/` directory, which includes:

- **Enhanced Blast Radius (`enhanced_blast_radius.py`)**: A more comprehensive implementation of blast radius analysis with visualization capabilities.
- **LLM-Powered Code Review (`llm_powered_code_review.py`)**: A more comprehensive implementation of code review with detailed analysis and recommendations.
- **Code Generation Agent (`code_generation_agent.py`)**: An agent that generates improved code based on insights from code review and blast radius analysis.
- **Self-Healing Loop (`self_healing_loop.py`)**: An orchestration system that coordinates multiple agents to create a self-healing code generation loop.

## Usage

To run any of these example agents:

```bash
# Navigate to the examples directory
cd docs/examples

# Run an agent
python agents/code_review_assistant.py --repo /path/to/repo --files file1.py file2.py
```

## Creating Your Own Agents

These examples are designed to be starting points for building your own agents. Feel free to modify them to suit your needs or use them as inspiration for building entirely new agents.

For more information on building agents with Arc Memory, see the [SDK Documentation](../../sdk/README.md).
