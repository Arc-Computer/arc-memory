# Self-Healing Code Generation Loop

This example demonstrates how to create a self-healing code generation loop using Arc Memory's knowledge graph and OpenAI's agent orchestration capabilities. The system coordinates three specialized agents to iteratively improve code quality:

1. **Code Review Agent**: Analyzes code quality, patterns, and potential issues
2. **Blast Radius Analysis Agent**: Analyzes potential impacts of changes
3. **Code Generation Agent**: Generates improved code based on insights

## How It Works

The self-healing loop follows these steps:

1. The Code Review Agent analyzes the target file and identifies issues, patterns, and potential improvements.
2. The Blast Radius Analysis Agent determines which components might be affected by changes to the file.
3. The Code Generation Agent uses insights from both agents to generate improved code that addresses issues while minimizing negative impacts.
4. The system evaluates the quality of the improvement and decides whether to accept it or try again.
5. This process repeats for a specified number of iterations or until a satisfactory improvement is achieved.

## Prerequisites

- Python 3.8+
- Arc Memory installed (`pip install arc-memory`)
- OpenAI API key (set as `OPENAI_API_KEY` environment variable)
- Knowledge graph built with `arc build --github`

## Usage

### Running the Self-Healing Loop

```bash
python self_healing_loop.py --repo /path/to/repo --file /path/to/file.py [--iterations 3] [--threshold 0.7] [--output improved_file.py]
```

Arguments:
- `--repo`: Path to the local repository
- `--file`: Path to the file to improve
- `--iterations`: Maximum number of improvement iterations (default: 3)
- `--threshold`: Minimum improvement score to accept (0.0-1.0, default: 0.7)
- `--output`: Optional path to save the improved code
- `--api-key`: OpenAI API key (uses `OPENAI_API_KEY` env var if not provided)

### Example

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key

# Run the self-healing loop on a file
python self_healing_loop.py --repo ./ --file src/core/auth.py --iterations 2 --output improved_auth.py
```

## Individual Agents

You can also run each agent individually:

### Code Review Agent

```bash
python llm_powered_code_review.py --repo /path/to/repo --files file1.py file2.py [--output review.json]
```

### Blast Radius Analysis Agent

```bash
python enhanced_blast_radius.py /path/to/file.py --repo /path/to/repo
```

### Code Generation Agent

```bash
python code_generation_agent.py --repo /path/to/repo --file /path/to/file.py --review review.json --impact impact.json [--output improved_file.py]
```

## Architecture

The self-healing loop uses a multi-agent orchestration pattern where:

1. Each agent is specialized for a specific task
2. Agents share the same knowledge graph for consistent context
3. The orchestrator coordinates the workflow between agents
4. Feedback mechanisms evaluate and improve the results

### Agent Communication

The agents communicate through JSON files containing their analysis results. This allows for:

- Clear separation of concerns between agents
- Easy inspection and debugging of intermediate results
- Flexibility to run agents in different environments or processes

### Knowledge Graph Integration

All agents leverage Arc Memory's knowledge graph to:

- Understand the codebase context and patterns
- Identify relationships between components
- Track the history and rationale of code changes
- Predict potential impacts of changes

## Customization

You can customize the self-healing loop in several ways:

### Adjusting Thresholds

Modify the improvement threshold to control how strict the system is about accepting changes:

```bash
# More permissive (accept more changes)
python self_healing_loop.py --repo ./ --file src/core/auth.py --threshold 0.5

# More strict (only accept high-quality changes)
python self_healing_loop.py --repo ./ --file src/core/auth.py --threshold 0.8
```

### Increasing Iterations

Increase the number of iterations to allow more attempts at improvement:

```bash
python self_healing_loop.py --repo ./ --file src/core/auth.py --iterations 5
```

### Modifying Agent Behavior

You can modify each agent's behavior by editing their respective Python files:

- `llm_powered_code_review.py`: Adjust the code review criteria and analysis depth
- `enhanced_blast_radius.py`: Change how potential impacts are analyzed and visualized
- `code_generation_agent.py`: Modify the code generation strategy and constraints

## Integration with OpenAI Assistants

You can also integrate this self-healing loop with OpenAI Assistants for a more interactive experience. Here's an example of how to create an assistant that uses the self-healing loop:

```python
from arc_memory.sdk import Arc
from arc_memory.sdk.adapters import get_adapter

# Initialize Arc with the repository path
arc = Arc(repo_path="./")

# Get the OpenAI adapter
openai_adapter = get_adapter("openai")

# Create an OpenAI Assistant with Arc Memory tools
assistant = openai_adapter.create_assistant(
    name="Self-Healing Code Assistant",
    instructions="""
    You are a Self-Healing Code Assistant that helps improve code quality.
    You can analyze code, identify issues, predict impacts, and generate improved code.
    Use the Arc Memory knowledge graph to understand the codebase context and patterns.
    """,
    model="gpt-4.1",
    tools=openai_adapter.adapt_functions([
        arc.query,
        arc.get_decision_trail,
        arc.get_related_entities,
        arc.analyze_component_impact
    ])
)
```

## Limitations

- The system relies on the quality of the knowledge graph. Ensure your graph is up-to-date with `arc build`.
- Code generation is limited by the context window of the LLM. Very large files may not be fully processed.
- The system may not handle complex refactorings that span multiple files.
- Generated code should always be reviewed by a human before being committed.

## Future Improvements

- Support for multi-file refactorings
- Integration with testing frameworks to validate generated code
- More sophisticated impact analysis using dynamic analysis
- Learning from accepted and rejected improvements to improve future suggestions
