# Notion Integration Guide

This guide explains how to set up and use Arc Memory's Notion integration to incorporate data from your Notion workspaces into your knowledge graph.

## 1. Introduction

Arc Memory can ingest pages and database entries from Notion. To do this, you **must** first create a Notion Integration (either "Internal" or "Public") to obtain an API token or OAuth credentials. This integration will act as the bridge between Arc Memory and your Notion workspace.

**Key Requirement**: You need to explicitly share the specific pages and databases within your Notion workspace with the integration you create for Arc Memory to access them.

## 2. Authentication Methods

You have two primary methods to authenticate Arc Memory with Notion:

### Method 1: Internal Integration Token (Recommended for Simplicity)

This method is generally simpler for personal use, internal team workspaces, or when you have direct control over the Notion workspace.

1.  **Go to Notion's "My Integrations" Page**:
    *   Navigate to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations) (you must be logged into Notion).
2.  **Create a New Integration**:
    *   Click the "+ New integration" button.
    *   Give your integration a name (e.g., "Arc Memory Access").
    *   Associate it with the Notion workspace you want to access.
    *   Choose "Internal Integration" for the type.
    *   For capabilities, ensure it has "Read content" permission. "Update content" and "Insert content" are not currently used by Arc Memory's ingestor but may be useful for future features. User information capabilities are generally not needed for basic ingestion.
    *   Click "Submit".
3.  **Copy Your Internal Integration Token**:
    *   Once created, you'll see an "Internal Integration Token" (starts with `secret_...`). Copy this token.
4.  **Set the Environment Variable**:
    *   Arc Memory's Notion ingestor primarily uses an API key for authentication. Set the following environment variable with the token you copied:
        ```bash
        export NOTION_API_KEY="your_internal_integration_token_here"
        ```
        *Note: The codebase might also check for `NOTION_TOKEN` or `NOTION_INTEGRATION_TOKEN`. `NOTION_API_KEY` is the preferred and most current variable.*
5.  **Share Pages/Databases with Your Integration**:
    *   This is a crucial step. See Section 6 for details.

### Method 2: OAuth for Public Integrations (Advanced)

This method is more suitable if you are developing a tool that uses Arc Memory and needs to request access to other users' Notion workspaces without them directly handling API tokens. This involves creating a "Public Integration" in Notion.

1.  **Create a Public Integration in Notion**:
    *   Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations).
    *   Create a new integration, but select "Public Integration" as the type.
    *   You will need to configure Redirect URIs, obtain a Client ID and Client Secret.
    *   Example Redirect URI for local CLI usage: `http://localhost:3000/auth/notion/callback`
2.  **Set Environment Variables for OAuth**:
    *   If you have created your own Public Notion OAuth application, set these environment variables:
        ```bash
        export ARC_NOTION_CLIENT_ID="your_notion_oauth_client_id"
        export ARC_NOTION_CLIENT_SECRET="your_notion_oauth_client_secret"
        export ARC_NOTION_REDIRECT_URI="your_configured_redirect_uri"
        ```
3.  **Authenticate via CLI (if OAuth app is set up)**:
    *   If the above environment variables are set, you can run:
        ```bash
        arc auth notion
        ```
    *   This will initiate the OAuth 2.0 flow. Arc Memory will store the obtained tokens in the system keyring.
    *   **Note**: The default `DEFAULT_NOTION_CLIENT_ID` and `DEFAULT_NOTION_CLIENT_SECRET` in Arc Memory are placeholders. This OAuth flow is primarily intended for users or developers who provide their own fully configured Public Notion OAuth application credentials. For most users, the Internal Integration Token method is simpler.

## 3. Configuring Notion Ingestion via SDK

Whether you're using an Internal Integration Token (`NOTION_API_KEY`) or have completed an OAuth flow, you can specify which Notion databases and/or pages Arc Memory should ingest. This is done using the `source_configs` parameter in `Arc.build()` or `Arc.build_repository()`.

```python
from arc_memory import Arc

# Ensure NOTION_API_KEY is set in your environment if using an Internal Integration Token,
# or that you have previously completed the OAuth flow via 'arc auth notion' if using a Public Integration.

arc = Arc(repo_path="/path/to/your/git/repository") # repo_path might be optional depending on your use case

build_summary = arc.build(
    source_configs={
        "notion": {
            "database_ids": ["your_database_id_without_dashes_1", "your_database_id_without_dashes_2"],
            "page_ids": ["your_page_id_without_dashes_1"]
        }
    },
    # Example: focus only on Notion data for this build
    include_github=False,
    include_jira=False,
    include_linear=False,
    # include_notion=True # This is implicitly True if "notion" is in source_configs
)

print("Build Summary:")
print(f"  Total nodes added: {build_summary.get('total_nodes_added')}")
print(f"  Total edges added: {build_summary.get('total_edges_added')}")

if build_summary.get('ingestor_summary'):
    for summary in build_summary['ingestor_summary']:
        if summary['name'] == 'notion':
            print(f"  Notion Ingestor:")
            print(f"    Status: {summary['status']}")
            print(f"    Pages Processed: {summary.get('metadata', {}).get('page_count', 0)}") # Access specific metadata
            print(f"    Databases Processed: {summary.get('metadata', {}).get('database_count', 0)}")
            if summary['error_message']:
                print(f"    Error: {summary['error_message']}")
```

**Key points for SDK configuration:**

*   **`database_ids`**: A list of Notion database IDs (as strings, typically UUIDs without dashes). If provided, the ingestor will fetch pages from these specific databases.
*   **`page_ids`**: A list of Notion page IDs (as strings, typically UUIDs without dashes). If provided, the ingestor will fetch these specific pages.
*   **Behavior without specific IDs**: If neither `database_ids` nor `page_ids` are provided (or if the lists are empty), the Notion ingestor will attempt to search for all pages and databases that have been shared with your Notion integration.
*   **Permissions**: The ingestor can only access content that has been explicitly shared with the Notion integration linked to your `NOTION_API_KEY` or OAuth token.

## 4. Building Knowledge Graph with Notion Data

### Using the CLI:

1.  **Ensure Authentication**:
    *   If using an Internal Integration Token, make sure the `NOTION_API_KEY` environment variable is set.
    *   If using a Public Integration with your own OAuth app, ensure `ARC_NOTION_CLIENT_ID`, `ARC_NOTION_CLIENT_SECRET`, and `ARC_NOTION_REDIRECT_URI` are set and you have run `arc auth notion` successfully.
2.  **Run the Build Command**:
    ```bash
    arc build --notion
    ```
    This command will ingest Notion data based on the active authentication method and the permissions granted to your Notion integration. By default, without SDK configuration for specific IDs, it will attempt to discover and ingest all shared pages and databases.

### Using the SDK:
Refer to the "Configuring Notion Ingestion via SDK" section above for detailed instructions on how to control Notion ingestion using `source_configs`.

## 5. Sharing Pages/Databases with Your Notion Integration

**This is a critical step for the Notion integration to access any data.**

Whether you created an Internal or a Public integration, it initially has no access to your pages or databases. You must manually share the specific content you want Arc Memory to ingest with that integration.

1.  **Go to the Notion Page or Database**: Open the page or database you want Arc Memory to access in your Notion workspace.
2.  **Click "Share"**: Usually found in the top-right corner of the Notion interface.
3.  **Invite Your Integration**:
    *   In the "Invite" or "Share with people, integrations, and more" search box, start typing the name you gave your Notion integration (e.g., "Arc Memory Access").
    *   Select your integration from the list.
    *   Ensure it has at least "Can view" or "Read content" permissions. For databases, granting "Can view" on the database allows the ingestor to see the database structure and its pages.
    *   Click "Invite".
4.  **Repeat for all relevant content**: You must do this for every top-level page and database you want Arc Memory to ingest. If a page is a sub-page of an already shared page, it might inherit permissions, but it's good practice to verify for key items.

*Tip: For databases, sharing the database itself with the integration will allow Arc Memory to see all pages within that database (respecting any filters you might apply via SDK).*

Refer to [Notion's official documentation on sharing](https://www.notion.so/help/sharing-and-permissions) for the most up-to-date instructions.

## 6. Troubleshooting

*   **`NOTION_API_KEY` not set or invalid**:
    *   Ensure the `NOTION_API_KEY` environment variable is correctly set with your **Internal Integration Token**.
    *   Verify the token is not revoked and is copied correctly.
*   **OAuth Issues (for Public Integrations)**:
    *   Ensure `ARC_NOTION_CLIENT_ID`, `ARC_NOTION_CLIENT_SECRET`, and `ARC_NOTION_REDIRECT_URI` are correct for **your** Public Notion App.
    *   Confirm the Redirect URI in your environment variable matches the one configured in the Notion Developer Console for your app.
*   **Pages/Databases Not Found or Empty Results**:
    *   **Crucially, ensure you have shared the specific pages and/or databases in Notion with your integration** (see Section 5). The integration can only "see" what has been explicitly shared with it.
    *   If using `database_ids` or `page_ids` in the SDK, double-check that these IDs are correct (they are typically UUIDs, often presented by Notion without dashes in URLs, but the API expects them with dashes, though Arc Memory's client might handle this).
*   **Rate Limits**: Notion has API rate limits. While Arc Memory's client includes some basic handling, very large workspaces might hit these limits. If you see rate limit errors:
    *   The error message from the ingestor summary might indicate a "Retry-After" period.
    *   Consider ingesting smaller sets of data using `database_ids` or `page_ids` if possible.
*   **Check Ingestor Summary**: The build result from `arc.build()` contains an `ingestor_summary`. Inspect the entry for the "notion" ingestor. It will report its status, the number of items processed, and any error messages encountered.
    ```
    # Example of checking summary (from SDK example above)
    if build_summary.get('ingestor_summary'):
        for summary in build_summary['ingestor_summary']:
            if summary['name'] == 'notion' and summary['error_message']:
                print(f"Notion Ingestor Error: {summary['error_message']}")
    ```
