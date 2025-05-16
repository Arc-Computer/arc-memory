# Temporal Understanding in Arc Memory

Arc Memory's bi-temporal knowledge graph is a core differentiator that enables powerful temporal reasoning about your codebase. This document explains the bi-temporal model and how it helps you understand the evolution of your code over time.

## What is Bi-Temporal Modeling?

Bi-temporal modeling tracks two distinct time dimensions:

1. **Valid Time**: When something happened in the real world
2. **Transaction Time**: When it was recorded in the system

This dual-time approach enables powerful queries that traditional version control systems cannot support:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                   Transaction Time                      │
│                   (When recorded)                       │
│                          │                              │
│                          ▼                              │
│                                                         │
│  ┌─────────┐        ┌──────────┐        ┌──────────┐   │
│  │ Jan 1   │        │ Jan 15   │        │ Feb 1    │   │
│  │         │        │          │        │          │   │
│  │ Commit  │───────▶│ PR Merge │───────▶│ Issue    │   │
│  │ 42abc   │        │ #123     │        │ #456     │   │
│  └─────────┘        └──────────┘        └──────────┘   │
│                                                         │
│                          ▲                              │
│                          │                              │
│                      Valid Time                         │
│                   (When it happened)                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Why Bi-Temporal Matters for Code

Traditional version control systems like Git track only a single timeline - the commit history. This misses critical context:

1. **Delayed Documentation**: When a decision is documented weeks after implementation
2. **Retroactive Changes**: When a PR description is updated after merging
3. **Historical Understanding**: What we knew about the code at a specific point in time

Arc Memory's bi-temporal model captures this nuanced history, enabling you to:

- Trace the evolution of code with complete context
- Understand what was known when decisions were made
- Reconstruct the state of knowledge at any point in time

## Core Temporal Capabilities

### 1. Point-in-Time Queries

Ask questions about what was known at a specific point in time:

```python
# What did we know about the authentication system on January 15th?
result = arc.query_at_time(
    "What is the authentication system architecture?",
    point_in_time=datetime(2023, 1, 15)
)
```

### 2. Time Travel Analysis

Analyze how understanding evolved over time:

```python
# How did our understanding of the payment system evolve?
timeline = arc.get_concept_timeline("payment system")
for entry in timeline:
    print(f"{entry.timestamp}: {entry.understanding}")
```

### 3. Decision Archaeology

Trace decisions to understand the context when they were made:

```python
# Why was this authentication approach chosen?
decision_trail = arc.get_decision_trail("src/auth/login.js", 42)
for decision in decision_trail:
    print(f"Decision: {decision.title}")
    print(f"Made on: {decision.valid_time}")
    print(f"Recorded on: {decision.transaction_time}")
    print(f"Context: {decision.rationale}")
```

### 4. Temporal Impact Analysis

Understand how changes propagate through the system over time:

```python
# How did this change impact the system over time?
impact = arc.analyze_temporal_impact("file:src/auth/login.js")
for timepoint, affected_components in impact.items():
    print(f"At {timepoint}:")
    for component in affected_components:
        print(f"  - {component.id}: {component.impact_score}")
```

## Bi-Temporal Data Model

Arc Memory's schema explicitly tracks both valid time and transaction time:

```
┌─────────────────────────────────────────────────────────┐
│                     Node Schema                         │
├─────────────┬─────────────┬─────────────┬─────────────┬─┤
│ id          │ type        │ title       │ body        │ │
├─────────────┼─────────────┼─────────────┼─────────────┼─┤
│ valid_from  │ valid_to    │ tx_from     │ tx_to       │ │
└─────────────┴─────────────┴─────────────┴─────────────┴─┘
```

- **valid_from/valid_to**: When the entity existed in the real world
- **tx_from/tx_to**: When the entity was recorded in the knowledge graph

This schema enables powerful temporal queries that traditional systems cannot support.

## Practical Applications

### Code Archaeology

Understand why code exists and how it evolved:

```bash
# Trace the history of a specific file
arc why file src/auth/login.js --timeline

# Understand the context of a specific line
arc why file src/auth/login.js 42 --temporal-context
```

### Decision Understanding

Reconstruct the context in which decisions were made:

```bash
# What did we know about authentication when we chose OAuth?
arc query "What authentication options were considered?" --at-time 2023-01-15

# How did our understanding change after implementation?
arc query "What authentication options were considered?" --at-time 2023-03-01
```

### Impact Prediction

Predict how changes will propagate through the system over time:

```bash
# How will this change impact the system over the next month?
arc analyze-impact file:src/auth/login.js --temporal-projection 30d
```

## Implementation Details

Arc Memory implements bi-temporal modeling through:

1. **Temporal Metadata**: Every node and edge in the knowledge graph has temporal metadata
2. **Temporal Queries**: The query engine respects temporal constraints
3. **Temporal Reasoning**: The reasoning engine understands temporal relationships
4. **Temporal Visualization**: The UI visualizes temporal data effectively

## Comparison with Traditional Approaches

| Capability | Git History | Documentation | Arc Memory |
|------------|------------|---------------|------------|
| Code Changes | ✅ | ❌ | ✅ |
| Decision Context | ❌ | Partial | ✅ |
| Knowledge Evolution | ❌ | ❌ | ✅ |
| Temporal Queries | ❌ | ❌ | ✅ |
| Impact Prediction | ❌ | ❌ | ✅ |

## Conclusion

Arc Memory's bi-temporal model provides a unique lens into your codebase, enabling you to understand not just what changed, but why it changed and how that understanding evolved over time. This temporal intelligence is critical for maintaining complex systems, onboarding new team members, and making informed architectural decisions.

By capturing both when things happened and when they were recorded, Arc Memory creates a complete picture of your codebase's evolution that traditional tools simply cannot provide.
