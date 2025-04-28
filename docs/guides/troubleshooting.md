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

## GitHub Integration Issues

### Authentication Failures

**Symptom**: GitHub API errors or rate limiting.

**Solution**:
1. Authenticate with GitHub:
   ```bash
   arc auth gh
   ```

2. Check your authentication status:
   ```bash
   arc auth status
   ```

3. If you're hitting rate limits, use a personal access token:
   ```bash
   arc auth gh --token YOUR_TOKEN
   ```

4. For CI/CD environments, use a GitHub App:
   ```bash
   arc auth gh-app --app-id APP_ID --private-key path/to/private-key.pem
   ```

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

3. Enable debug logging to see plugin discovery details:
   ```bash
   arc build --debug
   ```

### Plugin Errors

**Symptom**: Errors during plugin execution.

**Solution**:
1. Check the error message for details.

2. Enable debug logging:
   ```bash
   arc build --debug
   ```

3. Test your plugin in isolation:
   ```python
   from your_package.module import YourPluginClass
   plugin = YourPluginClass()
   nodes, edges, metadata = plugin.ingest()
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
