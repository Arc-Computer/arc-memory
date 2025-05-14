# Arc Memory Demo Guide

This guide contains instructions for running the Arc Memory demos.

## Prerequisites

Before running the demos, make sure you have:

1. **Arc Memory installed**: `pip install arc-memory[all]`
2. **OpenAI API key set**: `export OPENAI_API_KEY=your-api-key`
3. **GitHub authentication**: `arc auth github`
4. **Required Python packages**: `pip install colorama matplotlib networkx`

## Demo Checklist

- [ ] Ensure OPENAI_API_KEY is set in the environment
- [ ] Verify knowledge graph exists and is up to date
- [ ] Test all demo scripts one final time
- [ ] Have all terminal windows pre-arranged

## 1. Code Review Assistant Demo

- **Purpose**: Showcase how Arc Memory provides context for code review and understanding.
- **Run the demo**:
  ```bash
  ./demo_code_review.sh
  ```
- **Key points to highlight**:
  - Incremental updates (52% faster than before)
  - Decision trails showing why code exists
  - Impact analysis showing what might be affected
  - Relationships between components
  - Easy SDK integration

**Duration**: ~5 minutes

## 2. PR Impact Analysis Demo

- **Purpose**: Show how Arc Memory can predict the impact of changes before they're merged.
- **Run the demo**:
  ```bash
  python pr_impact_analysis.py 71
  ```
- **Key points to highlight**:
  - Automatic identification of affected components
  - Risk assessment based on impact analysis
  - Recommendations for review process
  - Integration potential with CI/CD pipelines

**Duration**: ~3-4 minutes

## 3. Blast Radius Visualization Demo

- **Purpose**: Visually demonstrate the potential impact of changes to a file.
- **Run the demo**:
  ```bash
  python blast_radius_viz.py arc_memory/auto_refresh/core.py
  ```
- **Key points to highlight**:
  - Visual representation of affected components
  - Centrality of the changed file in the codebase
  - Strength of relationships between components
  - Potential for integration with PR review tools

**Duration**: ~2-3 minutes

## Talking Points

### Business Value

- **Reduced MTTR**: Arc Memory helps teams understand code context faster, reducing Mean Time To Resolution for incidents.
- **Safer Changes**: By predicting the impact of changes, teams can make more informed decisions about code changes.
- **Knowledge Preservation**: Arc Memory captures the decision trails and reasoning behind code, preserving institutional knowledge.
- **Onboarding Acceleration**: New team members can quickly understand why code exists and how it relates to other components.

### Technical Differentiators

- **Temporal Knowledge Graph**: Arc Memory builds a bi-temporal knowledge graph that captures the evolution of code over time.
- **Causal Relationships**: The graph captures causal relationships between decisions, implications, and code changes.
- **Framework Agnostic**: The SDK is designed to work with any agent framework, including LangChain, OpenAI, and custom solutions.
- **Local-First**: Arc Memory runs locally by default, ensuring privacy and performance.

## Troubleshooting

If you encounter issues during the demo:

1. **Knowledge graph not found**: Run `arc build --github` to build the graph.
2. **OpenAI API key not set**: Set the environment variable with `export OPENAI_API_KEY=your-api-key`.
3. **Missing dependencies**: Install required packages with `pip install colorama matplotlib networkx`.
4. **GitHub authentication**: Run `arc auth github` to authenticate with GitHub.

## Next Steps

After the demo, suggest these next steps for interested parties:

1. **Try Arc Memory**: Install and try Arc Memory on their own repositories.
2. **Explore the SDK**: Integrate Arc Memory into their own tools and workflows.
3. **Join the Community**: Join the Arc Memory community for support and updates.
4. **Request a Follow-up**: Schedule a follow-up call to discuss specific use cases.
