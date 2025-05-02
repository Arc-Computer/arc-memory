# ADR 0003: Refactor Simulation Workflow from LangGraph to Smol Agents

## Status

Accepted

## Context

The current implementation of Arc Memory's simulation workflow uses LangGraph for orchestration. This implementation has grown to approximately 1500 lines of code in a single file (`arc_memory/simulate/langgraph_flow.py`), making it difficult to maintain and extend. Additionally, we've encountered several issues:

1. The monolithic structure makes it hard to debug and test individual components
2. Progress reporting is inconsistent and lacks visibility
3. The sandbox environment integration is not as seamless as desired
4. Error handling is complex due to the graph-based workflow
5. The agent has limited autonomy within the rigid graph structure

We need a more modular, maintainable, and agent-centric approach that gives more control to the AI agent while maintaining security through sandboxed environments.

## Decision

We will refactor the simulation workflow from LangGraph to Smol Agents for the following reasons:

1. **Code-centric approach**: Smol Agents' focus on code execution aligns better with our simulation needs, where we need to run code in sandboxed environments.

2. **Built-in security**: Smol Agents provides native integration with E2B, which we're already using for our sandbox environment.

3. **Simplicity**: The current LangGraph implementation is overly complex and difficult to maintain at 1500 lines in a single file.

4. **Better visibility**: Smol Agents would allow us to visually show the code being executed in the sandbox, improving transparency.

5. **More agent autonomy**: Giving the agent more control through code execution would likely lead to more efficient and flexible simulations.

The refactoring will involve breaking down the monolithic `langgraph_flow.py` into multiple focused modules:

- `diff.py` - Diff extraction and analysis
- `causal.py` - Causal graph building
- `sandbox.py` - Sandbox environment setup
- `analysis.py` - Metrics analysis and risk scoring
- `explanation.py` - LLM-based explanation generation
- `attestation.py` - Attestation generation
- `workflow.py` - Main workflow orchestration using Smol Agents

## Consequences

### Positive

1. **Improved maintainability**: Smaller, focused modules will be easier to maintain and test
2. **Better security**: Native integration with E2B will improve sandbox security
3. **Enhanced visibility**: Users will be able to see the code being executed in the sandbox
4. **More flexible workflow**: The agent will have more autonomy to handle complex scenarios
5. **Simplified error handling**: Python-native error handling will be more straightforward than graph-based error handling

### Negative

1. **Migration effort**: Significant refactoring effort required to move from LangGraph to Smol Agents
2. **Learning curve**: Team members will need to learn the Smol Agents framework
3. **Potential regressions**: Comprehensive testing will be needed to ensure no functionality is lost

### Neutral

1. **Framework dependency**: We're replacing one framework dependency (LangGraph) with another (Smol Agents)
2. **API changes**: The public API for simulation will need to be maintained for backward compatibility

## Implementation Plan

1. Create a new branch for the refactoring
2. Implement the new module structure
3. Migrate functionality from LangGraph to Smol Agents incrementally
4. Add comprehensive tests for each module
5. Update documentation to reflect the new architecture
6. Perform thorough testing before merging

## References

- [Smol Agents Documentation](https://huggingface.co/docs/smolagents/en/index)
- [Secure Code Execution in Smol Agents](https://huggingface.co/docs/smolagents/en/tutorials/secure_code_execution)
- [Arc Memory Simulation Improvements](../simulation_improvements.md)
