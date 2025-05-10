# Why Command

The Arc Memory CLI provides the `why` command for showing the decision trail for a specific line in a file. This command helps you understand why a particular line of code exists and the decisions that led to it.

**Related Documentation:**
- [Build Commands](./build.md) - Build your knowledge graph before using the why command
- [Trace Commands](./trace.md) - The underlying trace functionality
- [Relate Commands](./relate.md) - Show related nodes for an entity

## Overview

The `why` command uses the same breadth-first search (BFS) algorithm as the trace command, but presents the results in a more user-friendly format. It starts from the commit that last modified a specific line in a file and follows edges to related entities, providing a comprehensive view of the decision trail.

## Commands

### `arc why file`

Show the decision trail for a specific line in a file.

```bash
arc why file FILE_PATH LINE_NUMBER [OPTIONS]
```

This command traces the history of a specific line in a file, showing the commit that last modified it and related entities such as PRs, issues, and ADRs.

#### Arguments

- `FILE_PATH`: Path to the file, relative to the repository root.
- `LINE_NUMBER`: Line number to trace (1-based).

#### Options

- `--max-results`, `-m INTEGER`: Maximum number of results to return (default: 5).
- `--max-hops`, `-h INTEGER`: Maximum number of hops in the graph traversal (default: 3).
- `--format`, `-f [text|json|markdown]`: Output format (default: text).
- `--debug`: Enable debug logging.

#### Example

```bash
# Show the decision trail for line 42 in a file (default text format)
arc why file src/main.py 42

# Show with more results and hops
arc why file src/main.py 42 --max-results 10 --max-hops 4

# Output in JSON format
arc why file src/main.py 42 --format json

# Output in Markdown format
arc why file src/main.py 42 --format markdown

# Enable debug logging
arc why file src/main.py 42 --debug
```

### `arc why query`

Ask natural language questions about your codebase and get contextual answers.

```bash
arc why query QUESTION [OPTIONS]
```

This command leverages a local LLM to analyze your question, search the knowledge graph for relevant information, and provide a comprehensive answer with supporting evidence.

#### Arguments

- `QUESTION`: Natural language question to ask about the codebase.

#### Options

- `--max-results`, `-m INTEGER`: Maximum number of results to return (default: 5).
- `--depth`, `-d TEXT`: Search depth (shallow, medium, deep) (default: medium).
- `--format`, `-f [text|json|markdown]`: Output format (default: text).
- `--debug`: Enable debug logging.

#### Example

```bash
# Ask who implemented a feature
arc why query "Who implemented the authentication feature?"

# Ask about architectural decisions
arc why query "Why was the database schema changed last month?"

# Ask about specific technical choices
arc why query "What decision led to using SQLite instead of PostgreSQL?"

# Ask with deeper search
arc why query "How has the API evolved since version 0.2.0?" --depth deep

# Output in JSON format
arc why query "Who implemented the authentication feature?" --format json
```

## Output Formats

### Text Format

The text format presents the results in a series of panels, with each panel representing a node in the decision trail. The panels are color-coded by node type:

- **Commit**: Cyan
- **PR**: Green
- **Issue**: Yellow
- **ADR**: Blue
- **File**: Magenta

Each panel includes the node's title, ID, timestamp, and type-specific details.

### JSON Format

The JSON format returns the raw data as a JSON array, which is useful for programmatic consumption. Each node in the array includes the following fields:

- `type`: The type of the node (commit, pr, issue, adr, file)
- `id`: The ID of the node
- `title`: The title of the node
- `timestamp`: The timestamp of the node (ISO format)

Additional fields are included based on the node type:

- **Commit**: `author`, `sha`
- **PR**: `number`, `state`, `url`
- **Issue**: `number`, `state`, `url`
- **ADR**: `status`, `decision_makers`, `path`

### Markdown Format

The Markdown format presents the results in a structured Markdown document, which is useful for documentation and sharing. The document includes a title, sections for each node, and type-specific details.

## Understanding the Decision Trail

The decision trail shows the history of a specific line in a file, including:

1. The commit that last modified the line
2. The PR that merged the commit
3. Any issues that were mentioned in the PR
4. Any ADRs that were related to the issues

This helps you understand not just what changed, but why it changed, who made the decision, and what the rationale was.

## Natural Language Queries

The `arc why query` command allows you to ask questions about your codebase in natural language. This is powered by a local LLM (using Ollama with the Qwen3:4b model) that analyzes your question, searches the knowledge graph for relevant information, and provides a comprehensive answer.

The response includes:
- A brief summary of the answer
- Query understanding (how the system interpreted your question)
- A detailed answer with reasoning
- Supporting evidence from the knowledge graph with citations
- A confidence level indicating how well the available information answers your question

### Requirements for Natural Language Queries

- A built knowledge graph (run `arc build` first)
- [Ollama](https://ollama.ai) installed locally
- The Qwen3:4b model pulled (happens automatically on first use)

### Query Types

You can ask various types of questions, such as:

- **Who questions**: "Who implemented feature X?"
- **Why questions**: "Why was X changed to Y?"
- **What questions**: "What decision led to using X technology?"
- **When questions**: "When was feature X added?"
- **How questions**: "How has component X evolved over time?"

The system will search for relevant commits, PRs, issues, and ADRs to provide context-rich answers.

## Requirements

- A built knowledge graph (run `arc build` first)
- Git repository with commit history
- Optional: GitHub PRs and issues (requires GitHub authentication)
- Optional: ADRs in the repository
- For natural language queries: Ollama and the Qwen3:4b model