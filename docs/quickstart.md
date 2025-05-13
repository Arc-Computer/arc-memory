# Arc Memory Quickstart Guide

This guide will help you get up and running with Arc Memory in under 30 minutes. We'll cover installation, authentication, building your first knowledge graph, and running basic queries.

## 🚀 5-Minute Setup for the Impatient

Want to get started as quickly as possible? Here's the express setup:

```bash
# Install Arc Memory with all integrations
pip install arc-memory[all]

# Authenticate with GitHub
arc auth github

# Build your knowledge graph
cd /path/to/your/repo
arc build --github

# Ask a question about your codebase
arc why query "Why was this feature implemented?"
```

That's it! For more detailed instructions and advanced features, continue reading below.

## Step 1: Installation (2 minutes)

Arc Memory requires Python 3.10 or higher.

```bash
# Basic installation
pip install arc-memory

# Or with GitHub and Linear integration
pip install arc-memory[github,linear]

# For LLM enhancement capabilities
pip install arc-memory[llm]

# For all features
pip install arc-memory[all]
```

### One-Line Installation (Alternative)

You can also use our installation script for a streamlined setup:

```bash
curl -sSL https://arc.computer/install.sh | bash

# Or with specific options
curl -sSL https://arc.computer/install.sh | bash -s -- --with-github --with-llm
```

### Installing Ollama (Optional for Enhanced Analysis)

For enhanced natural language queries, you can use Ollama with local models. Install Ollama from [ollama.ai/download](https://ollama.ai/download).

After installing Ollama, start it with:

```bash
ollama serve
```

And pull a model (in a separate terminal):

```bash
ollama pull llama2
```

### Using OpenAI for Enhanced Analysis (Recommended)

For the highest quality analysis, we recommend using OpenAI models:

```bash
# Install with OpenAI support
pip install arc-memory[openai]

# Set your API key
export OPENAI_API_KEY=your-api-key

# Build with OpenAI enhancement
arc build --llm-provider openai --llm-model gpt-4o --llm-enhancement
```

## Step 2: Authentication (5 minutes)

### GitHub Authentication

```bash
# Using the CLI (recommended)
arc auth github

# Or programmatically
python -c "from arc_memory.auth.github import authenticate_github; token = authenticate_github(); print(f'Token: {token[:5]}...')"
```

### Linear Authentication (Optional)

```bash
# Using the CLI (recommended)
arc auth linear

# Or programmatically
python -c "from arc_memory.auth.linear import authenticate_linear; token = authenticate_linear(); print(f'Token: {token[:5]}...')"
```

## Step 3: Build Your Knowledge Graph (10 minutes)

```bash
# Navigate to your repository
cd /path/to/your/repo

# Build with GitHub data
arc build --github

# Or with both GitHub and Linear data
arc build --github --linear

# For enhanced analysis (takes longer but provides richer insights)
arc build --github --linear --llm-enhancement standard
```

You'll see progress indicators as Arc analyzes your repository and builds the knowledge graph.

## Step 4: Run Basic Queries (5 minutes)

### Using the CLI

```bash
# Ask a question about your codebase (requires Ollama to be running)
arc why query "Why was the authentication system refactored?"

# Get the decision trail for a specific file and line
arc why file src/auth/login.py 42

# Find related entities for a commit
arc relate commit abc123
```

### Using the SDK

Create a file named `arc_query.py`:

```python
from arc_memory import Arc

# Initialize Arc with your repository path
arc = Arc(repo_path="./")

# Ask a question about your codebase (requires Ollama to be running)
result = arc.query("Why was the authentication system refactored?")
print(f"Answer: {result.answer}")
print(f"Confidence: {result.confidence}")
print("Evidence:")
for evidence in result.evidence:
    print(f"- {evidence['title']}")

# Get the decision trail for a specific file and line
decision_trail = arc.get_decision_trail("src/auth/login.py", 42)
for entry in decision_trail:
    print(f"\nDecision: {entry.title}")
    print(f"Rationale: {entry.rationale}")
    print(f"Importance: {entry.importance}")

# Find related entities for a commit
related = arc.get_related_entities("commit:abc123")
print("\nRelated entities:")
for entity in related:
    print(f"- {entity.title} ({entity.relationship})")
```

Run it:

```bash
python arc_query.py
```

## Step 5: Framework Integration (8 minutes)

### LangChain Integration

Create a file named `arc_langchain.py`:

```python
from arc_memory import Arc
from langchain_openai import ChatOpenAI

# Initialize Arc with your repository path
arc = Arc(repo_path="./")

# Get Arc Memory functions as LangChain tools
from arc_memory.sdk.adapters import get_adapter
langchain_adapter = get_adapter("langchain")
tools = langchain_adapter.adapt_functions([
    arc.query,
    arc.get_decision_trail,
    arc.get_related_entities
])

# Create a LangChain agent with Arc Memory tools
llm = ChatOpenAI(model="gpt-4o")
agent = langchain_adapter.create_agent(
    tools=tools,
    llm=llm,
    system_message="You are a helpful assistant with access to Arc Memory."
)

# Use the agent
response = agent.invoke({"input": "What's the decision trail for src/auth/login.py line 42?"})
print(response)
```

Run it:

```bash
python arc_langchain.py
```

### OpenAI Integration

Create a file named `arc_openai.py`:

```python
from arc_memory import Arc

# Initialize Arc with your repository path
arc = Arc(repo_path="./")

# Get Arc Memory functions as OpenAI tools
from arc_memory.sdk.adapters import get_adapter
openai_adapter = get_adapter("openai")
tools = openai_adapter.adapt_functions([
    arc.query,
    arc.get_decision_trail,
    arc.get_related_entities
])

# Create an OpenAI agent with Arc Memory tools
agent = openai_adapter.create_agent(
    tools=tools,
    model="gpt-4o",
    system_message="You are a helpful assistant with access to Arc Memory."
)

# Use the agent
response = agent("What's the decision trail for src/auth/login.py line 42?")
print(response)
```

Run it:

```bash
python arc_openai.py
```

## Troubleshooting Common Issues

### Installation Issues

| Issue | Solution |
|-------|----------|
| **"Command not found: arc"** | Make sure the Python bin directory is in your PATH. Try installing with `pip install --user arc-memory` and check your PATH. |
| **"Python version must be >= 3.10"** | Update your Python version or use a virtual environment with Python 3.10+. |
| **"No module named 'arc_memory'"** | Verify installation with `pip list \| grep arc-memory`. If not listed, reinstall. |
| **"Error: Microsoft Visual C++ 14.0 is required"** | Install the [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/). |

### Authentication Issues

| Issue | Solution |
|-------|----------|
| **GitHub authentication fails** | Try manual authentication: `arc auth github --manual` and follow the prompts. |
| **Linear authentication fails** | Verify your Linear API key at [linear.app/settings/api](https://linear.app/settings/api). |
| **"Token not found"** | Run `arc doctor` to check authentication status and follow the suggested fixes. |

### Knowledge Graph Building Issues

| Issue | Solution |
|-------|----------|
| **"No such file or directory: '.arc'"** | Make sure you're in a Git repository. Run `git status` to verify. |
| **"Failed to build knowledge graph"** | Check permissions for the `.arc` directory. Try running with `--verbose` for more details. |
| **"LLM enhancement failed"** | For Ollama: ensure Ollama is running with `ollama serve`. For OpenAI: check your API key. |
| **Build process is too slow** | Use `--incremental` for faster builds after the initial one. Try `--parallel` for multi-threading. |

### Query Issues

| Issue | Solution |
|-------|----------|
| **"No knowledge graph found"** | Run `arc build` first to create the knowledge graph. |
| **"Failed to connect to Ollama"** | Ensure Ollama is running with `ollama serve` in a separate terminal. |
| **Empty or low-quality responses** | Try building with `--llm-enhancement` for richer analysis or use OpenAI models. |
| **"Entity not found"** | Check entity ID format. For files, use `file:path/to/file.py`. |

## Congratulations!

You've successfully:
- Installed Arc Memory
- Authenticated with GitHub (and optionally Linear)
- Built a knowledge graph from your repository
- Run basic queries using both the CLI and SDK
- Integrated Arc Memory with LangChain and OpenAI

## Next Steps

- [Getting Started Guide](./getting_started.md) - More detailed setup and usage instructions
- [SDK Documentation](./sdk/README.md) - Learn more about the SDK
- [CLI Reference](./cli/README.md) - Explore all CLI commands
- [Examples](./examples/README.md) - See more advanced examples
- [API Reference](./sdk/api_reference.md) - Detailed API documentation
- [GitHub Actions Integration](./examples/github_actions/README.md) - Integrate Arc Memory into your CI/CD pipeline
