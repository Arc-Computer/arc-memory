# Arc: The Memory Layer for Engineering Teams

<p align="center">
  <img src="public/Arc SDK Header.png" alt="Arc Logo"/> 
</p>

<p align="center">
  <a href="https://www.arc.computer"><img src="https://img.shields.io/badge/website-arc.computer-blue" alt="Website"/></a>
  <a href="https://github.com/Arc-Computer/arc-memory/actions"><img src="https://img.shields.io/badge/tests-passing-brightgreen" alt="Tests"/></a>
  <a href="https://pypi.org/project/arc-memory/"><img src="https://img.shields.io/pypi/v/arc-memory" alt="PyPI"/></a>
  <a href="https://pypi.org/project/arc-memory/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue" alt="Python"/></a>
  <a href="https://github.com/Arc-Computer/arc-memory/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Arc-Computer/arc-memory" alt="License"/></a>
  <a href="https://docs.arc.computer"><img src="https://img.shields.io/badge/docs-mintlify-teal" alt="Documentation"/></a>
</p>

*Arc is the memory layer for engineering teams — it records **why** every change was made, predicts the blast-radius of new code before you merge, and feeds that context to agents so they can handle long-range refactors safely.*

## What The Arc SDK Does

1. **Record the why.**
   Arc's Temporal Knowledge Graph ingests commits, PRs, issues, and ADRs to preserve architectural intent and decision history—entirely on your machine.

2. **Model the system.**
   From that history Arc derives a **causal graph** of services, data flows, and constraints—a lightweight world-model that stays in sync with the codebase.

3. **Capture causal relationships.**
   Arc tracks decision → implication → code-change chains, enabling multi-hop reasoning to show why decisions were made and their predicted impact.

4. **Enhance PR reviews.**
   Arc's GitHub extension surfaces decision trails and blast-radius hints directly in the PR view, giving reviewers instant context before they hit "Approve."

## Quick Start

```bash
# Install Arc Memory
pip install arc-memory[github]

# Build a knowledge graph from your repository
cd /path/to/your/repo
arc build --github

# Understand why a piece of code exists
arc why file src/auth/login.py 42

# Ask natural language questions about your codebase
arc why query "Why was the authentication system refactored?"
```

For a complete setup guide, see our [Quickstart Documentation](./docs/quickstart.md).

## Core Features

### Knowledge Graph

```bash
# Build with GitHub and Linear data
arc build --github --linear

# With OpenAI enhancement for deeper analysis
arc build --github --linear --llm-enhancement --llm-provider openai
```

### Decision Trails

```bash
# Show decision trail for a specific file and line
arc why file path/to/file.py 42

# Ask natural language questions
arc why query "What decision led to using SQLite instead of PostgreSQL?"
```

### GitHub Actions Integration

```bash
# Export knowledge graph for GitHub Actions
arc export <commit-sha> export.json --compress
```

Add to your workflow:
```yaml
- name: Analyze PR with Arc Memory
  uses: arc-computer/arc-memory-action@v1
  with:
    pr-number: ${{ github.event.pull_request.number }}
```

## SDK for Developers

```python
from arc_memory import Arc

# Initialize Arc with your repository path
arc = Arc(repo_path="./")

# Ask a question about your codebase
result = arc.query("What were the major changes in the last release?")
print(f"Answer: {result.answer}")

# Find out why a specific piece of code exists
decision_trail = arc.get_decision_trail("src/auth/login.py", 42)
```

## Documentation

- [Getting Started Guide](./docs/getting_started.md) - Complete setup instructions
- [SDK Documentation](./docs/sdk/README.md) - Using the Arc Memory SDK
- [CLI Reference](./docs/cli/README.md) - Command-line interface details
- [Examples](./docs/examples/README.md) - Real-world usage examples

## Why It Matters

As AI generates exponentially more code, the critical bottleneck shifts from *generation* to *understanding, provenance, and coordination*. Arc Memory preserves the reasoning, trade-offs, and decisions that shaped your codebase, enabling:

- **Faster onboarding** for new team members
- **Reduced knowledge loss** when developers leave
- **More efficient code reviews** with contextual insights
- **Safer refactoring** with impact prediction
- **Better agent coordination** through shared memory

## License

MIT
