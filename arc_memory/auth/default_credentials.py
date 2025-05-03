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

# Default Linear OAuth Client ID for the Arc organizational account
# This is embedded in the package to allow users to authenticate directly
# from the CLI without needing to provide their own OAuth credentials.
#
# This client ID is for the Arc Memory Linear OAuth App, which is configured
# for the standard OAuth 2.0 flow with a redirect URI.
# The Client Secret is required but not stored here for security reasons.
DEFAULT_LINEAR_CLIENT_ID = "abfe4960313bddfa75a59c37687aca0e"
