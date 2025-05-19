# Jira Integration Guide

This guide explains how to set up and use Arc Memory's Jira integration to incorporate Jira issues and projects into your knowledge graph.

## 1. Mandatory Credential Setup: Create Your Own Jira OAuth Application

**IMPORTANT: The default Jira OAuth credentials bundled with Arc Memory are placeholders ONLY and WILL NOT WORK. You MUST create your own Jira OAuth 2.0 (3LO) Application to integrate Jira with Arc Memory.**

This is necessary because Jira requires each integration to have a unique Client ID and Secret, and a specific Redirect URI that Atlassian will send authentication codes to.

### Steps to Create Your Jira OAuth Application:

1.  **Go to the Atlassian Developer Console**: [https://developer.atlassian.com/console/myapps/](https://developer.atlassian.com/console/myapps/)
2.  **Create a new "OAuth 2.0 integration"**:
    *   Click "Create" and select "OAuth 2.0 integration".
    *   Name your application (e.g., "Arc Memory - My Org").
    *   Agree to the terms and conditions.
3.  **Configure Permissions**:
    *   Navigate to the "Permissions" tab for your newly created app.
    *   Add the following Jira API scopes (at a minimum):
        *   `read:jira-work` (View Jira issue data)
        *   `read:jira-user` (View user information - may be needed for assignee/reporter details)
        *   `offline_access` (To allow Arc Memory to refresh tokens without user interaction)
        *   *(Optional but Recommended)* `read:project:jira` (To read project information)
    *   Refer to the [Atlassian Jira Cloud permissions documentation](https://developer.atlassian.com/cloud/jira/platform/scopes-for-oauth-2-3LO-apps/) for details on available scopes.
4.  **Configure Authorization**:
    *   Navigate to the "Authorization" tab.
    *   Click "Add" next to "OAuth 2.0 (3LO)".
    *   For the **Callback URL** (also known as Redirect URI), enter:
        *   `http://localhost:3000/auth/jira/callback`
        *   This is the default URI used by the Arc Memory CLI (`arc auth jira`) for local authentication. Ensure this matches what you will set in the `ARC_JIRA_REDIRECT_URI` environment variable.
5.  **Note Your Credentials**:
    *   Go to the "Settings" tab for your app.
    *   You will find your **Client ID** and **Client Secret** here. These are crucial for the next step.

For detailed official instructions, refer to the [Atlassian documentation on creating an OAuth 2.0 (3LO) app](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/).

### Set Required Environment Variables:

Once you have your Jira OAuth Application, you **must** set the following environment variables in your system for Arc Memory to use them:

*   **`ARC_JIRA_CLIENT_ID`**: Your application's Client ID.
    ```bash
    export ARC_JIRA_CLIENT_ID="your-app-client-id"
    ```
*   **`ARC_JIRA_CLIENT_SECRET`**: Your application's Client Secret.
    ```bash
    export ARC_JIRA_CLIENT_SECRET="your-app-client-secret"
    ```
*   **`ARC_JIRA_REDIRECT_URI`**: The Callback URL you configured in your Jira OAuth app. For local CLI usage, this is typically:
    ```bash
    export ARC_JIRA_REDIRECT_URI="http://localhost:3000/auth/jira/callback"
    ```
*   **`ARC_JIRA_CLOUD_ID`**: Your Jira Cloud instance's unique ID.
    *   **How to find it**: Your Cloud ID is a unique identifier for your Jira Cloud site.
        1.  One way to find it is by logging into your Jira instance. The Cloud ID is part of the URL for some administrative pages, or can be found by inspecting network requests in your browser's developer tools when interacting with Jira.
        2.  Alternatively, after successfully authenticating once via `arc auth jira` (which uses your Client ID and Secret), Arc Memory will attempt to discover this ID from the OAuth token response (from the `accessible-resources` endpoint) and store it. If `arc auth jira` completes, this ID should be configured.
        3.  If using the SDK and you know your Cloud ID, you can also pass it directly via `source_configs` (see SDK section below).
    ```bash
    export ARC_JIRA_CLOUD_ID="your-jira-cloud-id"
    ```

## 2. Authenticating Arc Memory with Jira (CLI)

After creating your Jira OAuth application and setting the environment variables (`ARC_JIRA_CLIENT_ID`, `ARC_JIRA_CLIENT_SECRET`, `ARC_JIRA_REDIRECT_URI`, and `ARC_JIRA_CLOUD_ID`), you can authenticate Arc Memory:

Run the authentication command:
```bash
arc auth jira
```
This command uses the environment variables you set to initiate the OAuth 2.0 flow:
1.  It starts a local server on port 3000 (or as specified by your `ARC_JIRA_REDIRECT_URI`) to receive the OAuth callback.
2.  It will open a browser window directing you to the Atlassian authorization page.
3.  You will be prompted to log in to your Atlassian account (if not already logged in) and authorize the application you created.
4.  Upon successful authorization, Atlassian redirects back to your specified `ARC_JIRA_REDIRECT_URI`. Arc Memory captures the authorization code.
5.  Arc Memory then exchanges this code for an access token and a refresh token, storing them securely in your system's keyring.
6.  It will also attempt to discover and store your Jira Cloud ID if not already explicitly set via `ARC_JIRA_CLOUD_ID`.

If the browser doesn't open automatically, the console will display a URL for you to open manually.

## 3. Configuring Jira Ingestion via SDK

For users of the Arc Memory Python SDK, you can configure Jira ingestion directly within your code. This is particularly useful for specifying which projects to ingest or for providing the `cloud_id` if it's not set as an environment variable.

The `cloud_id` and specific `project_keys` to ingest can be passed to `Arc.build()` or `Arc.build_repository()` using the `source_configs` parameter.

```python
from arc_memory import Arc

# Initialize Arc with the path to your repository
arc = Arc(repo_path="/path/to/your/git/repository")

# Configure Jira ingestion:
# Note: Your ARC_JIRA_CLIENT_ID, ARC_JIRA_CLIENT_SECRET, and ARC_JIRA_REDIRECT_URI
# must still be set as environment variables for the initial OAuth token acquisition by Arc Memory.
# The token is then stored and managed by Arc Memory.

build_summary = arc.build(
    source_configs={
        "jira": {
            "cloud_id": "your-jira-cloud-id",  # This overrides ARC_JIRA_CLOUD_ID if both are set
            "project_keys": ["PROJECT_A_KEY", "PROJECT_B_KEY"]  # Only ingest these specific projects
        }
    },
    include_github=False, # Assuming only Jira for this example
    include_linear=False
    # include_jira=True # This is implicitly True if "jira" is in source_configs
)

print("Build Summary:")
print(f"  Total nodes added: {build_summary.get('total_nodes_added')}")
print(f"  Total edges added: {build_summary.get('total_edges_added')}")

if build_summary.get('ingestor_summary'):
    for summary in build_summary['ingestor_summary']:
        if summary['name'] == 'jira':
            print(f"  Jira Ingestor:")
            print(f"    Status: {summary['status']}")
            print(f"    Nodes Processed: {summary['nodes_processed']}")
            print(f"    Edges Processed: {summary['edges_processed']}")
            if summary['error_message']:
                print(f"    Error: {summary['error_message']}")
```

**Key points for SDK configuration:**

*   **`cloud_id`**: If provided in `source_configs["jira"]`, it will take precedence over the `ARC_JIRA_CLOUD_ID` environment variable for that specific build operation. It's recommended to set this if you work with multiple Jira instances or prefer explicit configuration.
*   **`project_keys`**: If this list is provided under `source_configs["jira"]`, the Jira ingestor will *only* attempt to fetch and process issues from the specified Jira projects. If omitted, the ingestor will attempt to fetch issues from all projects accessible to the authenticated user and their token permissions.
*   **Authentication Tokens**: The SDK's build methods assume that authentication tokens have already been acquired (e.g., via `arc auth jira` CLI). The `source_configs` are for directing the ingestor's behavior *after* authentication is established.

## 4. Building Knowledge Graph with Jira Data

### Using the CLI:
Once authenticated (via `arc auth jira` using your custom app credentials and set environment variables), you can include Jira data in your knowledge graph build:
```bash
arc build --jira
```
This command will use the stored Jira token and the `ARC_JIRA_CLOUD_ID` environment variable. By default, it attempts to ingest data from all projects accessible via your token.

To combine with other data sources:
```bash
arc build --jira --github
```

### Using the SDK:
As shown in the section "Configuring Jira Ingestion via SDK," use the `source_configs` parameter within the `arc.build()` method to specify `cloud_id` and/or `project_keys` for targeted Jira ingestion.

## 5. Jira Integration Features

The Jira integration currently includes:

- **Projects**: Basic project information including key, name, and description.
- **Issues**: Comprehensive issue details including summary, description, status, type, priority, assignee, reporter, created/updated timestamps, and labels.
- **Issue Relationships**: Issue links (e.g., "depends on", "blocks", "relates to") are translated into graph relationships.

## 6. Schema Mapping

- **Jira Projects** → Custom `jira_project` node type within Arc Memory.
- **Jira Issues** → `NodeType.ISSUE` (standard Arc Memory issue node type).
- **Issue Links** → Various `EdgeRel` types like `EdgeRel.DEPENDS_ON`, `EdgeRel.BLOCKS`, `EdgeRel.MENTIONS`.
- **Project Membership** → `EdgeRel.PART_OF` edges from issues to their respective `jira_project` nodes.

## 7. Troubleshooting

### Authentication Issues:
*   **"Invalid Client ID or Secret" / Authentication Failed**:
    *   Ensure `ARC_JIRA_CLIENT_ID` and `ARC_JIRA_CLIENT_SECRET` environment variables are correctly set with the values from **your custom Jira OAuth Application**.
    *   Verify that the `ARC_JIRA_REDIRECT_URI` environment variable matches *exactly* the Redirect URI configured in your Jira OAuth app.
*   **Port in use error (e.g., for `http://localhost:3000`)**: Another application might be using the port specified in your `ARC_JIRA_REDIRECT_URI`. Close the conflicting application or temporarily change the port in your Jira app and the `ARC_JIRA_REDIRECT_URI` variable (and then re-authenticate using `arc auth jira`).
*   **Token expiration**: Jira OAuth tokens are typically short-lived (e.g., 1 hour). Arc Memory stores refresh tokens and attempts to automatically refresh them. If you consistently face issues, re-running `arc auth jira` might be necessary.

### Missing Data:
*   **No projects or issues visible**:
    *   Confirm your custom Jira OAuth Application has the required permissions (scopes) in the Atlassian Developer Console (e.g., `read:jira-work`, `read:project:jira`).
    *   If you've used `project_keys` in the SDK, ensure the keys are correct and that the authenticated user has access to those projects.
*   **Incorrect `ARC_JIRA_CLOUD_ID`**:
    *   If you've set `ARC_JIRA_CLOUD_ID` manually via environment variable, double-check its accuracy.
    *   If relying on auto-detection by `arc auth jira`, ensure the authentication process completed successfully at least once.
    *   When using the SDK, providing `cloud_id` in `source_configs` is the most explicit way to ensure the correct instance is targeted.

## 8. API Reference

For more details on the Jira Cloud REST API used by this integration:
- [Jira Cloud Platform REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
- [OAuth 2.0 (3LO) Apps Documentation](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)