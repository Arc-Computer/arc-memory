# Demo Day Checklist

## Before the Demo

- [ ] Ensure OPENAI_API_KEY is set in the environment
  ```bash
  export OPENAI_API_KEY=your-api-key
  ```

- [ ] Verify knowledge graph exists and is up to date
  ```bash
  ls -la ~/.arc/graph.db
  ```

- [ ] Test all demo scripts one final time
  ```bash
  ./demo_code_review.sh
  python pr_impact_analysis.py 71
  python blast_radius_viz.py arc_memory/auto_refresh/core.py
  ```

- [ ] Have all terminal windows pre-arranged
  - Terminal 1: For running the Code Review Assistant demo
  - Terminal 2: For running the PR Impact Analysis demo
  - Terminal 3: For running the Blast Radius Visualization demo

## During the Demo

### Demo 1: Code Review Assistant (5 minutes)

- [ ] Explain the purpose of the demo
  - "This demo shows how Arc Memory provides context for code review and understanding."

- [ ] Run the demo script
  ```bash
  ./demo_code_review.sh
  ```

- [ ] Highlight key points
  - Incremental updates (52% faster than before)
  - Decision trails showing why code exists
  - Impact analysis showing what might be affected
  - Relationships between components
  - Easy SDK integration

### Demo 2: PR Impact Analysis (3-4 minutes)

- [ ] Explain the purpose of the demo
  - "This demo shows how Arc Memory can predict the impact of changes before they're merged."

- [ ] Run the demo script
  ```bash
  python pr_impact_analysis.py 71
  ```

- [ ] Highlight key points
  - Automatic identification of affected components
  - Risk assessment based on impact analysis
  - Recommendations for review process
  - Integration potential with CI/CD pipelines

### Demo 3: Blast Radius Visualization (2-3 minutes)

- [ ] Explain the purpose of the demo
  - "This demo visually demonstrates the potential impact of changes to a file."

- [ ] Run the demo script
  ```bash
  python blast_radius_viz.py arc_memory/auto_refresh/core.py
  ```

- [ ] Highlight key points
  - Visual representation of affected components
  - Centrality of the changed file in the codebase
  - Strength of relationships between components
  - Potential for integration with PR review tools

## After the Demo

- [ ] Summarize the key benefits of Arc Memory
  - Reduced MTTR
  - Safer changes
  - Knowledge preservation
  - Onboarding acceleration

- [ ] Discuss next steps
  - Try Arc Memory on their own repositories
  - Explore the SDK
  - Join the community
  - Request a follow-up

- [ ] Answer questions

## Troubleshooting

If you encounter issues during the demo:

1. **Knowledge graph not found**: Run `arc build --github` to build the graph.
2. **OpenAI API key not set**: Set the environment variable with `export OPENAI_API_KEY=your-api-key`.
3. **Missing dependencies**: Install required packages with `pip install colorama matplotlib networkx`.
4. **GitHub authentication**: Run `arc auth github` to authenticate with GitHub.
