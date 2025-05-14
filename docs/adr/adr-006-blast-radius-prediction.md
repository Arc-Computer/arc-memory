---
title: Heuristic-First Approach to Blast Radius Prediction
date: 2025-05-14
status: accepted
decision_makers: ["Jarrod Barnes", "Engineering Team"]
---

# Heuristic-First Approach to Blast Radius Prediction

## Context

Predicting the "blast radius" of code changes—understanding which components might be affected by a change to a specific part of the codebase—is a key differentiator for Arc Memory. This capability helps developers assess risk, plan refactoring efforts, and understand the architecture of their codebase.

We need to decide on an implementation approach for blast radius prediction that balances:

- **Accuracy**: The predictions should be useful and reasonably accurate.
- **Performance**: The analysis should complete quickly enough to be used in interactive workflows.
- **Explainability**: Developers should understand why certain components are included in the blast radius.
- **Implementation Complexity**: The approach should be feasible to implement with our current resources.
- **Evolutionary Path**: The approach should allow for future improvements as we gather more data and feedback.

We considered several approaches:
1. Pure heuristic-based prediction using explicit dependencies and co-change patterns
2. LLM-based prediction using natural language understanding of code relationships
3. Machine learning models trained on historical change data
4. Reinforcement learning systems that improve over time
5. Hybrid approaches combining multiple techniques

## Decision

We will implement blast radius prediction using a heuristic-first approach, with a clear path to incorporating LLM-based enhancements and eventually reinforcement learning.

The initial implementation will focus on explicit dependencies and co-change patterns derived from the knowledge graph, without requiring LLM calls for basic functionality.

## Consequences

### Positive

- **Immediate Utility**: Heuristic-based prediction provides immediate value without requiring extensive training data or complex models.
- **Predictable Performance**: Heuristic approaches have more predictable performance characteristics than LLM-based approaches.
- **Explainability**: The reasoning behind predictions is clear and can be directly traced to graph relationships.
- **Lower Resource Requirements**: Heuristic approaches don't require LLM API calls for basic functionality, reducing costs and dependencies.
- **Incremental Improvement**: We can gradually enhance the heuristics based on user feedback and observed patterns.
- **Foundation for Advanced Approaches**: The heuristic approach provides a baseline and training data for future ML/RL approaches.

### Negative

- **Limited Sophistication**: Purely heuristic approaches may miss subtle relationships that require deeper understanding of code semantics.
- **Manual Tuning Required**: Heuristics require manual tuning and adjustment based on feedback and observed patterns.
- **Domain-Specific Limitations**: Heuristics that work well for one codebase or language may not generalize well to others.
- **Ceiling on Accuracy**: There's a natural ceiling on how accurate purely heuristic approaches can become without incorporating more advanced techniques.

### Mitigations

To address these limitations:

1. **Layered Enhancement Approach**: We'll implement a layered approach where basic heuristics can be enhanced with optional LLM-based analysis:
   - **Level 1**: Basic heuristics using explicit dependencies (no LLM required)
   - **Level 2**: Enhanced analysis with LLM-based insights (requires API key)
   - **Level 3**: Future RL-based prediction (planned for later phases)

2. **Feedback Collection**: We'll collect user feedback on prediction accuracy to improve our heuristics over time.

3. **Confidence Scoring**: We'll include confidence scores with predictions to help users understand the reliability of different aspects of the analysis.

4. **Extensible Framework**: We'll design the prediction system to be extensible, allowing for easy integration of more sophisticated approaches in the future.

## Implementation Details

The initial heuristic-based implementation will consider:

1. **Direct Dependencies**: Components that directly depend on or are depended upon by the target component.

2. **Indirect Dependencies**: Components connected through a chain of dependencies, with configurable depth.

3. **Co-Change Patterns**: Components that have historically changed together with the target component.

4. **Structural Similarity**: Components with similar structure or purpose to the target component.

5. **Import/Export Relationships**: Components that share imports or exports with the target component.

The implementation will be exposed through the `analyze_component_impact` method in the SDK, which will return a list of potentially affected components with impact scores and explanations.

For enhanced analysis, we'll provide optional LLM-based enrichment that can provide deeper insights into why components are related and how changes might propagate through the system.

This approach gives us a solid foundation while preserving a clear path to more sophisticated prediction capabilities in the future.
