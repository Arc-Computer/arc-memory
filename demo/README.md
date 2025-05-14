# Arc Memory Demo Guide

This guide contains instructions for running the Arc Memory demos.

## Prerequisites

Before running the demos, make sure you have:

1. **Arc Memory installed**: `pip install arc-memory[all]`
2. **OpenAI API key set**: `export OPENAI_API_KEY=your-api-key` (required for GPT-4.1 model)
3. **GitHub authentication**: `arc auth github`
4. **Required Python packages**: `pip install colorama matplotlib networkx`

## Demo Checklist

- [ ] Ensure OPENAI_API_KEY is set in the environment
- [ ] Verify knowledge graph exists and is up to date
- [ ] Test all demo scripts one final time
- [ ] Have all terminal windows pre-arranged

## 1. LLM-Powered Code Review Assistant Demo

- **Purpose**: Showcase how Arc Memory provides intelligent context for code review and understanding.
- **Run the demo**:
  ```bash
  ./demo_code_review.sh
  ```
- **Key points to highlight**:
  - LLM-powered analysis of code context and history
  - Detailed insights into code purpose and dependencies
  - Specific recommendations based on codebase patterns
  - Easy SDK integration for custom tools

**Duration**: ~5 minutes

## 2. Enhanced Blast Radius Visualization Demo

- **Purpose**: Visually demonstrate the potential impact of changes to a file with comprehensive SDK integration.
- **Run the demo**:
  ```bash
  ./demo_enhanced_blast_radius.sh
  ```
- **Key points to highlight**:
  - Full utilization of Arc Memory SDK methods (get_entity_details, get_decision_trail, get_related_entities)
  - Rich visualization showing different relationship types
  - Comprehensive LLM analysis with historical context
  - Actionable insights for safer code changes based on real graph data

**Duration**: ~3-4 minutes

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
