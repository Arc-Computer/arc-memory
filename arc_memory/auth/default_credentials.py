"""Default credentials for Arc Memory authentication.

This module contains the default Client ID for the Arc Memory GitHub OAuth app.
This is used when no other Client ID is provided.

Following GitHub's best practices for CLI applications, we only embed the Client ID,
which is considered public information. The Client Secret is not required for the
Device Flow authentication used by CLI applications.
"""

# Default GitHub OAuth Client ID for the Arc organizational account
# This is embedded in the package to allow users to authenticate directly
# from the CLI without needing to provide their own OAuth credentials.
#
# This client ID is for the Arc Memory GitHub OAuth App, which is configured
# for the Device Flow authentication method used by CLI applications.
# The Client Secret is not required for Device Flow and is not stored here.
DEFAULT_GITHUB_CLIENT_ID = "Iv23liNmVnxkNuRfG8tr"
