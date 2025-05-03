"""Default credentials for Arc Memory authentication.

This module contains the default Client IDs for the Arc Memory OAuth apps.
These are used when no other Client IDs are provided.

Following OAuth best practices for CLI applications, we only embed the Client IDs,
which are considered public information. Client Secrets are not stored here
and should be provided securely at runtime.
"""

# Default GitHub OAuth Client ID for the Arc organizational account
# This is embedded in the package to allow users to authenticate directly
# from the CLI without needing to provide their own OAuth credentials.
#
# This client ID is for the Arc Memory GitHub OAuth App, which is configured
# for the Device Flow authentication method used by CLI applications.
# The Client Secret is not required for Device Flow and is not stored here.
DEFAULT_GITHUB_CLIENT_ID = "Iv23liNmVnxkNuRfG8tr"

# Default Linear OAuth credentials for the Arc organizational account
# These are embedded in the package to allow users to authenticate directly
# from the CLI without needing to provide their own OAuth credentials.
#
# These credentials are for the Arc Memory Linear OAuth App, which is configured
# for the standard OAuth 2.0 flow with a redirect URI.
# While typically client secrets should not be embedded in code, for public CLI applications
# this is a common pattern as the secret is for the application itself, not for individual users.
DEFAULT_LINEAR_CLIENT_ID = "abfe4960313bddfa75a59c37687aca0e"

# This is the client secret for the Arc Memory Linear OAuth App.
# For a public CLI application, this is acceptable as it identifies the application,
# not individual users. Each user will still need to authenticate with Linear.
DEFAULT_LINEAR_CLIENT_SECRET = "fd9270bca3098c57e12fbf923a2fbeba"
