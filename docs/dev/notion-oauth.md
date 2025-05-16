# Notion OAuth Integration

This guide explains how to set up and use the Notion OAuth integration with Arc Memory.

## Overview

Arc Memory can ingest data from Notion workspaces via the Notion API. To access a user's Notion workspace, you need to authenticate using OAuth. This document explains how to:

1. Create a Notion integration
2. Set up OAuth credentials
3. Configure Arc Memory to use these credentials
4. Authenticate with Notion from the CLI

## Creating a Notion Integration

### Step 1: Create a Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give your integration a name (e.g., "Arc Memory")
4. Select the workspace where you want to create the integration
5. Upload an icon (optional)
6. Click "Submit"

### Step 2: Configure OAuth

1. In your integration settings, scroll to "Authorization" section
2. Click "Add capability" under OAuth Domain & URIs
3. Add the following redirect URI:
   - For development: `http://localhost:3000/auth/notion/callback`
   - For production: `https://arc.computer/auth/notion/callback`
4. Make sure "User capabilities" includes the following permissions:
   - `Read content`
   - `Read user information`
   - `Read comments`
   - Any other permissions your integration requires
5. Save your changes

### Step 3: Copy OAuth Credentials

1. Note down your "OAuth client ID" (looks like: `00000000-0000-0000-0000-000000000000`)
2. Note down your "OAuth client secret" (looks like: `secret_00000000000000000000000000000000000000000000`)

## Configuring Arc Memory

### Option 1: Environment Variables

Set the following environment variables:

```bash
export ARC_NOTION_CLIENT_ID="your-client-id"
export ARC_NOTION_CLIENT_SECRET="your-client-secret"
export ARC_NOTION_REDIRECT_URI="http://localhost:3000/auth/notion/callback"  # Optional, defaults to this value
```

### Option 2: Command Line Arguments

When running the `arc auth notion` command, provide the client ID and secret as arguments:

```bash
arc auth notion --client-id "your-client-id" --client-secret "your-client-secret"
```

## Authentication Flow

The authentication flow works as follows:

1. Run the `arc auth notion` command.
2. Arc Memory will start a local web server to receive the OAuth callback.
3. Your browser will open with the Notion authorization page.
4. Select the workspace you want to grant access to.
5. Notion will redirect back to the local server with an authorization code.
6. Arc Memory will exchange this code for an access token.
7. The access token will be securely stored in your system keyring.

### Example

```bash
# Using default Arc Memory credentials (if configured)
arc auth notion

# Using custom credentials
arc auth notion --client-id "your-client-id" --client-secret "your-client-secret"
```

## Permissions Required

The Notion integration needs the following permissions to work properly with Arc Memory:

- `read_content`: To access pages and databases
- `read_user`: To get user information
- `read_comments`: To access comments on pages and databases

## Troubleshooting

### Port Already in Use

If you see an error about the callback server port already being in use:

```
Failed to start local callback server.
This may be because port 3000 is already in use.
```

Try closing any applications that might be using port 3000, such as development servers or other instances of Arc Memory.

### Invalid Redirect URI

If you see an error about an invalid redirect URI:

```
Authentication failed: The redirect uri does not match the registered redirect URI for this application.
```

Make sure the redirect URI you registered in your Notion integration matches the one being used by Arc Memory. The default is `http://localhost:3000/auth/notion/callback`.

### Token Storage Issues

If you see a warning about failing to store the token in the system keyring:

```
Authentication successful, but failed to store token in system keyring.
```

Arc Memory will display your token. You can save it and set it as an environment variable:

```bash
export NOTION_API_KEY="your-token"
```

## Security Notes

- Your Notion OAuth credentials (client ID and secret) should be kept secure.
- Access tokens are stored in your system's secure keyring.
- In the OAuth flow, tokens never leave your local machine.
- When a user authenticates, they select which workspaces and pages to give access to.

## Development Notes

For developers working on the Arc Memory codebase:

- The Notion authentication implementation is in `arc_memory/auth/notion.py`
- Unit tests are in `arc_memory/tests/auth/test_notion_auth.py`
- The CLI command is defined in `arc_memory/cli/auth.py`
- Default credentials (if provided) are stored in `arc_memory/auth/default_credentials.py`