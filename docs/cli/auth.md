# Authentication Commands

The Arc Memory CLI provides commands for authenticating with GitHub and Linear, which is required for accessing data such as pull requests, issues, and Linear tickets.

**Related Documentation:**
- [Build Commands](./build.md) - After authenticating, build your knowledge graph
- [Doctor Commands](./doctor.md) - Verify your authentication status
- [Building Graphs Examples](../examples/building-graphs.md) - Examples of using authentication with builds

## Overview

Authentication is handled through the `arc auth` command group. Arc Memory uses GitHub's device flow for GitHub authentication and OAuth 2.0 for Linear authentication, which are secure ways to authenticate without having to enter your credentials directly.

## Commands

### `arc auth gh`

Authenticate with GitHub using device flow.

```bash
arc auth gh [OPTIONS]
```

This command initiates the GitHub device flow authentication process. It will display a code and a URL. You need to visit the URL, enter the code, and authorize the Arc Memory application to access your GitHub account.

#### Options

- `--client-id TEXT`: GitHub OAuth client ID. If not provided, uses the default Arc Memory app from the Arc-Computer organization.
- `--timeout INTEGER`: Timeout in seconds for the device flow (default: 300).
- `--debug`: Enable debug logging.

#### Example

```bash
# Authenticate with GitHub using the default Arc Memory app
arc auth gh

# Authenticate with a custom GitHub OAuth app
arc auth gh --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET

# Authenticate with a longer timeout
arc auth gh --timeout 600
```

### `arc auth gh-app`

Authenticate with a GitHub App.

```bash
arc auth gh-app [OPTIONS]
```

This command configures authentication for a GitHub App. GitHub Apps provide more granular permissions and can be installed on organizations.

#### Options

- `--app-id TEXT`: GitHub App ID.
- `--private-key TEXT`: Path to the GitHub App private key file.
- `--client-id TEXT`: GitHub OAuth client ID for the GitHub App.
- `--client-secret TEXT`: GitHub OAuth client secret for the GitHub App.
- `--debug`: Enable debug logging.

#### Example

```bash
# Authenticate with a GitHub App
arc auth gh-app --app-id 12345 --private-key path/to/private-key.pem
```

### `arc auth linear`

Authenticate with Linear using OAuth 2.0.

```bash
arc auth linear [OPTIONS]
```

This command initiates the Linear OAuth 2.0 authentication flow. It will start a local server to receive the callback, open a browser window for you to authenticate with Linear, and then exchange the authorization code for an access token.

#### Options

- `--client-id TEXT`: Linear OAuth client ID. If not provided, uses the default Arc Memory app from the Arc-Computer organization.
- `--client-secret TEXT`: Linear OAuth client secret. If not provided, uses the default Arc Memory app from the Arc-Computer organization.
- `--redirect-uri TEXT`: Redirect URI for the OAuth flow. Default is `http://localhost:3000/auth/linear/callback`.
- `--timeout INTEGER`: Timeout in seconds for the OAuth flow (default: 300).
- `--debug`: Enable debug logging.

#### Example

```bash
# Authenticate with Linear using the default Arc Memory app
arc auth linear

# Authenticate with a custom Linear OAuth app
arc auth linear --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET

# Authenticate with a longer timeout
arc auth linear --timeout 600
```

## GitHub Device Flow

Arc Memory uses GitHub's Device Flow for authentication, which is the recommended approach for CLI applications:

1. **How It Works**:
   - When you run `arc auth gh`, the CLI generates a user code and verification URL
   - You visit the URL in your browser and enter the code
   - You authenticate directly with GitHub in your browser
   - GitHub then authorizes the application and provides a token to the CLI

2. **Security Benefits**:
   - You never enter your GitHub credentials in the CLI
   - The CLI only needs a Client ID (public information) to initiate the flow
   - Your browser handles the secure authentication with GitHub
   - The token is generated directly between GitHub and the CLI

## Linear OAuth 2.0 Flow

Arc Memory uses Linear's OAuth 2.0 flow for authentication, which is the recommended approach for applications:

1. **How It Works**:
   - When you run `arc auth linear`, the CLI starts a local server to receive the callback
   - A browser window opens for you to authenticate with Linear
   - After authentication, Linear redirects back to the local server with an authorization code
   - The CLI exchanges the code for an access token
   - The token is stored securely in your system keyring

2. **Security Benefits**:
   - You never enter your Linear credentials in the CLI
   - The CLI only needs a Client ID and Client Secret to initiate the flow
   - Your browser handles the secure authentication with Linear
   - The token is generated directly between Linear and the CLI
   - The token is stored securely in your system keyring

## Authentication Storage

Arc Memory stores authentication tokens securely:

1. **System Keyring**: By default, tokens are stored in your system's secure keyring (Keychain on macOS, Credential Manager on Windows, etc.).
2. **Environment Variables**: You can also provide tokens via environment variables (`GITHUB_TOKEN` for GitHub, `LINEAR_API_KEY` for Linear API keys).

If a token is found in environment variables, Arc Memory will ask if you want to store it in the system keyring for future use.

## Checking Authentication Status

You can verify your authentication status by running:

```bash
arc doctor
```

This will show if you have a valid GitHub token configured.

## Troubleshooting

### GitHub Authentication Failures

If you encounter GitHub authentication issues:

1. **Network Issues**:
   - Check your internet connection
   - Ensure you can access github.com in your browser
   - If behind a corporate firewall, check if GitHub API access is allowed
   - Try again with `arc auth gh --debug` to see detailed error messages

2. **Token Expiration**:
   - GitHub tokens can expire or be revoked
   - Simply run `arc auth gh` again to get a new token
   - You'll see a new device code and URL to visit

3. **Permission Issues**:
   - Ensure the token has the necessary permissions (repo, read:org)
   - If you're using a custom client ID, verify it has the correct scopes
   - You may need to revoke the existing token in your GitHub settings and re-authenticate

4. **Rate Limiting**:
   - GitHub API has rate limits
   - If you hit them, wait or use a token with higher limits
   - Enterprise accounts typically have higher rate limits

5. **Default Credentials**:
   - Arc Memory uses a default GitHub OAuth Client ID from the Arc-Computer organization
   - If you see "Using Arc Memory's GitHub OAuth app for authentication", the default Client ID is being used
   - If you see "Default GitHub OAuth Client ID is not configured", contact the Arc Memory team
   - You can always provide your own Client ID with `--client-id`

### Linear Authentication Failures

If you encounter Linear authentication issues:

1. **Network Issues**:
   - Check your internet connection
   - Ensure you can access linear.app in your browser
   - If behind a corporate firewall, check if Linear API access is allowed
   - Try again with `arc auth linear --debug` to see detailed error messages

2. **Port Conflicts**:
   - The Linear OAuth flow requires a local server on port 3000
   - If port 3000 is already in use, the authentication will fail
   - Close any applications that might be using port 3000 and try again

3. **Browser Issues**:
   - The Linear OAuth flow requires a browser to open
   - If the browser doesn't open automatically, check the console for a URL to open manually
   - Make sure you're logged into Linear in your browser

4. **Token Expiration**:
   - Linear OAuth tokens have a very long expiration time (10 years by default)
   - If your token expires, simply run `arc auth linear` again to get a new token

5. **Permission Issues**:
   - Ensure you grant all requested permissions during the OAuth flow
   - If you denied any permissions, you'll need to re-authenticate
   - You may need to revoke the existing token in your Linear settings and re-authenticate

6. **Default Credentials**:
   - Arc Memory uses a default Linear OAuth Client ID and Secret from the Arc-Computer organization
   - If you see "Using Arc Memory's Linear OAuth app for authentication", the default credentials are being used
   - If you see "Default Linear OAuth Client ID is not configured", contact the Arc Memory team
   - You can always provide your own Client ID and Secret with `--client-id` and `--client-secret`

### Re-authentication

You may need to re-authenticate in these situations:

1. **New Device**: When using Arc Memory on a new device
2. **Token Revoked**: If you revoked the token in GitHub or Linear settings
3. **Token Expired**: If your token has expired
4. **Permission Changes**: If you need different permissions

To re-authenticate with GitHub:

```bash
# Simple re-authentication
arc auth gh

# Force re-authentication even if a token exists
arc auth gh --force  # Note: The --force flag is conceptual and may not be implemented yet

# Re-authenticate with debug logging
arc auth gh --debug
```

To re-authenticate with Linear:

```bash
# Simple re-authentication
arc auth linear

# Force re-authentication even if a token exists
arc auth linear --force  # Note: The --force flag is conceptual and may not be implemented yet

# Re-authenticate with debug logging
arc auth linear --debug
```

### Verifying Authentication

To verify that your authentication is working:

```bash
# Check your authentication status
arc doctor

# Try building the graph to verify GitHub and Linear API access
arc build
```

If you see GitHub and Linear data in your graph, your authentication is working correctly.

### Using Both GitHub and Linear

Arc Memory can use both GitHub and Linear data sources simultaneously. To authenticate with both:

```bash
# Authenticate with GitHub
arc auth gh

# Authenticate with Linear
arc auth linear

# Build a graph with both data sources
arc build
```

This will create a knowledge graph that includes both GitHub and Linear data, allowing you to trace connections between issues, pull requests, and Linear tickets.
