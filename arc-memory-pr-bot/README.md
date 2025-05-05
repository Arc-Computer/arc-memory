# Arc Memory PR Bot

A GitHub PR Bot for Arc Memory that enhances pull requests with contextual information from the knowledge graph, showing original design decisions, predicted impact, and test verification.

## Features

- Automatically analyzes pull requests when they are opened or updated
- Provides context about the original design decisions behind the code
- Predicts the impact of changes
- Verifies that changes were properly tested
- Uses LLMs to generate intelligent insights about PRs
- Visualizes relevant code diffs with contextual explanations

## How It Works

When a pull request is opened or updated, the PR Bot:

1. Analyzes the changes in the pull request
2. Extracts context information using the PR Context Generator:
   - Identifies related Linear tickets from branch names and PR descriptions
   - Finds relevant ADRs for the changed files
   - Retrieves commit history and related PRs
3. Queries the Arc Memory knowledge graph to find additional context
4. Processes the PR context using LLMs to generate intelligent insights
5. Extracts relevant code diffs for visualization
6. Generates a comment with three sections:
   - Original design decisions behind the code
   - Predicted impact of changes
   - Proof that changes were properly tested
7. Formats the insights and code diffs as a GitHub comment

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

## Setup

### Prerequisites

- Node.js 16+
- npm or yarn
- A GitHub account with permissions to create GitHub Apps

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Arc-Computer/arc-memory.git
   cd arc-memory/arc-memory-pr-bot
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file with the following variables:
   ```
   # The ID of your GitHub App
   APP_ID=

   # The private key of your GitHub App (multiline, base64 encoded)
   PRIVATE_KEY=

   # The webhook secret of your GitHub App
   WEBHOOK_SECRET=

   # The Smee.io URL for local development
   WEBHOOK_PROXY_URL=

   # LLM Configuration
   # Provider: openai or anthropic
   LLM_PROVIDER=openai

   # OpenAI Configuration
   OPENAI_API_KEY=
   OPENAI_MODEL=gpt-4o
   OPENAI_ORGANIZATION=

   # LLM Parameters
   LLM_TEMPERATURE=0.7
   LLM_MAX_TOKENS=4000
   LLM_CACHE_TTL=3600
   ```

4. Start the bot:
   ```bash
   npm run dev
   ```

### Creating a GitHub App

1. Go to your GitHub account settings -> Developer settings -> GitHub Apps -> New GitHub App
2. Fill in the required information:
   - GitHub App name: Arc Memory PR Bot
   - Homepage URL: https://github.com/Arc-Computer/arc-memory
   - Webhook URL: Use your Smee.io URL for development or your production URL
   - Webhook secret: Generate a random string
3. Set the following permissions:
   - Repository contents: Read
   - Pull requests: Read & Write
   - Metadata: Read
4. Subscribe to the following events:
   - Pull request
   - Pull request review
   - Push
5. Create the app and note the App ID
6. Generate a private key and download it
7. Update your `.env` file with the App ID, private key, and webhook secret

### Using Smee.io for Local Development

1. Go to [smee.io](https://smee.io/) and click "Start a new channel"
2. Copy the URL
3. Add it to your `.env` file as `WEBHOOK_PROXY_URL`
4. Update your GitHub App's webhook URL to the Smee.io URL
5. Start the Smee client:
   ```bash
   npx smee -u <SMEE_URL> -p 3000
   ```
6. Start the bot:
   ```bash
   npm run dev
   ```

### Analyzing Closed PRs

You can analyze closed PRs to test the PR Context Processor and refine prompts:

1. Create a `.env.analyze` file based on the `.env.analyze-example` template:
   ```bash
   cp .env.analyze-example .env.analyze
   ```

2. Add your GitHub token and OpenAI API key to the `.env.analyze` file

3. Build the project:
   ```bash
   npm run build
   ```

4. List recent closed PRs:
   ```bash
   npm run analyze-prs
   ```

5. Analyze a specific PR:
   ```bash
   npm run analyze-prs -- <pr-number>
   ```

The script will generate insights for the PR and save them to the `output` directory.

## Configuration

The PR Bot can be configured by adding a `.github/arc-pr-bot.yml` file to the root of your repository:

```yaml
# Enable or disable specific features
features:
  designDecisions: true
  impactAnalysis: true
  testVerification: true
  useLLM: true

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
  includeCodeSnippets: true

# LLM configuration
llm:
  provider: openai
  model: gpt-4o
  temperature: 0.7
  maxTokens: 4000
  cacheTTL: 3600
```

## Architecture

The Arc Memory PR Bot consists of several key components:

### GraphService

The GraphService provides an interface to the Arc Memory knowledge graph (SQLite database). It handles:

- Connecting to the database
- Querying for nodes and edges
- Finding related entities (Linear tickets, ADRs, commits, PRs)
- Caching results for performance

### ContextGenerator

The ContextGenerator extracts and enriches context information for pull requests:

- Extracts branch name and PR title/body
- Identifies related Linear tickets through branch naming conventions and mentions
- Retrieves relevant ADRs using the GraphService
- Formats the information for display in PR comments
- Implements fallback mechanisms when primary data sources are unavailable

### PR Context Processor

The PR Context Processor uses LLMs to generate intelligent insights about pull requests:

- Processes PR context data for LLM consumption
- Generates structured insights about design decisions, impact analysis, and test verification
- Handles fallbacks when LLM processing fails

### Comment Formatter

The Comment Formatter takes the LLM-generated insights and formats them into user-friendly PR comments:

- Customizable based on configuration
- Supports different sections (design decisions, impact analysis, test verification)
- Formats code diffs for visualization
- Handles fallbacks when certain information is missing

## Security Considerations

When deploying the Arc Memory PR Bot, it's important to handle GitHub App credentials securely:

### Credential Storage

- **Never commit credentials to version control**
- Store the `PRIVATE_KEY`, `APP_ID`, `WEBHOOK_SECRET`, and `OPENAI_API_KEY` as environment variables or in a secure secrets manager
- For local development, use a `.env` file that is listed in `.gitignore`
- For production, use environment variables or a secrets manager like AWS Secrets Manager, HashiCorp Vault, or GitHub Secrets

### Private Key Handling

- Keep the GitHub App's private key secure and rotate it periodically
- Consider encoding the private key as base64 when storing it in environment variables
- Limit access to the private key to only those who need it

### Webhook Secret

- Use a strong, randomly generated string for the webhook secret
- This secret is used to verify that webhook requests come from GitHub
- Rotate the webhook secret periodically

### Permissions

- Follow the principle of least privilege
- Only request the permissions that the bot actually needs
- Regularly review and audit the bot's permissions

## Docker Deployment

```sh
# 1. Build container
docker build -t arc-memory-pr-bot .

# 2. Start container
docker run -e APP_ID=<app-id> -e PRIVATE_KEY=<pem-value> -e WEBHOOK_SECRET=<webhook-secret> -e OPENAI_API_KEY=<openai-key> arc-memory-pr-bot
```

### Secure Docker Deployment

For a more secure Docker deployment, consider:

- Using Docker secrets or environment files instead of passing credentials directly in the command line
- Setting up a non-root user in the container
- Using a multi-stage build to minimize the attack surface
- Scanning the container for vulnerabilities before deployment

## Contributing

If you have suggestions for how the Arc Memory PR Bot could be improved, or want to report a bug, open an issue! We'd love all and any contributions.

For more, check out the [Contributing Guide](CONTRIBUTING.md).

## License

[MIT](LICENSE) © 2025 Arc Computer
