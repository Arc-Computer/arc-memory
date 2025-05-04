# Arc Memory PR Bot

The Arc Memory PR Bot is a GitHub App that enhances pull requests with contextual information from the knowledge graph. It provides insights about the original design decisions behind the code, predicts the impact of changes, and verifies that changes were properly tested.

## How It Works

When a pull request is opened or updated, the PR Bot:

1. Analyzes the changes in the pull request
2. Queries the Arc Memory knowledge graph to find relevant context
3. Generates a comment with three sections:
   - Original design decisions behind the code
   - Predicted impact of changes
   - Proof that changes were properly tested

## Example Output

Here's an example of the PR Bot's output:

```markdown
## Arc Memory PR Bot Analysis

### Original design decisions behind the code

This code implements the Linear OAuth 2.0 flow as decided in ADR-005 (Authentication Mechanisms). The decision to use OAuth instead of API keys was made to improve security and user experience, allowing users to authenticate without sharing their API keys.

Related decisions:
- ADR-005: Authentication Mechanisms (2023-04-15)
- Linear ticket ARC-42: "Implement Linear OAuth flow"

### Predicted impact of changes

Risk score: 35/100 (Low)

This change affects the authentication flow for Linear integration but does not impact existing functionality. The OAuth flow is isolated from the core knowledge graph building process.

Affected components:
- `arc_memory.auth.linear`
- `arc_memory.cli.auth`

### Proof that changes were properly tested

✅ Tests cover the main OAuth flow scenarios:
- Success path with valid credentials
- Error handling for invalid credentials
- Token refresh mechanism

Test coverage for modified files: 92%
```

## Installation

To install the Arc Memory PR Bot on your repository:

1. Go to [GitHub Apps page](#) (link to be added when the app is published)
2. Click "Install"
3. Select the repositories you want to enable the bot for

## Configuration

The PR Bot can be configured by adding a `.github/arc-pr-bot.yml` file to the root of your repository:

```yaml
# Enable or disable specific features
features:
  designDecisions: true
  impactAnalysis: true
  testVerification: true

# Configure the risk score thresholds
riskThresholds:
  low: 40
  medium: 70
  high: 90

# Customize the comment format
comment:
  includeRiskScore: true
  includeAffectedComponents: true
  includeTestCoverage: true
```

## How It Integrates with Arc Memory

The PR Bot uses the Arc Memory knowledge graph to find relevant context for the code changes. It connects to the same SQLite database that the Arc CLI builds, allowing it to access the full history of decisions, PRs, issues, and ADRs.

### Integration Architecture

The PR Bot integrates with the Arc Memory knowledge graph through the following components:

1. **Database Access Layer**: The PR Bot connects directly to the SQLite database created by the Arc CLI (`~/.arc/graph.db`), using a read-only connection to ensure data integrity.

2. **Entity Extraction**: When a PR is opened or updated, the bot:
   - Analyzes the changed files and their history
   - Queries the knowledge graph for related entities (ADRs, Linear tickets, PRs)
   - Extracts design decisions, impact information, and test verification data

3. **Multi-hop Reasoning**: The bot uses graph traversal algorithms to:
   - Connect seemingly unrelated entities through intermediate relationships
   - Discover the original design decisions that influenced the code
   - Identify potential impacts across the codebase

4. **LLM Integration**: The bot uses an LLM to:
   - Generate natural language explanations of the technical context
   - Analyze the potential impact of changes
   - Evaluate the completeness of testing

### Data Flow

1. GitHub webhook event → PR Bot
2. PR Bot extracts changed files → Knowledge Graph query
3. Knowledge Graph returns related entities → LLM analysis
4. LLM generates insights → PR comment

### Integration Points

The PR Bot integrates with several Arc Memory components:

- **Git Ingestor**: Uses commit history data ingested by the Git Ingestor
- **GitHub Ingestor**: Uses PR and issue data ingested by the GitHub Ingestor
- **Linear Ingestor**: Uses ticket data ingested by the Linear Ingestor
- **ADR Scanner**: Uses architectural decision records parsed by the ADR Scanner

This integration allows the PR Bot to provide a comprehensive view of the context behind code changes, connecting technical decisions to business requirements and architectural principles.

## Development

For information on developing or contributing to the PR Bot, see the [PR Bot README](../arc-memory-pr-bot/README.md).

## Troubleshooting

If the PR Bot is not working as expected:

1. Check that the bot is installed on your repository
2. Ensure your knowledge graph is built and up-to-date (`arc build`)
3. Verify that the PR Bot has access to your knowledge graph
4. Check the PR Bot logs for any errors

For more help, open an issue on the [Arc Memory repository](https://github.com/Arc-Computer/arc-memory/issues).
