# Arc Memory Quickstart Demo

A 5-minute demo that shows the immediate value of Arc Memory with minimal setup.

## Overview

This demo showcases how Arc Memory can instantly provide valuable insights about your codebase:

1. **Code Context**: Understand why code exists and who wrote it
2. **Dependency Analysis**: See what depends on a specific file or function
3. **Decision Archaeology**: Discover the reasoning behind code decisions

All in under 5 minutes, with minimal setup!

## Prerequisites

- Arc Memory installed: `pip install arc-memory`
- A Git repository (your own project or any open source project)

## Quick Start

```bash
# Clone a repository if you don't have one
git clone https://github.com/your-favorite/repo.git
cd repo

# Build the knowledge graph (takes 1-2 minutes)
arc build 

# Run the quickstart demo
python -m arc_memory.examples.quickstart

# Or specify a file to analyze
python -m arc_memory.examples.quickstart --file path/to/interesting/file.py
```

## What You'll See

The demo will:

1. **Find an interesting file** in your codebase (or use the one you specified)
2. **Show its history** including who wrote it and why
3. **Identify key dependencies** that rely on this file
4. **Highlight important decisions** that shaped the file
5. **Visualize the file's relationships** to other components

All presented in a simple, easy-to-understand format.

## Example Output

```
=== Arc Memory Quickstart Demo ===

Analyzing file: src/core/auth.py

File History:
- Created by Alice Chen on 2023-01-15
- Modified by Bob Smith on 2023-02-20 (Added password reset)
- Modified by Charlie Davis on 2023-04-10 (Security enhancements)

Key Dependencies:
- src/api/endpoints.py: Uses authentication functions
- src/utils/security.py: Provides encryption utilities
- src/models/user.py: User data model used by auth

Important Decisions:
- Added OAuth support (PR #42) to enable third-party login
- Implemented rate limiting (PR #83) after security audit
- Switched to bcrypt for password hashing (PR #57)

Relationship Visualization:
[Simple ASCII visualization of relationships]

=== Demo Complete ===

Try these commands to explore further:
- arc why src/core/auth.py:42
- arc relate file:src/core/auth.py
- arc query "Why was rate limiting added to the auth system?"
```

## How It Works

The Quickstart Demo uses Arc Memory's SDK to:

1. **Connect to the knowledge graph** using `Arc()`
2. **Find an interesting file** using heuristics or use your specified file
3. **Query the graph** using various SDK methods:
   - `arc.get_entity_history()`
   - `arc.get_related_entities()`
   - `arc.get_decision_trail()`
4. **Present the results** in a simple, readable format

## Next Steps

After seeing the immediate value of Arc Memory, you might want to:

1. **Explore the CLI** with commands like `arc why`, `arc relate`, and `arc query`
2. **Try the SDK** in your own scripts and tools
3. **Check out other examples** in the `docs/examples/` directory
4. **Build your own tools** on top of Arc Memory

## Customization

You can customize the Quickstart Demo by:

1. **Specifying a file** with the `--file` parameter
2. **Adjusting the analysis depth** with `--depth`
3. **Focusing on specific aspects** with `--focus history|dependencies|decisions`

For example:
```bash
python -m arc_memory.examples.quickstart --file src/core/auth.py --depth 3 --focus decisions
```
