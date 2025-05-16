# Arc Memory Demo Guide

This guide contains instructions for running the Arc Memory demos.

## Prerequisites

Before running the demos, make sure you have:

1. **Arc Memory installed**: `pip install arc-memory[all]`
2. **OpenAI API key set**: `export OPENAI_API_KEY=your-api-key` (required for GPT-4.1 model)
3. **GitHub authentication**: `arc auth github`
4. **Required Python packages**: `pip install colorama rich matplotlib networkx`
5. **Knowledge graph built**: `arc build --github`

## Demo Checklist

- [ ] Ensure OPENAI_API_KEY is set in the environment
- [ ] Verify knowledge graph exists and is up to date (`arc doctor`)
- [ ] Test all demo scripts one final time
- [ ] Have all terminal windows pre-arranged

## 1. Blast Radius Demo

- **Purpose**: Demonstrate Arc Memory's ability to predict the potential impact of changes to a core component.
- **Run the demo**:
  ```bash
  ./blast_radius_demo.py --file arc_memory/sdk/core.py
  ```
- **Key points to highlight**:
  - Identifies components that might be affected by changes with different severity levels
  - Analyzes direct, indirect, and potential impacts
  - Visualizes the impact network to show relationships between components
  - Helps developers understand the "blast radius" of their changes

**Duration**: ~2-3 minutes

## 2. Code Relationships Demo

- **Purpose**: Showcase Arc Memory's understanding of dependencies and relationships between code components.
- **Run the demo**:
  ```bash
  ./code_relationships_demo.py --file arc_memory/sdk/relationships.py
  ```
- **Key points to highlight**:
  - Identifies imports, dependencies, and other relationships
  - Shows both incoming and outgoing relationships
  - Visualizes the relationship network to show connections between components
  - Helps developers understand how code components are interconnected

**Duration**: ~2-3 minutes

## 3. Knowledge Graph Query Demo

- **Purpose**: Demonstrate Arc Memory's ability to answer natural language questions about the codebase.
- **Run the demo**:
  ```bash
  ./knowledge_query_demo.py --interactive
  ```
- **Key points to highlight**:
  - Answers questions about code changes, architecture, and dependencies
  - Provides evidence to support answers
  - Shows reasoning process for complex queries
  - Helps developers quickly find information about the codebase

**Duration**: ~3-4 minutes

## 4. Code Time Machine Demo

- **Purpose**: Explore how code evolved over time, understand key decisions, and visualize impact.
- **Run the demo**:
  ```bash
  cd code_time_machine
  ./run_demo.sh
  ```
- **Key points to highlight**:
  - Timeline visualization of code changes
  - Decision archaeology to understand why code exists
  - Impact prediction for safer changes
  - Improvement suggestions based on historical patterns

**Duration**: ~5 minutes

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
