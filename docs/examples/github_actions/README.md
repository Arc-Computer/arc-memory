# Arc Memory GitHub Actions Integration

This directory contains examples and documentation for integrating Arc Memory with GitHub Actions. These workflows automate PR analysis, provide insights about code changes, and help improve code review quality.

## Available Workflows

### 1. PR Review Workflow

The [arc_memory_pr_review.yml](./arc_memory_pr_review.yml) workflow analyzes pull requests and posts insights as PR comments. It:

- Builds a knowledge graph from your repository
- Analyzes the changes in the PR
- Identifies potential impacts and dependencies
- Posts a detailed analysis as a PR comment

### 2. Scheduled Knowledge Graph Updates

The [arc_memory_update.yml](./arc_memory_update.yml) workflow keeps your knowledge graph up-to-date with scheduled builds. This is useful for large repositories where building the graph for each PR might be time-consuming.

## Setting Up GitHub Actions

### Basic Setup

1. Create a `.github/workflows` directory in your repository if it doesn't exist
2. Copy the desired workflow file (e.g., `arc_memory_pr_review.yml`) to that directory
3. Commit and push the changes

GitHub will automatically detect and run the workflow based on the triggers defined in the file.

### Required Permissions

The workflows require these permissions:

- `contents: read` - To read repository contents
- `pull-requests: write` - To post comments on PRs

These are defined in the workflow files and don't require additional setup if you're using the default `GITHUB_TOKEN`.

### Secrets Configuration

Some workflows may require additional secrets:

- `OPENAI_API_KEY` - If using OpenAI for enhanced analysis
- `LINEAR_API_KEY` - If integrating with Linear

Add these secrets in your repository settings under Settings > Secrets and variables > Actions.

## Customizing the Workflows

### Analysis Depth

You can adjust the analysis depth based on your repository size and complexity:

```yaml
- name: Analyze PR Impact
  run: |
    arc export --pr-sha $PR_SHA --output-path pr_analysis.json --max-hops 2
    arc ci analyze --pr $PR_NUMBER --analysis-depth standard
```

Options for `--analysis-depth`:
- `basic` - Fast, lightweight analysis
- `standard` - Balanced depth and performance (default)
- `deep` - Thorough analysis (slower)

### LLM Enhancement

For higher quality analysis, you can use different LLM providers:

#### OpenAI (Recommended for Best Quality)

```yaml
- name: Build Knowledge Graph with OpenAI
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    arc build --github --llm-provider openai --llm-model gpt-4o --llm-enhancement
```

#### Anthropic Claude

```yaml
- name: Build Knowledge Graph with Anthropic
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    arc build --github --llm-provider anthropic --llm-model claude-3-opus-20240229 --llm-enhancement
```

#### Local Models with Ollama

```yaml
- name: Set up Ollama
  run: |
    curl -fsSL https://ollama.com/install.sh | sh
    ollama serve &
    ollama pull gemma3:27b-it-qat

- name: Build Knowledge Graph with Ollama
  run: |
    arc build --github --llm-provider ollama --llm-model gemma3:27b-it-qat --llm-enhancement
```

### Comment Customization

You can customize the PR comment format:

```yaml
- name: Post Analysis as PR Comment
  uses: actions/github-script@v6
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    script: |
      const fs = require('fs');
      const analysis = fs.readFileSync('pr_analysis.md', 'utf8');
      
      const commentBody = `## 🧠 Arc Memory Analysis
      
      ${analysis}
      
      ---
      *Powered by [Arc Memory](https://github.com/Arc-Computer/arc-memory)*`;
      
      // Post comment logic...
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Workflow fails with "No such file or directory: '.arc'"** | Make sure the checkout step has `fetch-depth: 0` to get the full history. |
| **"Failed to build knowledge graph"** | Check the GitHub token permissions and ensure it has read access to the repository. |
| **"LLM enhancement failed"** | Verify that the API key is correctly set in the repository secrets. |
| **Build process times out** | Use `--incremental` and consider setting up a scheduled workflow for full builds. |

### Debugging

For more detailed logs, add the `--verbose` flag to Arc Memory commands:

```yaml
- name: Build Knowledge Graph
  run: |
    arc build --github --incremental --verbose
```

You can also add debug steps to inspect the environment:

```yaml
- name: Debug Info
  run: |
    arc doctor
    ls -la ~/.arc
    echo "PR SHA: $PR_SHA"
```

## Examples

### Minimal PR Review Workflow

```yaml
name: Arc Memory PR Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  arc-memory-analysis:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - run: pip install arc-memory[github]
      
      - run: arc build --github --incremental
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - run: |
          arc export --pr-sha ${{ github.event.pull_request.head.sha }} --output-path pr_analysis.json
          arc ci analyze --pr ${{ github.event.pull_request.number }} --output-format markdown > pr_analysis.md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - uses: actions/github-script@v6
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          script: |
            const fs = require('fs');
            const analysis = fs.readFileSync('pr_analysis.md', 'utf8');
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `## Arc Memory Analysis\n\n${analysis}`
            });
```

## Next Steps

- [CI Integration Strategy](../../roadmap/ci_integration_strategy.md) - Learn more about Arc Memory's CI integration strategy
- [PR Comment Integration](../../roadmap/pr_comment_integration.md) - Detailed plan for PR comment integration
- [Graph Density Enhancement](../../roadmap/graph_density_enhancement.md) - Improving graph quality for better insights
