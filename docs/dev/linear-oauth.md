# Linear OAuth 2.0 Implementation

This document describes the implementation of Linear OAuth 2.0 authentication in Arc Memory.

## Overview

Arc Memory uses Linear's OAuth 2.0 flow for authentication, which allows users to authenticate with Linear without sharing their credentials with Arc Memory. The implementation follows the standard OAuth 2.0 Authorization Code flow, which is the recommended approach for applications that can securely store a client secret.

## Architecture

The Linear OAuth 2.0 implementation consists of the following components:

1. **OAuth Configuration**: Defined in `LinearAppConfig` class, which includes client ID, client secret, redirect URI, and scopes.
2. **OAuth Token**: Defined in `LinearOAuthToken` class, which includes access token, token type, expiration, and scope.
3. **OAuth Flow**: Implemented in `start_oauth_flow` function, which handles the complete OAuth 2.0 flow.
4. **Callback Server**: Implemented in `OAuthCallbackServer` class, which receives the authorization code from Linear.
5. **Token Exchange**: Implemented in `exchange_code_for_token` function, which exchanges the authorization code for an access token.
6. **Token Storage**: Implemented in `store_oauth_token_in_keyring` function, which securely stores the token in the system keyring.
7. **Token Retrieval**: Implemented in `get_oauth_token_from_keyring` function, which retrieves the token from the system keyring.
8. **Token Validation**: Implemented in `is_expired` method of `LinearOAuthToken` class, which checks if the token is expired.

## OAuth 2.0 Flow

The Linear OAuth 2.0 flow in Arc Memory follows these steps:

1. **Initialization**: The user runs `arc auth linear` command.
2. **Server Setup**: Arc Memory starts a local server on port 3000 to receive the callback.
3. **Authorization Request**: Arc Memory generates an authorization URL and opens the user's browser to that URL.
4. **User Authentication**: The user authenticates with Linear in their browser and grants permissions.
5. **Authorization Code**: Linear redirects back to the local server with an authorization code.
6. **Token Exchange**: Arc Memory exchanges the authorization code for an access token.
7. **Token Storage**: Arc Memory securely stores the token in the system keyring.

## Security Considerations

The implementation includes several security features:

1. **CSRF Protection**: Uses a secure state parameter to prevent cross-site request forgery attacks.
2. **Secure Storage**: Stores tokens in the system's secure keyring.
3. **Minimal Scope**: Requests only the necessary permissions from Linear.
4. **Token Validation**: Validates tokens before using them.
5. **Error Handling**: Provides clear error messages for authentication failures.
6. **Port Conflict Resolution**: Handles port conflicts gracefully.

## Default Credentials

Arc Memory includes default Linear OAuth credentials from the Arc-Computer organization, which allows users to authenticate without having to create their own Linear OAuth application. These credentials are stored in `arc_memory/auth/default_credentials.py`.

## Integration with Existing Code

The Linear OAuth implementation integrates with the existing code in several ways:

1. **LinearIngestor**: Updated to work with OAuth tokens.
2. **GraphQLClient**: Enhanced to support OAuth authentication.
3. **Token Refresh**: Implemented token refresh handling.
4. **Error Handling**: Added proper error handling for OAuth-specific errors.

## Testing

The Linear OAuth implementation includes comprehensive tests:

1. **Unit Tests**: Test individual components of the OAuth flow.
2. **Integration Tests**: Test the complete OAuth flow.
3. **Error Handling Tests**: Test error scenarios and edge cases.

## Troubleshooting

Common issues and their solutions:

1. **Port Conflicts**: If port 3000 is already in use, the authentication will fail. Close any applications that might be using port 3000 and try again.
2. **Browser Issues**: If the browser doesn't open automatically, check the console for a URL to open manually.
3. **Token Expiration**: Linear OAuth tokens have a very long expiration time (10 years by default). If your token expires, simply run `arc auth linear` again to get a new token.
4. **Permission Issues**: Ensure you grant all requested permissions during the OAuth flow. If you denied any permissions, you'll need to re-authenticate.

## Future Improvements

Potential future improvements to the Linear OAuth implementation:

1. **Refresh Token Support**: Implement refresh token support for long-lived sessions.
2. **Custom Port Selection**: Allow users to specify a custom port for the callback server.
3. **Silent Authentication**: Implement silent authentication for background processes.
4. **Multi-Account Support**: Support authentication with multiple Linear accounts.
5. **Token Revocation**: Implement token revocation for logout functionality.

## References

- [Linear OAuth 2.0 Documentation](https://linear.app/developers/oauth-2-0-authentication)
- [OAuth 2.0 Authorization Code Flow](https://oauth.net/2/grant-types/authorization-code/)
- [RFC 6749: The OAuth 2.0 Authorization Framework](https://tools.ietf.org/html/rfc6749)
