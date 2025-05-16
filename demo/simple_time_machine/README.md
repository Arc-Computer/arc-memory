# Simple Code Time Machine

A lightweight, easy-to-understand demo that showcases Arc Memory's temporal understanding capabilities without complex dependencies.

## Overview

The Simple Code Time Machine demonstrates how Arc Memory can help you:

1. **Explore file history** - See how a file evolved over time
2. **Understand key decisions** - Discover why code exists and who made the changes
3. **Visualize impact** - Understand how changes to a file affect other components

Unlike the full Code Time Machine demo, this simplified version:
- Has minimal dependencies (just Arc Memory and standard libraries)
- Works without requiring OpenAI API keys
- Uses simple text-based visualization
- Is designed to be easily understood and modified

## Prerequisites

- Arc Memory installed: `pip install arc-memory`
- A Git repository with a knowledge graph built: `arc build`

That's it! No other dependencies or API keys required.

## Usage

```bash
# Run the demo on a specific file
python -m demo.simple_time_machine.main --file path/to/file.py

# Or run with a specific repository path
python -m demo.simple_time_machine.main --repo /path/to/repo --file path/to/file.py

# Run in interactive mode to select a file
python -m demo.simple_time_machine.main --interactive
```

## How It Works

The Simple Code Time Machine uses Arc Memory's SDK to:

1. **Get file history** using `arc.get_entity_history()`
2. **Find decision trails** using `arc.get_decision_trail()`
3. **Analyze impact** using `arc.get_related_entities()` and `arc.analyze_component_impact()`

It then presents this information in a simple, text-based format that's easy to understand.

## Example Output

```
=== File Timeline: src/auth/login.py ===

2023-01-15: File created by Alice
  - Initial implementation of login functionality
  - Related PR: "Add basic authentication" (#42)

2023-02-20: Modified by Bob
  - Added password reset functionality
  - Related PR: "Implement password reset" (#57)

2023-04-10: Modified by Charlie
  - Security enhancement: Added rate limiting
  - Related PR: "Security improvements" (#83)

=== Key Decisions ===

Decision: Add OAuth support (Line 42)
Author: Alice
Date: 2023-02-28
Rationale: "Added OAuth to support third-party login providers as requested in issue #64"

Decision: Implement rate limiting (Line 78)
Author: Charlie
Date: 2023-04-10
Rationale: "Added rate limiting to prevent brute force attacks after security audit"

=== Impact Analysis ===

High Impact Components:
- src/auth/session.py (0.9) - Direct dependency
- src/api/endpoints.py (0.8) - Uses authentication functions

Medium Impact Components:
- src/utils/security.py (0.6) - Shared utility functions
- src/models/user.py (0.5) - Referenced by authentication logic

Low Impact Components:
- src/templates/login.html (0.3) - Indirectly affected
```

## Customization

The Simple Code Time Machine is designed to be easily customized:

1. **Modify visualization**: Edit the `visualize_*.py` files to change how information is displayed
2. **Add new analysis**: Extend the `analyze_*.py` files to add new types of analysis
3. **Change the flow**: Modify `main.py` to change the order or types of analysis performed

## Implementation Details

The demo consists of just a few simple files:

- `main.py` - Main script that orchestrates the demo
- `visualize_timeline.py` - Visualizes the file's timeline
- `visualize_decisions.py` - Visualizes key decisions
- `visualize_impact.py` - Visualizes impact analysis
- `utils.py` - Utility functions

Each file is well-commented and designed to be educational, showing how to use Arc Memory's SDK effectively.

## Comparison with Full Code Time Machine

This simplified demo is a subset of the full [Code Time Machine](../code_time_machine/) demo, which offers:

- Rich terminal UI with colorful formatting
- LLM-powered reasoning for deeper insights (requires OpenAI API key)
- More detailed visualizations
- Additional analysis capabilities

If you want the full experience and don't mind the additional dependencies, check out the complete Code Time Machine demo.

## Next Steps

After exploring this demo, you might want to:

1. **Build your own analysis tools** using the Arc Memory SDK
2. **Integrate Arc Memory** into your development workflow
3. **Explore the full Code Time Machine** for more advanced features
4. **Check out other examples** in the `docs/examples/` directory
