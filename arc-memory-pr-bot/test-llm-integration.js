/**
 * Test script for the LLM integration
 *
 * This script tests the LLM integration by:
 * 1. Initializing the OpenAI client
 * 2. Creating a mock PR context
 * 3. Calling the PR Context Processor to generate insights
 * 4. Logging the results
 *
 * Usage:
 * 1. Set the OPENAI_API_KEY environment variable
 * 2. Run the script with Node.js: node test-llm-integration.js
 */

import { LLMClientFactory, LLMProvider, PRContextProcessor } from './lib/llm/index.js';
import { NodeType } from './lib/graph-service.js';

// Simple logger for testing
const logger = {
  info: (...args) => console.log('[INFO]', ...args),
  warn: (...args) => console.warn('[WARN]', ...args),
  error: (...args) => console.error('[ERROR]', ...args),
  debug: (...args) => console.debug('[DEBUG]', ...args),
};

// Create a mock PR context
const mockPRContext = {
  prNumber: 123,
  prTitle: 'Add Linear OAuth integration',
  prBody: `This PR implements the Linear OAuth flow as described in the Linear API documentation.

Key changes:
- Add LinearOAuthClient class for handling the OAuth flow
- Update LinearIngestor to support OAuth authentication
- Add CLI commands for Linear OAuth login
- Add tests for the OAuth flow

Fixes ARC-42`,
  prAuthor: 'jbarnes850',
  baseRef: 'main',
  headRef: 'feature/linear-oauth',
  repository: 'arc-memory',
  owner: 'Arc-Computer',
  changedFiles: [
    {
      filename: 'arc_memory/auth/linear.py',
      status: 'added',
      additions: 120,
      deletions: 0,
      changes: 120,
      patch: '@@ -0,0 +1,120 @@\n+"""Linear OAuth authentication.\n+\n+This module implements the Linear OAuth flow.\n+"""\n+\n+import json\n+import os\n+import time\n+from typing import Dict, Optional, Tuple\n+\n+import requests\n+\n+from arc_memory.auth.base import BaseAuthClient\n+from arc_memory.config import get_config_dir\n+\n+# Linear OAuth endpoints\n+LINEAR_AUTH_URL = "https://linear.app/oauth/authorize"\n+LINEAR_TOKEN_URL = "https://api.linear.app/oauth/token"\n+LINEAR_API_URL = "https://api.linear.app/graphql"\n+\n+class LinearOAuthClient(BaseAuthClient):\n+    """Linear OAuth client.\n+\n+    This class handles the Linear OAuth flow, including:\n+    - Generating the authorization URL\n+    - Exchanging the authorization code for an access token\n+    - Refreshing the access token\n+    - Storing and retrieving tokens\n+    """\n+\n+    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):\n+        """Initialize the Linear OAuth client.\n+\n+        Args:\n+            client_id: The Linear OAuth client ID\n+            client_secret: The Linear OAuth client secret\n+            redirect_uri: The redirect URI for the OAuth flow\n+        """\n+        self.client_id = client_id\n+        self.client_secret = client_secret\n+        self.redirect_uri = redirect_uri\n+        self.token_file = os.path.join(get_config_dir(), "linear_token.json")\n+\n+    def get_authorization_url(self, state: str) -> str:\n+        """Get the Linear authorization URL.\n+\n+        Args:\n+            state: A random string to prevent CSRF attacks\n+\n+        Returns:\n+            The authorization URL\n+        """\n+        params = {\n+            "client_id": self.client_id,\n+            "redirect_uri": self.redirect_uri,\n+            "response_type": "code",\n+            "state": state,\n+            "scope": "read,write",\n+        }\n+        return f"{LINEAR_AUTH_URL}?{urlencode(params)}"\n+\n+    def exchange_code_for_token(self, code: str) -> Dict[str, str]:\n+        """Exchange the authorization code for an access token.\n+\n+        Args:\n+            code: The authorization code from the OAuth callback\n+\n+        Returns:\n+            The token response, including access_token, refresh_token, etc.\n+\n+        Raises:\n+            Exception: If the token exchange fails\n+        """\n+        data = {\n+            "client_id": self.client_id,\n+            "client_secret": self.client_secret,\n+            "redirect_uri": self.redirect_uri,\n+            "code": code,\n+            "grant_type": "authorization_code",\n+        }\n+        response = requests.post(LINEAR_TOKEN_URL, data=data)\n+        if response.status_code != 200:\n+            raise Exception(f"Failed to exchange code for token: {response.text}")\n+\n+        token_data = response.json()\n+        self._save_token(token_data)\n+        return token_data\n+'
    },
    {
      filename: 'arc_memory/cli/auth.py',
      status: 'modified',
      additions: 45,
      deletions: 5,
      changes: 50,
      patch: '@@ -10,6 +10,7 @@ import click\n import requests\n \n from arc_memory.auth.github import GitHubAuthClient\n+from arc_memory.auth.linear import LinearOAuthClient\n from arc_memory.config import get_config\n \n \n@@ -48,3 +49,42 @@ def github_login():\n     click.echo(f"Successfully authenticated with GitHub as {user_login}")\n     click.echo("Your credentials have been saved for future use.")\n     return True\n+\n+\n+@click.command()\n+@click.option("--port", default=3000, help="Port to use for the OAuth callback server")\n+def linear_login(port):\n+    """Authenticate with Linear using OAuth.\n+\n+    This command starts a local server to handle the OAuth callback,\n+    then opens a browser to the Linear authorization page.\n+    """\n+    config = get_config()\n+    client_id = config.get("linear", {}).get("client_id")\n+    client_secret = config.get("linear", {}).get("client_secret")\n+\n+    if not client_id or not client_secret:\n+        click.echo("Linear OAuth client ID and secret are required.")\n+        click.echo("Please set them in your config file or environment variables.")\n+        return False\n+\n+    # Create the Linear OAuth client\n+    redirect_uri = f"http://localhost:{port}/auth/linear/callback"\n+    linear_client = LinearOAuthClient(client_id, client_secret, redirect_uri)\n+\n+    # Generate a random state to prevent CSRF attacks\n+    state = secrets.token_urlsafe(32)\n+\n+    # Get the authorization URL\n+    auth_url = linear_client.get_authorization_url(state)\n+\n+    # Start the OAuth flow\n+    click.echo("Starting Linear OAuth flow...")\n+    click.echo(f"Opening browser to {auth_url}")\n+    click.launch(auth_url)\n+\n+    # Start a local server to handle the callback\n+    # ... (code to start server and handle callback) ...\n+\n+    click.echo("Successfully authenticated with Linear")\n+    click.echo("Your credentials have been saved for future use.")\n+    return True'
    },
    {
      filename: 'tests/auth/test_linear_auth.py',
      status: 'added',
      additions: 85,
      deletions: 0,
      changes: 85,
      patch: '@@ -0,0 +1,85 @@\n+"""Tests for Linear OAuth authentication.\n+\n+This module tests the Linear OAuth flow.\n+"""\n+\n+import json\n+import os\n+from unittest import mock\n+\n+import pytest\n+import responses\n+\n+from arc_memory.auth.linear import (\n+    LINEAR_AUTH_URL,\n+    LINEAR_TOKEN_URL,\n+    LinearOAuthClient,\n+)\n+\n+\n+@pytest.fixture\n+def linear_client():\n+    """Create a Linear OAuth client for testing."""\n+    return LinearOAuthClient(\n+        client_id="test_client_id",\n+        client_secret="test_client_secret",\n+        redirect_uri="http://localhost:3000/auth/linear/callback",\n+    )\n+\n+\n+def test_get_authorization_url(linear_client):\n+    """Test generating the authorization URL."""\n+    url = linear_client.get_authorization_url("test_state")\n+    assert url.startswith(LINEAR_AUTH_URL)\n+    assert "client_id=test_client_id" in url\n+    assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Flinear%2Fcallback" in url\n+    assert "state=test_state" in url\n+    assert "scope=read%2Cwrite" in url\n+\n+\n+@responses.activate\n+def test_exchange_code_for_token(linear_client, tmp_path):\n+    """Test exchanging the authorization code for an access token."""\n+    # Mock the token file path\n+    with mock.patch.object(linear_client, "token_file", str(tmp_path / "linear_token.json")):\n+        # Mock the token response\n+        responses.add(\n+            responses.POST,\n+            LINEAR_TOKEN_URL,\n+            json={\n+                "access_token": "test_access_token",\n+                "refresh_token": "test_refresh_token",\n+                "expires_in": 3600,\n+                "token_type": "Bearer",\n+            },\n+            status=200,\n+        )\n+\n+        # Exchange the code for a token\n+        token_data = linear_client.exchange_code_for_token("test_code")\n+\n+        # Check the token data\n+        assert token_data["access_token"] == "test_access_token"\n+        assert token_data["refresh_token"] == "test_refresh_token"\n+        assert token_data["expires_in"] == 3600\n+        assert token_data["token_type"] == "Bearer"\n+\n+        # Check that the token was saved\n+        assert os.path.exists(linear_client.token_file)\n+        with open(linear_client.token_file, "r") as f:\n+            saved_token = json.load(f)\n+            assert saved_token["access_token"] == "test_access_token"\n+            assert saved_token["refresh_token"] == "test_refresh_token"'
    }
  ],
  relatedEntities: {
    linearTickets: [
      {
        id: 'issue:ARC-42',
        type: NodeType.ISSUE,
        title: 'Implement Linear OAuth flow',
        body: 'Implement the Linear OAuth flow as described in the Linear API documentation.',
        extra: {
          number: 42,
          state: 'completed',
          url: 'https://linear.app/arc-computer/issue/ARC-42/implement-linear-oauth-flow',
        },
        number: 42,
        state: 'completed',
        url: 'https://linear.app/arc-computer/issue/ARC-42/implement-linear-oauth-flow',
      }
    ],
    adrs: [
      {
        id: 'adr:ADR-005',
        type: NodeType.ADR,
        title: 'Authentication Mechanisms',
        body: 'This ADR describes the authentication mechanisms used in the Arc Memory project.',
        extra: {
          status: 'accepted',
          path: 'docs/adr/adr-005-authentication-mechanisms.md',
          decision_makers: ['jbarnes850', 'alice'],
          timestamp: '2023-04-15T00:00:00Z',
        },
        status: 'accepted',
        path: 'docs/adr/adr-005-authentication-mechanisms.md',
        decision_makers: ['jbarnes850', 'alice'],
      }
    ],
    commits: [
      {
        id: 'commit:abc123',
        type: NodeType.COMMIT,
        title: 'Add LinearOAuthClient class',
        body: 'This commit adds the LinearOAuthClient class for handling the OAuth flow.',
        extra: {
          author: 'jbarnes850',
          sha: 'abc123def456',
          timestamp: '2023-05-01T00:00:00Z',
          files: ['arc_memory/auth/linear.py'],
        },
        author: 'jbarnes850',
        sha: 'abc123def456',
        files: ['arc_memory/auth/linear.py'],
      },
      {
        id: 'commit:def456',
        type: NodeType.COMMIT,
        title: 'Update CLI commands for Linear OAuth',
        body: 'This commit adds CLI commands for Linear OAuth login.',
        extra: {
          author: 'jbarnes850',
          sha: 'def456abc789',
          timestamp: '2023-05-02T00:00:00Z',
          files: ['arc_memory/cli/auth.py'],
        },
        author: 'jbarnes850',
        sha: 'def456abc789',
        files: ['arc_memory/cli/auth.py'],
      },
      {
        id: 'commit:ghi789',
        type: NodeType.COMMIT,
        title: 'Add tests for Linear OAuth',
        body: 'This commit adds tests for the Linear OAuth flow.',
        extra: {
          author: 'jbarnes850',
          sha: 'ghi789jkl012',
          timestamp: '2023-05-03T00:00:00Z',
          files: ['tests/auth/test_linear_auth.py'],
        },
        author: 'jbarnes850',
        sha: 'ghi789jkl012',
        files: ['tests/auth/test_linear_auth.py'],
      }
    ],
    relatedPRs: []
  }
};

// Main function to test the LLM integration
async function testLLMIntegration() {
  try {
    // Check if the API key is set
    if (!process.env.OPENAI_API_KEY) {
      console.error('Error: OPENAI_API_KEY environment variable is not set');
      console.error('Please set it before running this script');
      process.exit(1);
    }

    console.log('Creating LLM client...');
    const llmClient = LLMClientFactory.createClientFromEnv(logger);

    console.log('Creating PR Context Processor...');
    const prContextProcessor = new PRContextProcessor(llmClient, logger);

    console.log('Generating insights...');
    console.log('This may take a minute or two...');

    // Generate insights for the mock PR context
    const insights = await prContextProcessor.generateInsights(mockPRContext);

    // Log the results
    console.log('\n=== Design Decisions Insight ===');
    console.log('Summary:', insights.designDecisions.summary);
    console.log('Related ADRs:', insights.designDecisions.relatedADRs);
    console.log('Related Tickets:', insights.designDecisions.relatedTickets);
    console.log('Design Principles:', insights.designDecisions.designPrinciples);
    console.log('Explanation:', insights.designDecisions.explanation);

    console.log('\n=== Impact Analysis Insight ===');
    console.log('Summary:', insights.impactAnalysis.summary);
    console.log('Risk Score:', insights.impactAnalysis.riskScore);
    console.log('Affected Components:', insights.impactAnalysis.affectedComponents);
    console.log('Potential Issues:', insights.impactAnalysis.potentialIssues);
    console.log('Recommendations:', insights.impactAnalysis.recommendations);

    console.log('\n=== Test Verification Insight ===');
    console.log('Summary:', insights.testVerification.summary);
    console.log('Test Coverage:', insights.testVerification.testCoverage);
    console.log('Test Gaps:', insights.testVerification.testGaps);
    console.log('Recommendations:', insights.testVerification.recommendations);

    console.log('\nLLM integration test completed successfully!');
  } catch (error) {
    console.error('Error testing LLM integration:', error);
    process.exit(1);
  }
}

// Run the test
testLLMIntegration();
