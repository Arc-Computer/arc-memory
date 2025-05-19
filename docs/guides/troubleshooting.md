# Troubleshooting Guide

This guide provides solutions for common issues you might encounter when using Arc Memory SDK.

**Related Documentation:**
- [Dependencies Guide](./dependencies.md) - Complete list of dependencies
- [Test Environment Setup](./test-environment.md) - Setting up a test environment
- [Doctor Commands](../cli/doctor.md) - Checking graph status and diagnostics

## Installation Issues

### Missing Dependencies

**Symptom**: Import errors when trying to use Arc Memory SDK.

**Solution**:
1. Ensure you have all required dependencies installed:
   ```bash
   pip install arc-memory
   ```

2. If you're using specific features, install the relevant optional dependencies:
   ```bash
   # For GitHub integration
   pip install requests pyjwt cryptography keyring

   # For CLI features
   pip install typer rich tqdm
   ```

3. Check for version conflicts:
   ```bash
   pip list
   ```

4. Use the dependency validation function:
   ```python
   from arc_memory.dependencies import validate_dependencies
   validate_dependencies()
   ```

### Python Version Issues

**Symptom**: `SyntaxError` or other errors indicating incompatible Python version.

**Solution**:
1. Arc Memory SDK requires Python 3.10 or higher. Check your Python version:
   ```bash
   python --version
   ```

2. If you have multiple Python versions installed, ensure you're using the correct one:
   ```bash
   # On Unix/macOS
   which python

   # On Windows
   where python
   ```

3. Create a virtual environment with the correct Python version:
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate  # On Unix/macOS
   venv\Scripts\activate     # On Windows
   ```

## Database Issues

### Database Not Found

**Symptom**: Error message indicating the database file doesn't exist.

**Solution**:
1. Run the build command to create the database:
   ```bash
   arc build
   ```

2. Check if the database file exists at the default location:
   ```bash
   # On Unix/macOS
   ls -la ~/.arc/graph.db

   # On Windows
   dir %USERPROFILE%\.arc\graph.db
   ```

3. Specify a custom database path:
   ```bash
   arc build --db-path ./my-graph.db
   arc trace file --db-path ./my-graph.db path/to/file.py 42
   ```

4. Use test mode for development and testing:
   ```python
   from arc_memory.sql.db import init_db
   conn = init_db(test_mode=True)
   ```

### Database Connection Errors

**Symptom**: Errors like `'PosixPath' object has no attribute 'execute'` or `'str' object has no attribute 'execute'`.

**Solution**:
1. Make sure you're passing a database connection object to functions that require it:
   ```python
   from arc_memory.sql.db import get_connection, get_node_by_id

   # Correct: Get a connection first
   conn = get_connection(db_path)
   node = get_node_by_id(conn, "node:123")
   ```

2. Use the `ensure_connection` function for flexible code that works with both paths and connections:
   ```python
   from arc_memory.sql.db import get_node_by_id

   # This works with either a path or a connection
   node = get_node_by_id(db_path, "node:123")
   node = get_node_by_id(conn, "node:123")
   ```

3. Check the function documentation to understand parameter requirements:
   ```python
   help(get_node_by_id)  # Shows parameter types and descriptions
   ```

4. Use a context manager for automatic connection handling:
   ```python
   from contextlib import closing
   from arc_memory.sql.db import get_connection

   with closing(get_connection(db_path)) as conn:
       # Use conn within this block
       node = get_node_by_id(conn, "node:123")
   # Connection is automatically closed here
   ```

### Database Corruption

**Symptom**: SQL errors or unexpected behavior when querying the database.

**Solution**:
1. Check the database status:
   ```bash
   arc doctor
   ```

2. Rebuild the database:
   ```bash
   # Rename the existing database
   mv ~/.arc/graph.db ~/.arc/graph.db.bak

   # Rebuild
   arc build
   ```

3. If you have a compressed backup, restore from it:
   ```bash
   # On Unix/macOS
   cp ~/.arc/graph.db.zst ~/.arc/graph.db.zst.bak

   # Decompress
   from arc_memory.sql.db import decompress_db
   decompress_db()
   ```

### Performance Issues

**Symptom**: Slow database operations or high memory usage.

**Solution**:
1. Check the size of your database:
   ```bash
   arc doctor
   ```

2. Limit the scope of your build:
   ```bash
   arc build --max-commits 1000 --days 90
   ```

3. Use incremental builds:
   ```bash
   arc build --incremental
   ```

4. Compress the database when not in use:
   ```python
   from arc_memory.sql.db import compress_db
   compress_db()
   ```

## Ingestion Issues

This section covers problems related to fetching data from specific sources like Jira, Notion, GitHub, etc., during the `arc build` process. Always start by checking the `ingestor_summary` returned by `arc.build()` or printed by the CLI for detailed error messages from specific ingestors.

### Interpreting `ingestor_summary`

When you build your knowledge graph using `arc.build()` (SDK) or `arc build` (CLI), the process attempts to fetch data from multiple sources. The summary of this process is crucial for troubleshooting.

**SDK Example:**
```python
from arc_memory import Arc

arc = Arc(repo_path=".")
# Example: build_results = arc.build(include_github=True, include_jira=True, include_notion=True)
# Ensure you have configured authentication for each service you include.
build_results = arc.build(
    include_github=True, # Assumes GITHUB_TOKEN is set
    source_configs={
        "jira": {"project_keys": ["YOUR_PROJECT_KEY"]}, # Assumes Jira auth is set up
        "notion": {"page_ids": ["your_page_id"]} # Assumes Notion auth is set up
    }
)

print("Ingestor Summary:")
for summary in build_results.get("ingestor_summary", []):
    print(f"  Ingestor: {summary['name']}")
    print(f"    Status: {summary['status']}")
    print(f"    Nodes Processed: {summary['nodes_processed']}")
    print(f"    Edges Processed: {summary['edges_processed']}")
    if summary['error_message']:
        print(f"    Error: {summary['error_message']}")
    # Some ingestors might provide additional metadata in their summary's metadata field
    if summary.get('metadata'): 
        print(f"    Metadata: {summary['metadata']}")
```

**Structure of an entry in `ingestor_summary`:**
```json
{
    "name": "jira", // Name of the ingestor
    "status": "failure", // "success" or "failure"
    "nodes_processed": 0,
    "edges_processed": 0,
    "error_message": "API token is invalid or expired. Cloud ID: your-cloud-id. Project Keys: ['YOUR_PROJECT_KEY']",
    "processing_time_seconds": 1.23,
    "metadata": {"project_count": 0, "issue_count": 0, "timestamp": "..."} // Optional, ingestor-specific
}
```
Check the `status` and `error_message` for each ingestor to pinpoint issues. The `error_message` may contain context like relevant IDs.

### Partial Success During Ingestion

It's possible for some ingestors to succeed while others fail during a single `arc build` run. For example, GitHub data might be ingested successfully, but Jira ingestion could fail due to an authentication error.
- The `ingestor_summary` (as shown above) will detail the status for each ingestor.
- The overall `total_nodes_added` and `total_edges_added` in the main build results will only reflect data from successfully completed ingestors.
- Address the errors for the failed ingestors (using the `error_message` in their summary entry) and re-run the build. Arc Memory will attempt to incrementally update data from already successful ingestors and re-attempt the failed ones.

### Authentication Failures (Jira/Notion)

**Symptom**: Errors in `ingestor_summary` for Jira or Notion, such as "Unauthorized", "Invalid Client ID", "Redirect URI mismatch", "API token is invalid", or "401 Client Error".

**Troubleshooting Steps**:

1.  **Verify Environment Variables**:
    *   **Jira**: Ensure `ARC_JIRA_CLIENT_ID`, `ARC_JIRA_CLIENT_SECRET`, `ARC_JIRA_REDIRECT_URI`, and `ARC_JIRA_CLOUD_ID` are correctly set. **You must create your own Jira OAuth App**. Refer to the [Jira Integration Guide](./jira_integration.md#1-mandatory-credential-setup-create-your-own-jira-oauth-application).
    *   **Notion (Internal Token - Recommended)**: Ensure `NOTION_API_KEY` is set with your Internal Integration Token.
    *   **Notion (Public OAuth App - Advanced)**: If you've set up your own Notion OAuth app, ensure `ARC_NOTION_CLIENT_ID`, `ARC_NOTION_CLIENT_SECRET`, and `ARC_NOTION_REDIRECT_URI` are correct.
    *   Double-check for typos or extra spaces in these variable values.

2.  **Match OAuth App Credentials**:
    *   The Client ID and Secret in your environment variables **must exactly match** those from the Jira or Notion OAuth application you created in their respective developer consoles.

3.  **Check Redirect URI (for CLI-based OAuth flows like Jira and custom Notion OAuth)**:
    *   The `ARC_JIRA_REDIRECT_URI` or `ARC_NOTION_REDIRECT_URI` must be one of the Redirect URIs registered in your Jira/Notion OAuth application settings. For the CLI, this is typically `http://localhost:3000/auth/jira/callback` or `http://localhost:3000/auth/notion/callback`.

4.  **Re-authenticate via CLI**:
    *   For Jira: `arc auth jira`
    *   For Notion (if using your own Public OAuth app): `arc auth notion`
    *   This can help refresh tokens and ensure the correct ones are stored by Arc Memory.

5.  **Notion Specific**:
    *   **Internal Integration Token**: Confirm the token is valid and not revoked.
    *   **Content Sharing**: Ensure the Notion pages and databases you want to access have been explicitly "Shared" with your Notion Integration (the one linked to your `NOTION_API_KEY` or OAuth app). This is a common reason for missing content. See the [Notion Integration Guide](./notion_integration.md#5-sharing-pagesdatabases-with-your-notion-integration).

### Content Not Found / Empty Results (Notion)

**Symptom**: The Notion ingestor in `ingestor_summary` shows `status: "success"` but `nodes_processed: 0` (or very few, e.g., only database nodes but no pages from within them), or specific IDs provided in `source_configs` for `page_ids` or `database_ids` are not found.

**Troubleshooting Steps**:

1.  **Crucial: Share Content with Your Notion Integration**:
    *   Go to your Notion workspace.
    *   For **every page and database** you want Arc Memory to ingest, you must click "Share" (top-right) and invite the Notion Integration you created (the one associated with your `NOTION_API_KEY` or OAuth app).
    *   Grant at least "Can view" permissions. For databases, sharing the database itself allows the ingestor to see pages within it.
    *   Refer to the sharing instructions in the [Notion Integration Guide](./notion_integration.md#5-sharing-pagesdatabases-with-your-notion-integration).
2.  **Verify IDs in `source_configs`**:
    *   If you're using `database_ids` or `page_ids` in the SDK `source_configs`, double-check that these IDs are correct (usually UUIDs, Notion URLs might show them without dashes but the API might expect dashes; Arc Memory's client typically handles this normalization). Ensure they belong to the workspace associated with your token.

### Incorrect `cloud_id` for Jira

**Symptom**: Jira ingestor fails. The `error_message` in `ingestor_summary` might indicate that the cloud instance wasn't found, an invalid URL was constructed (e.g., containing `None` for the cloud_id part), or there are authentication issues that stem from targeting the wrong Jira site.

**Troubleshooting Steps**:

1.  **Verify Jira Cloud ID**:
    *   If using the `ARC_JIRA_CLOUD_ID` environment variable, ensure it's the correct ID for your Jira Cloud instance.
    *   If using the SDK and providing `cloud_id` in `source_configs["jira"]`, verify that value. This SDK value will override the environment variable for that specific build.
2.  **Finding Your `cloud_id`**:
    *   Your Jira Cloud ID is a unique UUID that identifies your specific Jira site. It's **not** your company name in `yourcompany.atlassian.net`.
    *   After successfully authenticating with `arc auth jira` at least once, Arc Memory attempts to discover and store this ID. If `arc auth jira` fails, this ID might not be set.
    *   You can also find it by logging into your Jira instance and inspecting network requests in your browser's developer tools while using Jira, or by checking specific admin pages if available.
    *   Refer to the "Set Required Environment Variables" section in the [Jira Integration Guide](./jira_integration.md) for more tips.
3.  **Ensure Correct Account**: Make sure the Jira account used for authentication (when `arc auth jira` was run) has access to the projects on the Jira instance identified by the `cloud_id`.

## GitHub Integration Issues

### Authentication Failures

**Symptom**: GitHub API errors or rate limiting.

**Solution**:
1. Authenticate with GitHub:
   ```bash
   arc auth github
   ```
   (Note: The CLI command was `arc auth gh` in older versions, `arc auth github` is current).

2. Check your authentication status:
   ```bash
   arc auth status
   ```

3. If you're hitting rate limits, ensure `GITHUB_TOKEN` environment variable is set with a Personal Access Token (PAT) that has appropriate scopes (`repo`, `read:user`, `read:org`).

4. For CI/CD environments, using a GitHub App is recommended for more robust authentication and rate limits.
   Refer to the [GitHub Integration Guide](./github_integration.md).


### Network Issues

**Symptom**: Timeout or connection errors when accessing GitHub.

**Solution**:
1. Check your internet connection.

2. If you're behind a corporate firewall, ensure GitHub API access is allowed.

3. Use a proxy if necessary:
   ```bash
   export HTTPS_PROXY=http://proxy.example.com:8080
   arc build
   ```

4. Increase the timeout:
   ```bash
   arc build --timeout 120
   ```

## Git Issues

### Git Not Found

**Symptom**: Error indicating Git executable not found.

**Solution**:
1. Ensure Git is installed and in your PATH:
   ```bash
   git --version
   ```

2. If Git is installed in a non-standard location, set the path:
   ```python
   import os
   os.environ['GIT_PYTHON_GIT_EXECUTABLE'] = '/path/to/git'
   ```

### Repository Issues

**Symptom**: Errors about the repository not being found or not being a Git repository.

**Solution**:
1. Ensure you're in a Git repository:
   ```bash
   git status
   ```

2. Specify the repository path explicitly:
   ```bash
   arc build --repo-path /path/to/repo
   ```

3. For shallow clones, fetch the full history:
   ```bash
   git fetch --unshallow
   ```

## Plugin Issues

### Plugin Discovery Failures

**Symptom**: Custom plugins not being discovered.

**Solution**:
1. Ensure your plugin is properly installed:
   ```bash
   pip list | grep your-plugin-name
   ```

2. Check that your plugin is registered with the correct entry point:
   ```python
   # In setup.py or pyproject.toml
   entry_points={
       "arc_memory.plugins": [
           "your-plugin-name = your_package.module:YourPluginClass",
       ],
   }
   ```

3. Enable verbose logging to see plugin discovery details:
   ```bash
   arc build --verbose 
   ```
   (Note: `--debug` might be available for more detailed logs than `--verbose` in some commands or future versions).

### Plugin Errors

**Symptom**: Errors during custom plugin execution, often visible in the `ingestor_summary` for your plugin.

**Solution**:
1. Check the `error_message` for your plugin in the `ingestor_summary`.

2. Enable verbose or debug logging:
   ```bash
   arc build --verbose
   ```

3. Test your plugin in isolation, as shown in the [Custom Ingestors Guide](./custom_ingestors.md#3-example-implementation).
   ```python
   # Example for testing your plugin
   # from your_package.module import YourPluginClass
   # plugin = YourPluginClass()
   # config = {"your_plugin_config_key": "value"} # Simulate source_configs
   # nodes, edges, metadata = plugin.ingest(**config)
   # print(f"Nodes: {len(nodes)}, Edges: {len(edges)}, Metadata: {metadata}")
   ```

## CLI Issues

### Command Not Found

**Symptom**: `arc` command not found.

**Solution**:
1. Ensure Arc Memory SDK is installed:
   ```bash
   pip install arc-memory
   ```

2. Check if the `arc` command is in your PATH:
   ```bash
   # On Unix/macOS
   which arc

   # On Windows
   where arc
   ```

3. If using a virtual environment, ensure it's activated:
   ```bash
   source venv/bin/activate  # On Unix/macOS
   venv\Scripts\activate     # On Windows
   ```

### Unexpected CLI Behavior

**Symptom**: CLI commands not working as expected.

**Solution**:
1. Check the command help:
   ```bash
   arc --help
   arc build --help
   ```

2. Enable debug logging:
   ```bash
   arc --debug build
   ```

3. Check for environment variables that might affect behavior:
   ```bash
   # On Unix/macOS
   env | grep ARC

   # On Windows
   set | findstr ARC
   ```

## Test Mode Issues

### Test Mode Not Working

**Symptom**: Test mode not behaving as expected.

**Solution**:
1. Ensure you're initializing the database with test mode:
   ```python
   from arc_memory.sql.db import init_db
   conn = init_db(test_mode=True)
   ```

2. Check that you're using the test connection for all operations:
   ```python
   from arc_memory.sql.db import get_node_count
   count = get_node_count(conn)  # Use the same connection
   ```

3. If you're mixing real and test databases, ensure you're using the correct one:
   ```python
   # Test database
   test_conn = init_db(test_mode=True)

   # Real database
   real_conn = init_db(test_mode=False)
   ```

## Getting Additional Help

If you're still experiencing issues:

1. Check the [GitHub repository](https://github.com/Arc-Computer/arc-memory/issues) for similar issues.

2. Enable debug logging and capture the output:
   ```bash
   arc --debug build > build_log.txt 2>&1
   ```

3. Create a minimal reproducible example.

4. Open an issue on GitHub with:
   - A clear description of the problem
   - Steps to reproduce
   - Expected vs. actual behavior
   - Debug logs
   - Your environment details (OS, Python version, Arc Memory version)
