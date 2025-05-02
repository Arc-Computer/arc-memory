# Arc Memory Simulation Improvements

This document outlines the plan for improving the simulation history display and overall user experience in the Arc Memory simulation feature.

## Current Issues

### 1. Simulation History Display Problems

The current simulation history display shows:
- Missing dates (showing "Unknown")
- Empty entries with no ID but with "Unknown" date
- Missing or incomplete service information
- Inconsistent formatting

Example of current output:
```
┃ ID         ┃ Date    ┃ Scenario        ┃ Risk Score ┃ Services    ┃
┡━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ sim_test_1 │ Unknown │ network_latency │ 25         │ api-service │
│ sim_test_2 │ Unknown │ network_latency │ 30         │ api-service │
│            │ Unknown │                 │ 0          │             │
```

### 2. Lack of Clear Explanation in Simulation Output

- Missing detailed reasoning and explanations ("show your work")
- Lack of transparency about data sources and assumptions
- Insufficient integration with the LLM in `arc_memory/simulate/langgraph_flow.py`

### 3. Evidence of Testing in Sandbox Environment

- Limited visibility into the actual testing that occurred
- No access to unit, integration, and end-to-end test results
- Code execution from `arc_memory/simulate/code_interpreter.py` not visible to users

### 4. Output Format Issues

- JSON output not converted to human-readable format in the CLI
- No progress indicators for long-running operations
- Limited error handling and user feedback

## Improvement Plan

### 1. Fix Data Storage and Retrieval

#### Tasks:
- [ ] Review database schema to ensure all necessary fields are defined
- [ ] Fix simulation node creation in `memory/storage.py` to include all metadata
- [ ] Update query functions in `memory/query.py` to retrieve complete simulation data
- [ ] Add validation to ensure no empty entries are displayed in history
- [ ] Format dates consistently in human-readable format

#### Files to modify:
- `arc_memory/memory/storage.py`
- `arc_memory/memory/query.py`
- `arc_memory/cli/sim.py` (history command)

### 2. Enhance Explanation Generation

#### Tasks:
- [ ] Modify LLM system prompt in `langgraph_flow.py` to request more detailed explanations
- [ ] Structure the prompt to explicitly ask for reasoning, data sources, and assumptions
- [ ] Update the explanation generation function to store the full explanation
- [ ] Add a way to display the full explanation in the CLI output

#### Files to modify:
- `arc_memory/simulate/langgraph_flow.py`
- `arc_memory/simulate/llm.py` (if exists, or create it)

#### Example prompt enhancement:
```python
SYSTEM_PROMPT = """
You are an expert system analyst evaluating the impact of code changes.
Please provide:
1. A detailed analysis of the potential impact
2. Clear explanation of your reasoning process
3. List of all data sources you considered
4. Any assumptions you made during analysis
5. Confidence level in your assessment

Show your work step by step so the user can understand your thought process.
"""
```

### 3. Improve Sandbox Testing Visibility

#### Tasks:
- [ ] Enhance logging in `code_interpreter.py` to capture more detailed information
- [ ] Store test execution details (commands run, outputs, errors) in the simulation node
- [ ] Create a way to display this information on demand (with `--verbose` flag)
- [ ] Add a summary of tests performed in the standard output

#### Files to modify:
- `arc_memory/simulate/code_interpreter.py`
- `arc_memory/cli/sim.py`

### 4. Enhance Output Formatting

#### Tasks:
- [ ] Create a formatter to convert JSON output to markdown for CLI display
- [ ] Add progress indicators for long-running operations
- [ ] Implement better error handling with user-friendly messages
- [ ] Add color coding for risk levels and important information

#### Files to modify:
- `arc_memory/cli/sim.py`
- `arc_memory/cli/utils.py` (create if doesn't exist)

#### Example formatter function:
```python
def format_simulation_results(results_json):
    """Convert simulation results JSON to human-readable markdown."""
    markdown = f"""
# Simulation Results: {results_json['sim_id']}

## Summary
- **Date**: {format_date(results_json['timestamp'])}
- **Scenario**: {results_json['scenario']}
- **Risk Score**: {results_json['risk_score']}/100
- **Affected Services**: {', '.join(results_json['services'])}

## Detailed Analysis
{results_json['explanation']}

## Metrics
{format_metrics(results_json['metrics'])}
"""
    return markdown
```

### 5. Improve CLI Experience

#### Tasks:
- [ ] Add a progress bar for long-running simulations
- [ ] Provide clearer error messages with suggestions for resolution
- [ ] Add more detailed help text and examples
- [ ] Implement a `--format` option to allow output in different formats (text, markdown, json)

#### Files to modify:
- `arc_memory/cli/sim.py`
- `arc_memory/cli/utils.py`

## Implementation Strategy

### Phase 1: Data Storage and Retrieval
Focus on ensuring all simulation data is properly stored and retrieved, fixing the basic display issues in the history command.

### Phase 2: Output Formatting
Implement the formatter to convert JSON to human-readable output and add progress indicators.

### Phase 3: Explanation Enhancement
Improve the LLM prompts and explanation generation to provide more detailed reasoning.

### Phase 4: Sandbox Testing Visibility
Enhance the code interpreter to capture and display more detailed testing information.

### Phase 5: CLI Experience
Finalize the CLI experience with better error handling, help text, and additional options.

## Testing Strategy

For each phase:
1. Write unit tests to verify the functionality
2. Perform manual testing with different scenarios
3. Verify backward compatibility with existing simulations
4. Check edge cases (empty results, errors, etc.)

## Documentation Updates

After implementation:
1. Update CLI documentation in `docs/cli/sim.md`
2. Add examples in `docs/examples/simulation.md`
3. Update README with new features
4. Add troubleshooting tips for common issues

## Refactoring Plan: LangGraph to Smol Agents

Based on the issues identified and the need for a more modular, maintainable approach, we've decided to refactor the simulation workflow from LangGraph to Smol Agents. This section outlines the detailed refactoring plan.

### Why Smol Agents?

| Feature | LangGraph | Smol Agents |
|---------|-----------|-------------|
| **Architecture** | Graph-based workflow with nodes and edges | Code-centric agent approach with Python execution |
| **Complexity** | Higher complexity with state management and graph definitions | Lower complexity with more direct code execution |
| **Security** | No built-in sandboxing | Built-in sandboxing options (local, E2B, Docker) |
| **Control Flow** | Explicit graph definition with conditional edges | More natural Python control flow |
| **Debugging** | Requires understanding graph state transitions | More straightforward Python debugging |
| **Integration with E2B** | Requires custom integration | Native integration with E2B |
| **Code Size** | Our implementation is ~1500 lines in one file | Would likely be more modular and smaller |
| **Agent Autonomy** | Limited by graph structure | Higher autonomy with code execution |

### Module Structure

```bash
arc_memory/simulate/
├── __init__.py
├── diff.py                # Diff extraction and analysis
├── causal.py              # Causal graph building
├── sandbox.py             # Sandbox environment setup
├── analysis.py            # Metrics analysis and risk scoring
├── explanation.py         # LLM-based explanation generation
├── attestation.py         # Attestation generation
├── workflow.py            # Main workflow orchestration (using Smol Agents)
├── agents/                # Agent definitions
│   ├── __init__.py
│   ├── diff_agent.py      # Agent for diff analysis
│   ├── sandbox_agent.py   # Agent for sandbox testing
│   ├── analysis_agent.py  # Agent for metrics analysis
│   └── explain_agent.py   # Agent for explanation generation
└── utils/                 # Utility functions
    ├── __init__.py
    ├── git.py             # Git utilities
    ├── progress.py        # Progress reporting
    └── formatting.py      # Output formatting
```

### Implementation Phases

#### Phase 1: Core Module Creation
1. Create the basic module structure
2. Implement utility functions and shared code
3. Extract core functionality from `langgraph_flow.py` into appropriate modules

#### Phase 2: Agent Implementation
1. Create agent definitions using Smol Agents
2. Implement the sandbox integration with E2B
3. Develop the workflow orchestration

#### Phase 3: CLI Integration
1. Update the CLI to use the new workflow
2. Implement progress reporting and output formatting
3. Add support for the `--memory` flag and history subcommand

#### Phase 4: Testing and Documentation
1. Write comprehensive tests for each module
2. Update documentation to reflect the new architecture
3. Create examples demonstrating the new workflow

### Benefits of This Approach

1. **Improved maintainability**: Smaller, focused modules will be easier to maintain and test
2. **Better security**: Native integration with E2B will improve sandbox security
3. **Enhanced visibility**: Users will be able to see the code being executed in the sandbox
4. **More flexible workflow**: The agent will have more autonomy to handle complex scenarios
5. **Simplified error handling**: Python-native error handling will be more straightforward

For more details on this decision, see [ADR-0003: Refactor Simulation Workflow to Smol Agents](adr/0003-refactor-simulation-workflow-to-smol-agents.md).
