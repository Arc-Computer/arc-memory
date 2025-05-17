# Jira Integration Guide

This guide explains how to set up and use Arc Memory's Jira integration to incorporate Jira issues and projects into your knowledge graph.

## Prerequisites

- An Atlassian account with access to a Jira Cloud instance
- The Cloud ID of your Jira instance (will be auto-detected during authentication)
- Permissions to create an OAuth application in Atlassian Developer Console

## Setting Up Jira OAuth Integration

### 1. Create an OAuth 2.0 Application in Atlassian Developer Console

1. Go to [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/)
2. Click "Create" and select "OAuth 2.0 integration"
3. Fill in the application details:
   - Name: "Arc Memory"
   - Description: "Knowledge graph tool for development workflows"
4. For Permissions, add:
   - Jira API: "Read" (minimum)
   - Jira API: "Write" (optional, for future enhancements)
5. Configure the callback URL:
   - For local development: `http://localhost:3000/auth/jira/callback`
   - For production: `https://arc.computer/auth/jira/callback`
6. Save the application and note the Client ID and Client Secret

### 2. Configure Arc Memory with Jira OAuth Credentials

You can either:

**Option A: Use environment variables**
```bash
export ARC_JIRA_CLIENT_ID="your-client-id"
export ARC_JIRA_CLIENT_SECRET="your-client-secret"
```

**Option B: Supply credentials directly in the authentication command**
```bash
arc auth jira --client-id "your-client-id" --client-secret "your-client-secret"
```

### 3. Authenticate with Jira

Run the authentication command:

```bash
arc auth jira
```

This will:
1. Start a local server to receive the OAuth callback
2. Open a browser to the Atlassian authorization page
3. After you authorize, store the access token securely in your system keyring
4. Automatically detect and store your Jira Cloud ID

If the browser doesn't open automatically, you'll see a URL in the console that you can manually open.

## Building Knowledge Graph with Jira Data

Once authenticated, you can include Jira data in your knowledge graph build:

```bash
arc build --jira
```

To combine with other data sources:

```bash
arc build --jira --github --linear
```

## Jira Integration Features

The Jira integration currently includes:

- **Projects**: Basic project information including key, name, and description
- **Issues**: Comprehensive issue details including:
  - Summary and description
  - Status and type
  - Priority
  - Assignee and reporter
  - Created and updated timestamps
  - Labels
- **Issue Relationships**: Issue links are translated into graph relationships
  - Dependencies between issues
  - Blockages
  - Related issues

## Schema Mapping

The Jira integration maps Jira entities to Arc Memory's schema as follows:

- **Jira Projects** → Custom `jira_project` node type
- **Jira Issues** → `NodeType.ISSUE` (standard issue node type)
- **Issue Links** → Various edge types including:
  - `EdgeRel.DEPENDS_ON` for "depends on" links
  - `EdgeRel.BLOCKS` for "blocks" links
  - `EdgeRel.MENTIONS` for "relates to" links
- **Project Membership** → `EdgeRel.PART_OF` edges from issues to their projects

## Troubleshooting

### Authentication Issues

- **Port in use error**: If port 3000 is already in use, try closing applications that might be using it.
- **Token expiration**: Jira tokens expire after 1 hour by default. The integration will automatically attempt to refresh them.

### Missing Data

- **No projects or issues visible**: Check that your OAuth token has sufficient permissions. Try re-authenticating with additional scopes.
- **Missing Cloud ID**: If your Jira Cloud ID isn't auto-detected, specify it manually:
  ```bash
  export ARC_JIRA_CLOUD_ID="your-cloud-id"
  ```
  or
  ```bash
  arc auth jira --cloud-id "your-cloud-id"
  ```

## API Reference

For more details on the Jira API used by this integration, see:
- [Jira Cloud Platform REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Jira Software Cloud REST API](https://developer.atlassian.com/cloud/jira/software/rest/intro/)