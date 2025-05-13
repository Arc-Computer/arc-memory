# Arc Memory Security Guide

This document provides security best practices and recommendations for using Arc Memory in your environment. Following these guidelines will help ensure that your sensitive data and credentials remain secure.

## Table of Contents

1. [Token Storage and Permissions](#token-storage-and-permissions)
2. [Database Security](#database-security)
3. [Input Validation](#input-validation)
4. [Export Security](#export-security)
5. [Network Security](#network-security)
6. [Dependency Security](#dependency-security)
7. [Security Best Practices](#security-best-practices)

## Token Storage and Permissions

Arc Memory requires access tokens for GitHub and Linear (optional) to build a comprehensive knowledge graph. Here are best practices for managing these tokens:

### GitHub Token Recommendations

1. **Use Fine-Grained Personal Access Tokens (PATs)**: Create a token with only the permissions needed:
   - `repo` (for private repositories)
   - `read:user` (for user information)
   - `read:org` (if accessing organization repositories)

2. **Scope Limitations**: Limit the token to only the repositories you need to analyze.

3. **Token Expiration**: Set an expiration date for your token (e.g., 30-90 days) and rotate regularly.

4. **Token Storage**: Arc Memory uses your system's secure credential storage (keyring) to store tokens. Never store tokens in plain text files or environment variables.

Example of creating a properly scoped GitHub token:

```bash
# Store a GitHub token with appropriate scopes
arc auth github --token <your-token>
```

### Linear Token Recommendations

1. **API Key Permissions**: Create a read-only API key with the minimum necessary permissions:
   - `Read issues`
   - `Read teams`
   - `Read projects`

2. **Token Rotation**: Regularly rotate your Linear API key.

3. **Token Storage**: As with GitHub tokens, Linear tokens are stored in your system's secure credential storage.

Example of creating a properly scoped Linear token:

```bash
# Store a Linear token with appropriate scopes
arc auth linear --token <your-token>
```

### Token Validation

Arc Memory validates token permissions when you authenticate. If your token lacks necessary permissions, you'll receive a specific error message indicating which permissions are missing.

## Database Security

Arc Memory stores its knowledge graph in a local SQLite database by default. Here are recommendations for securing this database:

1. **File Permissions**: Ensure the database file has appropriate permissions:
   ```bash
   # Set restrictive permissions on the database file
   chmod 600 ~/.arc/graph.db
   ```

2. **Backup Security**: If you back up the database, ensure the backups are also secured with appropriate permissions.

3. **Database Location**: The default location is `~/.arc/graph.db`. You can specify a custom location with:
   ```bash
   # Use a custom database location
   arc build --db-path /secure/location/graph.db
   ```

4. **Database Encryption**: For highly sensitive environments, consider using an encrypted filesystem for the directory containing the database.

5. **Neo4j Security**: If using Neo4j instead of SQLite:
   - Use strong passwords
   - Enable TLS/SSL
   - Use Neo4j's role-based access control
   - Configure Neo4j to only listen on localhost if not needed remotely

## Input Validation

Arc Memory performs validation on inputs to prevent security issues:

1. **File Path Validation**: All file paths are validated to prevent path traversal attacks.

2. **Query Sanitization**: Natural language queries are sanitized before being used in database queries.

3. **Component ID Validation**: Component IDs are validated to ensure they match the expected format.

4. **Export Path Validation**: Export paths are validated to prevent writing to unauthorized locations.

When using the SDK, you should also validate inputs before passing them to Arc Memory methods:

```python
import os
from pathlib import Path
from arc_memory import Arc

# Validate file paths
def validate_path(path_str):
    path = Path(path_str)
    # Check for path traversal attempts
    if ".." in path.parts:
        raise ValueError("Path traversal detected")
    # Check if path is within allowed directories
    if not path.is_relative_to(Path("./src")):
        raise ValueError("Path must be within src directory")
    return path

# Use validated path
try:
    file_path = validate_path(user_input)
    arc = Arc(repo_path="./")
    decision_trail = arc.get_decision_trail(file_path=str(file_path), line_number=42)
except ValueError as e:
    print(f"Invalid input: {e}")
```

## Export Security

When exporting knowledge graphs, consider these security measures:

1. **Signing Exports**: Use GPG signing to verify the integrity of exported files:
   ```bash
   # Export with signing
   arc export <commit-sha> export.json --sign --key-id <your-gpg-key-id>
   ```

2. **Compression**: Use compression to reduce the size of exported files and make them harder to read without proper tools:
   ```bash
   # Export with compression
   arc export <commit-sha> export.json --compress
   ```

3. **Export Filtering**: Only export the minimum necessary data:
   ```bash
   # Export with filtering
   arc export <commit-sha> export.json --max-hops 2
   ```

4. **Export Permissions**: Set appropriate file permissions on exported files:
   ```bash
   # Set restrictive permissions on exported files
   chmod 600 export.json
   ```

## Network Security

Arc Memory primarily operates locally, but it does make API calls to GitHub and Linear:

1. **HTTPS Only**: All API calls use HTTPS with certificate validation.

2. **Rate Limiting**: Arc Memory respects API rate limits and implements exponential backoff.

3. **Proxy Support**: If you're behind a corporate proxy, configure it in your environment:
   ```bash
   # Configure proxy
   export HTTPS_PROXY=https://proxy.example.com:8080
   ```

4. **Firewall Rules**: If using a firewall, allow outbound connections to:
   - `api.github.com` (for GitHub API)
   - `api.linear.app` (for Linear API)

## Dependency Security

Arc Memory has dependencies that should be kept up to date:

1. **Regular Updates**: Keep Arc Memory and its dependencies updated:
   ```bash
   pip install --upgrade arc-memory
   ```

2. **Dependency Scanning**: Consider using tools like `safety` or `pip-audit` to scan for vulnerabilities:
   ```bash
   pip install safety
   safety check
   ```

3. **Minimal Installation**: If you don't need all features, install only what you need:
   ```bash
   # Install with minimal dependencies
   pip install arc-memory
   
   # Install with specific optional dependencies
   pip install arc-memory[cli]
   ```

## Security Best Practices

General security best practices when using Arc Memory:

1. **Principle of Least Privilege**: Use tokens with the minimum necessary permissions.

2. **Regular Auditing**: Regularly audit who has access to tokens and databases.

3. **Secure Environment**: Run Arc Memory in a secure environment with up-to-date software.

4. **Data Minimization**: Only build knowledge graphs for repositories you need to analyze.

5. **Secure Configuration**: Keep configuration files with sensitive information secure.

6. **Error Handling**: Handle errors securely without exposing sensitive information.

7. **Logging**: Configure logging to avoid recording sensitive information.

8. **CI/CD Security**: If using Arc Memory in CI/CD pipelines, use secure environment variables and secrets management.

Example of secure CI/CD configuration (GitHub Actions):

```yaml
name: Arc Memory Analysis

on:
  pull_request:
    branches: [ main ]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install arc-memory
      
      - name: Run Arc Memory analysis
        env:
          GITHUB_TOKEN: ${{ secrets.ARC_GITHUB_TOKEN }}
        run: |
          arc auth github --token "$GITHUB_TOKEN"
          arc build --github
          arc export ${{ github.event.pull_request.head.sha }} export.json --compress
```

## Reporting Security Issues

If you discover a security vulnerability in Arc Memory, please report it by emailing [security@arc.computer](mailto:security@arc.computer). Please do not report security vulnerabilities through public GitHub issues.

---

By following these security guidelines, you can use Arc Memory safely and securely in your environment. If you have any questions or need further assistance, please contact [support@arc.computer](mailto:support@arc.computer).
