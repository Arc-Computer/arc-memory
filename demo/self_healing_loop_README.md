# Self-Healing Code Generation Loop

This example demonstrates a simplified approach to self-healing code generation using OpenAI's capabilities. The system coordinates three specialized agents to improve code quality:

1. **Code Review Agent**: Analyzes code quality, patterns, and potential issues
2. **Impact Analysis Agent**: Determines potential impacts of changes
3. **Code Generation Agent**: Creates improved code based on insights

## How It Works

The self-healing loop follows these steps:

1. The Code Review Agent analyzes the target file and identifies issues, patterns, and potential improvements.
2. The Impact Analysis Agent determines which components might be affected by changes to the file.
3. The Code Generation Agent uses insights from both agents to generate improved code that addresses issues while minimizing negative impacts.
4. The improved code is saved to the specified output file.

## Prerequisites

- Python 3.8+
- OpenAI API key (set as `OPENAI_API_KEY` environment variable)
- OpenAI Python package (`pip install openai`)

## Usage

### Running the Self-Healing Loop

```bash
python demo/self_healing_loop.py --file /path/to/file.py [--output improved_file.py]
```

Arguments:
- `--file`: Path to the file to improve
- `--output`: Optional path to save the improved code

### Example

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key

# Run the self-healing loop on a file
python demo/self_healing_loop.py --file demo/test_files/sample_code.py --output improved_code.py
```

### Using the Demo Script

For convenience, you can use the provided demo script:

```bash
bash demo/scripts/run_self_healing_demo.sh
```

This script will:
1. Check if your OpenAI API key is set
2. Run the self-healing loop on the sample code file
3. Save the improved code to `demo/test_files/improved_code.py`
4. Show a diff of the changes

## Architecture

The self-healing loop uses a simple, direct approach to multi-agent orchestration:

1. Each agent is specialized for a specific task
2. The orchestrator coordinates the workflow between agents in a linear fashion
3. Each agent's output is passed directly to the next agent in the pipeline

### Agent Design

Each agent in the self-healing loop is designed to:

1. **Focus on a single responsibility**: Code review, impact analysis, or code generation
2. **Provide detailed, actionable output**: Specific issues, potential impacts, or code improvements
3. **Work independently**: Each agent can be run separately for targeted analysis

## Results

The self-healing loop can produce impressive improvements to code quality:

- **Structural improvements**: Better organization, modularization, and encapsulation
- **Bug fixes**: Identification and correction of potential bugs and edge cases
- **Performance optimizations**: More efficient algorithms and data structures
- **Readability enhancements**: Clearer naming, better documentation, and consistent style

In our sample code example, the self-healing loop:
- Reduced code size by over 60% (from 217 lines to 77 lines)
- Improved error handling with specific exception types
- Replaced global variables with a proper configuration class
- Implemented proper logging instead of print statements
- Refactored functions to follow the Single Responsibility Principle

## Customization

You can customize the self-healing loop by modifying the Python script:

1. **Adjust the prompts**: Change the instructions given to each agent
2. **Modify the OpenAI model**: Use different models for different tasks
3. **Add additional agents**: Extend the pipeline with specialized agents for specific tasks

## Limitations

- Code generation is limited by the context window of the LLM. Very large files may not be fully processed.
- The system may not handle complex refactorings that span multiple files.
- Generated code should always be reviewed by a human before being committed.

## Future Improvements

- Support for multi-file refactorings
- Integration with testing frameworks to validate generated code
- More sophisticated impact analysis
- Learning from accepted and rejected improvements to improve future suggestions
