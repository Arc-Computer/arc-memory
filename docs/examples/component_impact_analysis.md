# Component Impact Analysis

This document provides detailed examples and guidance for using Arc Memory's component impact analysis features to predict the potential impact of changes to components in your codebase.

## Overview

Component impact analysis helps you understand the potential "blast radius" of changes to a specific component in your codebase. This is particularly useful for:

- Planning refactoring efforts
- Assessing risk before making changes
- Identifying unexpected dependencies
- Prioritizing code reviews
- Understanding the architecture of your codebase

Arc Memory analyzes three types of impact:

1. **Direct Impact**: Components that directly depend on or are depended upon by the target component
2. **Indirect Impact**: Components that are connected to the target component through a chain of dependencies
3. **Potential Impact**: Components that have historically changed together with the target component (co-change patterns)

## Basic Usage

The simplest way to analyze component impact is to use the `analyze_component_impact` method of the `Arc` class:

```python
from arc_memory import Arc

# Initialize Arc with the repository path
arc = Arc(repo_path="./")

# Analyze the potential impact of changes to a component
impact_results = arc.analyze_component_impact(component_id="file:src/auth/login.py")

# Print the results
for result in impact_results:
    print(f"{result.title}: {result.impact_score}")
```

## Advanced Usage

For more detailed analysis, you can use additional parameters:

```python
# Define a progress callback function
def progress_callback(stage, message, progress):
    print(f"[{stage}] {message} ({progress:.0%})")

# Advanced impact analysis with progress reporting
impact_results = arc.analyze_component_impact(
    component_id="file:src/auth/login.py",
    impact_types=["direct", "indirect", "potential"],
    max_depth=5,
    cache=True,
    callback=progress_callback
)

# Process and display the results
for result in impact_results:
    print(f"Component: {result.title}")
    print(f"Impact Score: {result.impact_score}")
    print(f"Impact Type: {result.impact_type}")
    print(f"Impact Path: {' -> '.join(result.impact_path)}")
    print("Properties:")
    for key, value in result.properties.items():
        print(f"- {key}: {value}")
    print("Related Entities:")
    for entity in result.related_entities:
        print(f"- {entity.title} ({entity.relationship})")
    print("---")
```

### Parameters Explained

- **component_id**: The ID of the component to analyze. This can be a file, directory, module, or any other component in your codebase.
- **impact_types**: Types of impact to include in the analysis. Options are:
  - `"direct"`: Components that directly depend on or are depended upon by the target component
  - `"indirect"`: Components that are connected to the target component through a chain of dependencies
  - `"potential"`: Components that have historically changed together with the target component
- **max_depth**: Maximum depth of indirect dependency analysis. Higher values will analyze more distant dependencies but may take longer.
- **cache**: Whether to use cached results if available. Set to `False` to force a fresh analysis.
- **callback**: Optional callback function for progress reporting.

## Understanding the Results

Each result in the returned list is an `ImpactResult` object (which extends `EntityDetails`) with the following attributes:

- **id**: The ID of the affected component
- **type**: The type of the component (e.g., "FILE", "DIRECTORY", "MODULE")
- **title**: The title or name of the component
- **body**: Additional description or content of the component (optional)
- **timestamp**: The timestamp of the entity (optional)
- **properties**: Dictionary of component properties
- **related_entities**: List of entities related to this component
- **impact_type**: Type of impact ("direct", "indirect", or "potential")
- **impact_score**: A score between 0 and 1 indicating the strength of the impact
- **impact_path**: List of component IDs showing the path of dependencies from the target component to this component

## Practical Examples

### Example 1: Analyzing Impact on a Core Component

```python
from arc_memory import Arc

arc = Arc(repo_path="./")

# Analyze impact on a core component
impact_results = arc.analyze_component_impact(
    component_id="file:src/core/database.py",
    impact_types=["direct", "indirect"],
    max_depth=3
)

# Group results by impact type
direct_impacts = [r for r in impact_results if r.impact_type == "direct"]
indirect_impacts = [r for r in impact_results if r.impact_type == "indirect"]

print(f"Direct impacts: {len(direct_impacts)}")
print(f"Indirect impacts: {len(indirect_impacts)}")

# Sort by impact score
high_impact = [r for r in impact_results if r.impact_score > 0.7]
print(f"High impact components: {len(high_impact)}")
for result in sorted(high_impact, key=lambda x: x.impact_score, reverse=True):
    print(f"{result.title}: {result.impact_score}")
```

### Example 2: Visualizing Impact with NetworkX

```python
import networkx as nx
import matplotlib.pyplot as plt
from arc_memory import Arc

arc = Arc(repo_path="./")

# Analyze impact
impact_results = arc.analyze_component_impact(
    component_id="file:src/api/routes.py",
    impact_types=["direct", "indirect"],
    max_depth=2
)

# Create a graph
G = nx.DiGraph()

# Add the target component
G.add_node("TARGET", label="routes.py", impact=1.0)

# Add impacted components
for result in impact_results:
    G.add_node(result.id, label=result.title.split("/")[-1], impact=result.impact_score)

    # Add edges based on impact path
    path = result.impact_path
    for i in range(len(path) - 1):
        if path[i] == "file:src/api/routes.py":
            G.add_edge("TARGET", path[i+1])
        else:
            G.add_edge(path[i], path[i+1])

# Draw the graph
pos = nx.spring_layout(G)
node_colors = [G.nodes[n].get("impact", 0.5) for n in G.nodes()]
labels = {n: G.nodes[n].get("label", n) for n in G.nodes()}

plt.figure(figsize=(12, 8))
nx.draw(G, pos, with_labels=True, labels=labels,
        node_color=node_colors, cmap=plt.cm.Reds,
        node_size=1000, arrows=True)
plt.title("Impact Analysis for routes.py")
plt.savefig("impact_analysis.png")
plt.show()
```

### Example 3: Integrating with CI/CD Pipeline

```python
import sys
from arc_memory import Arc

def analyze_changed_files(repo_path, changed_files, threshold=0.7):
    """Analyze the impact of changed files and fail if high-impact components are affected."""
    arc = Arc(repo_path=repo_path)
    high_impact_changes = []

    for file_path in changed_files:
        component_id = f"file:{file_path}"
        impact_results = arc.analyze_component_impact(
            component_id=component_id,
            impact_types=["direct", "indirect"],
            max_depth=2
        )

        # Check for high-impact results
        high_impact = [r for r in impact_results if r.impact_score > threshold]
        if high_impact:
            high_impact_changes.append((file_path, high_impact))

    return high_impact_changes

if __name__ == "__main__":
    # Get changed files from command line arguments
    repo_path = sys.argv[1]
    changed_files = sys.argv[2:]

    high_impact_changes = analyze_changed_files(repo_path, changed_files)

    if high_impact_changes:
        print("⚠️ High-impact changes detected!")
        for file_path, impacts in high_impact_changes:
            print(f"\n{file_path} affects:")
            for impact in impacts:
                print(f"  - {impact.title} (score: {impact.impact_score:.2f})")

        # Exit with error code to fail the CI pipeline
        sys.exit(1)
    else:
        print("✅ No high-impact changes detected.")
        sys.exit(0)
```

## Best Practices

1. **Start with direct impacts**: Begin by analyzing direct impacts before diving into indirect impacts.
2. **Limit max_depth**: Use a reasonable max_depth (2-3) to avoid performance issues with large codebases.
3. **Focus on high-impact scores**: Pay special attention to components with impact scores above 0.7.
4. **Combine with other analyses**: Use impact analysis alongside decision trails and entity relationships for a complete picture.
5. **Cache results**: Enable caching for better performance when running repeated analyses.
6. **Use in CI/CD**: Integrate impact analysis into your CI/CD pipeline to automatically detect high-risk changes.
7. **Visualize results**: Use visualization tools to better understand complex dependency networks.

## Troubleshooting

### Common Issues

1. **Component not found**: Ensure the component ID is correct and the component exists in your knowledge graph.
2. **Performance issues**: Reduce max_depth or limit impact_types for faster analysis.
3. **Missing dependencies**: Make sure your knowledge graph is up-to-date with `arc build`.
4. **Unexpected results**: Verify that your knowledge graph includes all relevant data sources.

### Error Handling

```python
from arc_memory import Arc
from arc_memory.sdk.errors import QueryError

try:
    arc = Arc(repo_path="./")
    impact_results = arc.analyze_component_impact(component_id="file:src/auth/login.py")
    # Process results...
except QueryError as e:
    print(f"Error analyzing component impact: {e}")
    # Handle the error appropriately
```
