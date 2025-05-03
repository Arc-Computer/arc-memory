# Linear OAuth Troubleshooting Guide

This guide helps you troubleshoot common issues with Linear OAuth authentication in Arc Memory.

## Common Issues

### Authentication Fails with "Port Already in Use"

**Symptoms:**
- Error message: "Failed to start callback server on localhost:3000: [Errno 48] Address already in use"
- Authentication process stops immediately

**Causes:**
- Another application is using port 3000
- A previous instance of Arc Memory is still running
- A web server or development environment is running on port 3000

**Solutions:**
1. Close any applications that might be using port 3000
2. Check for running processes using port 3000:
   ```bash
   # On macOS/Linux
   lsof -i :3000
   
   # On Windows
   netstat -ano | findstr :3000
   ```
3. Kill the process using port 3000:
   ```bash
   # On macOS/Linux
   kill -9 <PID>
   
   # On Windows
   taskkill /PID <PID> /F
   ```
4. Try again after ensuring port 3000 is free

### Browser Doesn't Open Automatically

**Symptoms:**
- No browser window opens during authentication
- CLI shows a message about opening a browser

**Causes:**
- Default browser is not configured
- Browser is not available
- Operating system restrictions

**Solutions:**
1. Look for a URL in the console output
2. Manually copy and paste the URL into your browser
3. Make sure you're logged into Linear in your browser
4. Complete the authentication process in the browser

### Authentication Fails with "Invalid Request"

**Symptoms:**
- Error message: "Invalid request: content must be application/x-www-form-urlencoded"
- Authentication process fails after browser authentication

**Causes:**
- Incorrect content type in token exchange request
- Misconfigured Linear OAuth application

**Solutions:**
1. Run with debug logging: `arc auth linear --debug`
2. Check the debug logs for detailed error messages
3. Verify that your Linear OAuth application is configured correctly
4. Try again with the default Arc Memory Linear OAuth app

### Authentication Fails with "Invalid Client"

**Symptoms:**
- Error message: "Invalid client: client_id or client_secret is invalid"
- Authentication process fails after browser authentication

**Causes:**
- Incorrect client ID or client secret
- Misconfigured Linear OAuth application

**Solutions:**
1. Verify that your client ID and client secret are correct
2. Check that your Linear OAuth application is active
3. Try again with the default Arc Memory Linear OAuth app

### Authentication Fails with "Invalid Redirect URI"

**Symptoms:**
- Error message: "Invalid redirect URI"
- Authentication process fails after browser authentication

**Causes:**
- Redirect URI in the request doesn't match the one configured in Linear
- Misconfigured Linear OAuth application

**Solutions:**
1. Verify that your redirect URI matches the one configured in Linear
2. Check that your Linear OAuth application has the correct redirect URI
3. Try again with the default Arc Memory Linear OAuth app

### Authentication Succeeds but Data Ingestion Fails

**Symptoms:**
- Authentication completes successfully
- `arc build` command fails with Linear API errors
- No Linear data in the knowledge graph

**Causes:**
- Insufficient permissions granted during OAuth flow
- Token is valid but doesn't have the required scopes
- Linear API rate limiting

**Solutions:**
1. Re-authenticate with Linear: `arc auth linear`
2. Make sure you grant all requested permissions during the OAuth flow
3. Check the Linear API status and rate limits
4. Run with debug logging: `arc build --debug`

### Token Expiration Issues

**Symptoms:**
- Authentication worked previously but now fails
- Error message about expired token

**Causes:**
- Linear OAuth token has expired (unlikely as they last 10 years by default)
- Token has been revoked in Linear

**Solutions:**
1. Re-authenticate with Linear: `arc auth linear`
2. Check if you've revoked the token in Linear settings
3. Verify that your Linear account is active

## Advanced Troubleshooting

### Checking Token Status

You can check the status of your Linear OAuth token:

```bash
# Run the doctor command
arc doctor

# Look for Linear token information
# It should show if a token is configured and valid
```

### Manual Token Verification

To manually verify your Linear token:

```bash
# Create a simple test script
cat > test_linear_token.py << 'EOF'
import requests
import sys

# Replace with your token
token = sys.argv[1] if len(sys.argv) > 1 else None

if not token:
    print("Please provide a token as an argument")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.linear.app/graphql",
    headers=headers,
    json={
        "query": """
        query {
          viewer {
            id
            name
            email
          }
        }
        """
    }
)

print(f"Status code: {response.status_code}")
print(response.json())
EOF

# Run the script with your token
python test_linear_token.py YOUR_TOKEN
```

### Debugging Network Issues

If you suspect network issues:

```bash
# Check connectivity to Linear API
curl -I https://api.linear.app/graphql

# Check DNS resolution
nslookup linear.app

# Check for firewall or proxy issues
traceroute linear.app
```

### Clearing Stored Tokens

If you need to start fresh:

```bash
# On macOS
security delete-generic-password -s arc-memory -a linear-oauth-token

# On Windows
cmdkey /delete:arc-memory

# On Linux (depends on keyring implementation)
# For example, with libsecret:
secret-tool clear service arc-memory user linear-oauth-token
```

## Getting Help

If you're still experiencing issues:

1. Run with debug logging: `arc auth linear --debug`
2. Capture the full output (removing any sensitive information)
3. Check the [Linear API Status](https://status.linear.app/)
4. Contact the Arc Memory team with the debug output and a description of the issue
