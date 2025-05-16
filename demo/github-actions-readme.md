# Arc Memory GitHub Actions Integration

This demo shows how to integrate Arc Memory with GitHub Actions to automatically update your knowledge graph on merges to main and analyze the impact of changes.

## Setup Instructions

1. Copy the `github-actions-workflow.yml` file to your repository's `.github/workflows/` directory:

```bash
mkdir -p .github/workflows/
cp demo/github-actions-workflow.yml .github/workflows/arc-memory.yml
```

2. Add your OpenAI API key as a GitHub secret:
   - Go to your repository on GitHub
   - Navigate to Settings > Secrets and variables > Actions
   - Click "New repository secret"
   - Name: `OPENAI_API_KEY`
   - Value: Your OpenAI API key

3. Commit and push the workflow file:

```bash
git add .github/workflows/arc-memory.yml
git commit -m "Add Arc Memory GitHub Actions workflow"
git push
```

## What This Workflow Does

1. **Triggers**: The workflow runs on:
   - Pushes to the main/master branch
   - When a PR is merged into main/master

2. **Actions**:
   - Checks out the repository with full history
   - Sets up Python
   - Installs Arc Memory
   - Uses GitHub Actions caching to store the knowledge graph between runs
   - Updates the knowledge graph (refresh if exists, build if new)
   - For merged PRs, analyzes the impact of changes
   - Uploads the knowledge graph and impact report as artifacts

3. **Environment Variables**:
   - `GITHUB_TOKEN`: Automatically provided by GitHub Actions
   - `OPENAI_API_KEY`: Your OpenAI API key (added as a secret)

## Customizing the Workflow

- **LLM Model**: The workflow uses `o4-mini` by default. You can change this by modifying the `--llm-model` parameter.
- **Build Parameters**: Add additional parameters to the `arc build` command as needed.
- **Caching Strategy**: Adjust the cache key to control when the cache is invalidated.
- **Impact Analysis**: Customize the impact analysis report format and content.

## Viewing Results

After the workflow runs:

1. Go to the Actions tab in your repository
2. Click on the latest workflow run
3. Under "Artifacts", you'll find:
   - `arc-memory-graph`: The updated knowledge graph
   - `impact-report`: Analysis of the changes (for merged PRs)

## Next Steps

- Add a step to comment on PRs with the impact analysis
- Integrate with other CI/CD tools
- Add custom notifications for high-impact changes
