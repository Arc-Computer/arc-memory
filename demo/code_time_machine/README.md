# Code Time Machine Demo

The Code Time Machine demo showcases Arc Memory's unique temporal understanding capabilities by creating a "time machine" experience that allows developers to explore how code evolved over time, understand the reasoning behind key decisions, and visualize the potential impact of changes.

## Overview

The Code Time Machine leverages Arc Memory's knowledge graph to provide insights that would be impossible to obtain from traditional code analysis tools. By combining Git history, GitHub issues/PRs, and code structure analysis, it creates a comprehensive view of your codebase's evolution and relationships.

The demo follows this narrative flow:

1. **Introduction**: Explains the concept of the Code Time Machine
2. **Graph Building**: Builds or loads the knowledge graph
3. **File Selection**: Selects a significant file to explore
4. **Timeline Exploration**: Shows how the file evolved over time using real historical data
5. **Decision Archaeology**: Explores key decisions that shaped the file with context from PRs and issues
6. **Impact Prediction**: Demonstrates how changes would affect the system using relationship analysis
7. **Improvement Suggestions**: Generates potential improvements based on historical patterns and code context

## Prerequisites

Before running the demo, make sure you have:

1. **Arc Memory installed**: `pip install arc-memory[all]`
2. **OpenAI API key set**: `export OPENAI_API_KEY=your-api-key` (required for reasoning engine)
3. **GitHub authentication**: `arc auth github`
4. **Required Python packages**: `pip install colorama rich openai`
5. **Knowledge graph built**: `arc build --llm-enhancement standard --llm-provider openai --llm-model gpt-4.1 --github`

Note: The reasoning engine requires the OpenAI package and a valid API key. If you don't have an API key, the demo will still work but without the advanced reasoning capabilities.

## Usage

The easiest way to run the demo is using the provided script:

```bash
# Run the demo on a specific file
./demo/code_time_machine/run_demo.sh path/to/file.py

# Run with reasoning enabled (requires OpenAI API key)
./demo/code_time_machine/run_demo.sh path/to/file.py --reasoning
```

You can also run the module directly:

```bash
# Basic usage (will prompt for file selection)
python -m demo.code_time_machine.main --repo /path/to/repo --interactive

# Specify a file to explore
python -m demo.code_time_machine.main --repo /path/to/repo --file path/to/file.py

# Enable reasoning engine with OpenAI's o4-mini model
python -m demo.code_time_machine.main --repo /path/to/repo --file path/to/file.py --reasoning

# Disable reasoning engine
python -m demo.code_time_machine.main --repo /path/to/repo --file path/to/file.py --no-reasoning
```

### Reasoning Engine

The Code Time Machine demo includes an optional reasoning engine that leverages OpenAI's Responses API with reasoning models (o4-mini by default) to provide advanced analysis of code evolution, decision trails, and impact prediction. This provides:

1. **Better Reasoning Capabilities**: Step-by-step reasoning about code evolution and decisions
2. **Transparency with Reasoning Summaries**: Shows how the model arrived at conclusions
3. **More Intelligent Analysis**: Deeper insights into code patterns and potential improvements

To use the reasoning engine, you need to set your OpenAI API key:

```bash
export OPENAI_API_KEY=your-api-key
```

## Demo Components

The Code Time Machine demo consists of the following components:

- **Main Demo Script**: `main.py` - Orchestrates the entire experience
- **Custom Impact Analysis**: `custom_impact.py` - Analyzes component relationships using real graph data
- **Reasoning Engine**: `reasoning_engine.py` - Provides advanced analysis with LLM reasoning
- **Timeline Visualizer**: `visualizers/timeline_visualizer.py` - Visualizes the timeline of a file's evolution
- **Decision Visualizer**: `visualizers/decision_visualizer.py` - Visualizes the decision trails for a file
- **Impact Visualizer**: `visualizers/impact_visualizer.py` - Visualizes the potential impact of changes to a file

## Visualization Approach

The demo uses CLI-based visualization with:

- Rich library for terminal formatting and tables
- ASCII/Unicode-based timeline visualization
- Color-coded decision points and impact predictions

## Key Features

### Timeline Visualization

The timeline visualization shows how a file has evolved over time, including:

- When the file was created
- Major modifications and their authors
- References to the file from other entities
- A visual timeline representation

### Decision Archaeology

The decision archaeology feature explores key decisions that shaped the file, including:

- Commit messages and authors
- Related PRs and issues
- Rationales extracted from PR descriptions and comments
- Code before and after the change

### Impact Prediction

The impact prediction feature shows a visualization of:

- Components that depend on the selected file
- How changes to specific functions would affect other parts
- Risk assessment for different types of changes

### Improvement Suggestions

The improvement suggestions feature generates suggestions for:

- Code quality improvements
- Performance optimizations
- Security enhancements
- Documentation improvements

## Example

```bash
# Run the demo on a significant file
./demo/code_time_machine/run_demo.sh arc_memory/sdk/core.py

# Or run the module directly
python -m demo.code_time_machine.main --repo ./ --file arc_memory/sdk/core.py
```

## Real Data Approach

The Code Time Machine demo uses only real data from the Arc Memory knowledge graph, with no mock data or sample visualizations. This ensures that the demo accurately represents the value of Arc Memory's temporal understanding capabilities:

1. **Timeline Exploration**: Uses real file history from Git commits and related entities
2. **Decision Archaeology**: Extracts actual decision trails from PRs, issues, and commit messages
3. **Impact Prediction**: Analyzes real component relationships in the knowledge graph
4. **Improvement Suggestions**: Generates suggestions based on actual code patterns and history

## Extending the Demo

You can extend the demo by:

1. Adding more visualizers in the `visualizers` directory
2. Enhancing the existing visualizers with more detailed information
3. Adding interactive elements to allow users to explore specific aspects in more detail
4. Integrating with other Arc Memory SDK capabilities

## Troubleshooting

If you encounter issues during the demo:

1. **Knowledge graph not found**: Run `arc build --github` to build the graph
2. **OpenAI API key not set**: Set the environment variable with `export OPENAI_API_KEY=your-api-key`
3. **Missing dependencies**: Install required packages with `pip install colorama rich`
4. **GitHub authentication**: Run `arc auth github` to authenticate with GitHub
