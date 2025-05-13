# Arc Memory Examples

This directory contains ready-to-use examples that demonstrate how to integrate Arc Memory into your workflow. Each example is designed to be simple to run and modify for your own needs.

## Quick Start

To run any example:

1. Make sure you have Arc Memory installed with all required dependencies:
   ```bash
   # Install Arc Memory with all dependencies
   pip install arc-memory[all]

   # Or install with specific dependencies
   pip install arc-memory[openai,langchain]
   ```

2. Set up your OpenAI API key:
   ```bash
   export OPENAI_API_KEY=your-api-key
   ```

3. Authenticate with data sources (if needed):
   ```bash
   # Authenticate with GitHub
   arc auth github

   # Authenticate with Linear
   arc auth linear
   ```

4. Build a comprehensive knowledge graph for your repository:
   ```bash
   cd /path/to/your/repo

   # Build with all data sources and LLM enhancement
   arc build --github --linear --llm-enhancement

   # Or build with just Git data for a simpler graph
   arc build
   ```

5. Run the example:
   ```bash
   python agents/code_review_agent.py
   ```

## Testing Requirements

To test these examples, you'll need:

1. **A built knowledge graph**: The examples assume you have already built a knowledge graph for your repository using `arc build`. See the [Getting Started Guide](../getting_started.md) for detailed instructions.

2. **Required dependencies**:
   - For OpenAI examples: `pip install openai`
   - For LangChain examples: `pip install langchain langchain-openai`

3. **API keys**:
   - OpenAI API key set as an environment variable: `export OPENAI_API_KEY=your-api-key`

4. **Registered adapters**: The framework adapters need to be registered. This happens automatically when you install Arc Memory with the appropriate dependencies.

## Troubleshooting

If you encounter issues running the examples:

1. **Adapter not found**: Make sure you've installed Arc Memory with the appropriate dependencies:
   ```bash
   pip install arc-memory[openai,langchain]
   ```

2. **Knowledge graph not found**: Make sure you've built a knowledge graph for your repository:
   ```bash
   arc build
   ```

3. **API key issues**: Make sure your OpenAI API key is set correctly:
   ```bash
   export OPENAI_API_KEY=your-api-key
   ```

4. **Authentication issues**: Make sure you're authenticated with the necessary data sources:
   ```bash
   # Check authentication status
   arc doctor

   # Re-authenticate if needed
   arc auth github
   arc auth linear
   ```

5. **LLM enhancement issues**: If you're using LLM enhancement and encounter issues:
   ```bash
   # Check if Ollama is installed
   which ollama

   # Install Ollama if needed (visit https://ollama.com/download)

   # Check if Ollama is running
   curl http://localhost:11434/api/version

   # Start Ollama if needed
   ollama serve
   ```

6. **Import errors**: Make sure you're running the examples from the correct directory:
   ```bash
   cd /path/to/arc-memory/docs/examples
   python agents/code_review_agent.py
   ```

## Available Examples

### Agent Examples

These examples show how to create agents that use Arc Memory to answer questions about your codebase:

- [Code Review Agent](./agents/code_review_agent.py) - An agent that helps with code reviews by providing context and impact analysis
- [Onboarding Agent](./agents/onboarding_agent.py) - An agent that helps new team members understand the codebase
- [Decision Tracker](./agents/decision_tracker.py) - An agent that explains why code exists and tracks decision trails
- [Impact Analyzer](./agents/impact_analyzer.py) - An agent that analyzes the potential impact of code changes

### Framework Integration Examples

These examples show how to integrate Arc Memory with different agent frameworks:

- [LangChain Integration](./agents/langchain_integration.py) - How to use Arc Memory with LangChain
- [OpenAI Integration](./agents/openai_integration.py) - How to use Arc Memory with OpenAI's API

## Example Structure

Each example follows a similar structure:

1. **Setup** - Initialize Arc Memory and configure the agent
2. **Agent Creation** - Create an agent with Arc Memory tools
3. **Usage** - Show how to use the agent to answer questions
4. **Customization** - Suggestions for customizing the agent for your needs

## Creating Your Own Agents

To create your own agent:

1. Choose which Arc Memory functions you want to expose:
   ```python
   from arc_memory import Arc

   arc = Arc(repo_path="./")

   # Choose which functions to expose
   arc_functions = [
       arc.query,                    # Natural language queries
       arc.get_decision_trail,       # Trace code history
       arc.get_related_entities,     # Find connections
       arc.analyze_component_impact  # Analyze impact
   ]
   ```

2. Choose your preferred framework and create an agent:
   ```python
   # For OpenAI
   from arc_memory.sdk.adapters import get_adapter

   openai_adapter = get_adapter("openai")
   tools = openai_adapter.adapt_functions(arc_functions)
   agent = openai_adapter.create_agent(tools=tools, model="gpt-4o")

   # For LangChain
   from langchain_openai import ChatOpenAI

   langchain_adapter = get_adapter("langchain")
   tools = langchain_adapter.adapt_functions(arc_functions)
   agent = langchain_adapter.create_agent(
       tools=tools,
       llm=ChatOpenAI(model="gpt-4o")
   )
   ```

3. Use your agent:
   ```python
   # For OpenAI
   response = agent("Why was the authentication system refactored?")

   # For LangChain
   response = agent.invoke({"input": "Why was the authentication system refactored?"})
   ```

## Next Steps

- [SDK Documentation](../sdk/README.md) - Learn more about the Arc Memory SDK
- [Getting Started Guide](../getting_started.md) - Complete guide to using Arc Memory
- [API Reference](../sdk/api_reference.md) - Detailed API documentation
