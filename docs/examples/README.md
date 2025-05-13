# Arc Memory Examples

This directory contains ready-to-use examples that demonstrate how to integrate Arc Memory into your workflow. Each example is designed to be simple to run and modify for your own needs.

## Quick Start

To run any example:

1. Make sure you have Arc Memory installed:
   ```bash
   pip install arc-memory
   ```

2. Build a knowledge graph for your repository:
   ```bash
   cd /path/to/your/repo
   arc build
   ```

3. Run the example:
   ```bash
   python code_review_agent.py
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
