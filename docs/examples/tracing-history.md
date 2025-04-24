# Tracing History Examples

This guide provides examples of how to trace the history of code using Arc Memory, showing how to follow the decision trail from a specific line of code to related commits, PRs, issues, and ADRs.

**Related Documentation:**
- [Trace Commands](../cli/trace.md) - Reference for trace commands
- [Build Commands](../cli/build.md) - Build your knowledge graph before tracing
- [Trace API](../api/trace.md) - Programmatic access to trace functionality
- [Models](../api/models.md) - Understanding the data models in trace results

## Basic History Tracing

The simplest way to trace the history of a specific line in a file is:

```bash
# Trace the history of line 42 in a file
arc trace file src/main.py 42
```

This will:
1. Find the commit that last modified line 42 in `src/main.py`
2. Traverse the knowledge graph to find related entities
3. Display the results in a table

Example output:

```
┌───────┬──────────────┬───────────────────────┬─────────────────────┬───────────────────────┐
│ Type  │ ID           │ Title                 │ Timestamp           │ Details               │
├───────┼──────────────┼───────────────────────┼─────────────────────┼───────────────────────┤
│ commit│ abc123       │ Fix bug in login form │ 2023-04-15T14:32:10 │ Author: John Doe      │
│       │              │                       │                     │ SHA: abc123def456     │
├───────┼──────────────┼───────────────────────┼─────────────────────┼───────────────────────┤
│ pr    │ 42           │ Fix login issues      │ 2023-04-16T09:15:22 │ PR #42                │
│       │              │                       │                     │ State: merged         │
│       │              │                       │                     │ URL: github.com/...   │
├───────┼──────────────┼───────────────────────┼─────────────────────┼───────────────────────┤
│ issue │ 123          │ Login form bug        │ 2023-04-10T11:20:05 │ Issue #123            │
│       │              │                       │                     │ State: closed         │
│       │              │                       │                     │ URL: github.com/...   │
└───────┴──────────────┴───────────────────────┴─────────────────────┴───────────────────────┘
```

## Adjusting Search Depth and Results

You can control the depth of the search and the number of results:

```bash
# Get more results (up to 5)
arc trace file src/main.py 42 --max-results 5

# Search deeper in the graph (up to 3 hops)
arc trace file src/main.py 42 --max-hops 3

# Combine both
arc trace file src/main.py 42 --max-results 5 --max-hops 3
```

Increasing `--max-hops` will follow longer paths in the graph, potentially finding more distantly related entities. Increasing `--max-results` will return more entities.

## Tracing History for Different File Types

Arc Memory works with any file type in your repository:

```bash
# Trace history for a Python file
arc trace file src/main.py 42

# Trace history for a JavaScript file
arc trace file src/app.js 100

# Trace history for a configuration file
arc trace file config.yaml 5

# Trace history for documentation
arc trace file docs/README.md 10
```

## Finding the Decision Behind a Feature

To understand why a particular feature was implemented:

```bash
# Find the commit that introduced the feature
git blame src/feature.py

# Note the line number where the feature was introduced (e.g., line 42)
arc trace file src/feature.py 42 --max-hops 3
```

This will show you:
1. The commit that introduced the feature
2. The PR that merged the commit
3. Any issues that were mentioned in the PR
4. Any ADRs that were related to the issues

## Tracing History Programmatically

You can also trace history programmatically in your Python code:

```python
from pathlib import Path
from arc_memory.trace import trace_history_for_file_line

# Trace the history of line 42 in a file
results = trace_history_for_file_line(
    db_path=Path("~/.arc/graph.db"),
    file_path="src/main.py",
    line_number=42,
    max_results=5,
    max_hops=3
)

# Process the results
for result in results:
    print(f"{result['type']}: {result['title']} ({result['timestamp']})")

    # Access type-specific fields
    if result['type'] == 'commit':
        print(f"  Author: {result.get('author')}")
        print(f"  SHA: {result.get('sha')}")
    elif result['type'] == 'pr':
        print(f"  PR #{result.get('number')}")
        print(f"  State: {result.get('state')}")
        print(f"  URL: {result.get('url')}")
```

## Real-World Use Cases

### Debugging a Bug

When you find a bug, trace the history of the problematic line:

```bash
arc trace file src/buggy_file.py 123
```

This can help you understand:
- Who wrote the code and why
- What PR introduced the bug
- What issues were being addressed
- What architectural decisions influenced the code

### Understanding a Complex Feature

When you need to understand a complex feature:

```bash
# Trace multiple lines
arc trace file src/complex_feature.py 42
arc trace file src/complex_feature.py 100
arc trace file src/complex_feature.py 150
```

### Code Review

During code review, trace the history of changed lines:

```bash
# Get the diff
git diff main...feature-branch

# For each significant change, trace its history
arc trace file src/changed_file.py 42
```

### Onboarding New Team Members

Help new team members understand the codebase:

```bash
# For key files, trace the history of important lines
arc trace file src/core_module.py 10
arc trace file src/core_module.py 50
arc trace file src/core_module.py 100
```

## Troubleshooting

### No History Found

If no history is found:

```bash
# Ensure the knowledge graph is built
arc build

# Check if the file is tracked by Git
git ls-files | grep your_file.py

# Verify the line number exists
wc -l your_file.py
```

### Incomplete History

If the history seems incomplete:

```bash
# Rebuild the knowledge graph
arc build

# Try increasing the search depth
arc trace file your_file.py 42 --max-hops 4
```

### Performance Issues

If tracing is slow:

```bash
# Check the size of your knowledge graph
arc doctor

# Consider limiting the scope of your graph
arc build --max-commits 1000 --days 90
```
