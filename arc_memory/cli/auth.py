"""Authentication commands for Arc Memory CLI."""

import os
import sys
from typing import Optional

import typer
from rich.console import Console

from arc_memory.auth.default_credentials import (
    DEFAULT_GITHUB_CLIENT_ID,
    DEFAULT_LINEAR_CLIENT_ID,
    DEFAULT_LINEAR_CLIENT_SECRET,
)
from arc_memory.auth.github import (
    GitHubAppConfig,
    get_github_app_config_from_env,
    get_github_app_config_from_keyring,
    get_token_from_env as get_github_token_from_env,
    get_token_from_keyring as get_github_token_from_keyring,
    poll_device_flow as poll_github_device_flow,
    start_device_flow as start_github_device_flow,
    store_github_app_config_in_keyring,
    store_token_in_keyring as store_github_token_in_keyring,
)
from arc_memory.auth.linear import (
    LinearAppConfig,
    get_token_from_env as get_linear_token_from_env,
    get_token_from_keyring as get_linear_token_from_keyring,
    poll_device_flow as poll_linear_device_flow,
    start_device_flow as start_linear_device_flow,
    start_oauth_flow,
    store_token_in_keyring as store_linear_token_in_keyring,
    validate_client_id as validate_linear_client_id,
)
from arc_memory.errors import GitHubAuthError, LinearAuthError
from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.telemetry import track_cli_command

app = typer.Typer(help="Authentication commands")
console = Console()
logger = get_logger(__name__)


@app.callback()
def callback() -> None:
    """Authentication commands for Arc Memory."""
    configure_logging(debug=is_debug_mode())


@app.command("gh")
def github_auth(
    client_id: str = typer.Option(
        None, help="GitHub OAuth client ID. If not provided, uses the default Arc Memory app."
    ),
    timeout: int = typer.Option(
        300, help="Timeout in seconds for the device flow."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Authenticate with GitHub using device flow.

    This command uses GitHub's Device Flow, which is the recommended approach for CLI applications.
    It will display a code and URL for you to visit in your browser to complete authentication.
    """
    configure_logging(debug=debug)

    # Track command usage (don't include client_id in telemetry)
    track_cli_command("auth", subcommand="gh", args={"timeout": timeout, "debug": debug})

    # Check if we already have a token
    env_token = get_github_token_from_env()
    if env_token:
        console.print(
            "[green]GitHub token found in environment variables.[/green]"
        )
        if typer.confirm("Do you want to store this token in the system keyring?"):
            if store_github_token_in_keyring(env_token):
                console.print(
                    "[green]Token stored in system keyring.[/green]"
                )
            else:
                console.print(
                    "[yellow]Failed to store token in system keyring. "
                    "You can still use the token from environment variables.[/yellow]"
                )
        return

    keyring_token = get_github_token_from_keyring()
    if keyring_token:
        console.print(
            "[green]GitHub token found in system keyring.[/green]"
        )
        if typer.confirm("Do you want to use this token?"):
            console.print(
                "[green]Using existing token from system keyring.[/green]"
            )
            return

    # Use default Arc Memory app if client ID not provided
    if not client_id:
        # First try environment variables (for development or custom overrides)
        env_client_id = os.environ.get("ARC_GITHUB_CLIENT_ID")

        if env_client_id:
            logger.debug("Using GitHub OAuth Client ID from environment variables")
            client_id = env_client_id
        else:
            # Use the default embedded Client ID
            logger.debug("Using default embedded GitHub OAuth Client ID")
            client_id = DEFAULT_GITHUB_CLIENT_ID

            # Validate the client ID format
            from arc_memory.auth.github import validate_client_id
            if not validate_client_id(client_id):
                console.print(
                    "[yellow]Warning: The GitHub OAuth Client ID may not be valid.[/yellow]"
                )
                console.print(
                    "If authentication fails, you can provide your own Client ID with --client-id,"
                )
                console.print(
                    "or set the ARC_GITHUB_CLIENT_ID environment variable."
                )
                if not typer.confirm("Do you want to continue with this Client ID?"):
                    sys.exit(1)

            console.print(
                "[green]Using Arc Memory's GitHub OAuth app for authentication.[/green]"
            )

    try:
        # Start device flow (only requires Client ID)
        device_code, verification_uri, interval = start_github_device_flow(client_id)

        console.print(
            f"[bold blue]Please visit: [link={verification_uri}]{verification_uri}[/link][/bold blue]"
        )
        console.print(
            f"[bold]And enter the code: [green]{device_code}[/green][/bold]"
        )

        # Poll for token (Client Secret not required for Device Flow)
        token = poll_github_device_flow(
            client_id, device_code, interval, timeout
        )

        # Store token in keyring
        if store_github_token_in_keyring(token):
            console.print(
                "[green]Authentication successful! Token stored in system keyring.[/green]"
            )
            # Track successful authentication
            track_cli_command("auth", subcommand="gh", success=True)
        else:
            console.print(
                "[yellow]Authentication successful, but failed to store token in system keyring.[/yellow]"
            )
            console.print(
                f"Your token is: {token}"
            )
            console.print(
                "You can set this as an environment variable: export GITHUB_TOKEN=<token>"
            )
            # Track partial success
            track_cli_command("auth", subcommand="gh",
                             args={"keyring_error": True}, success=True)
    except GitHubAuthError as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        # Track authentication failure
        track_cli_command("auth", subcommand="gh", success=False, error=e)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during authentication")
        console.print(f"[red]Unexpected error: {e}[/red]")
        # Track unexpected error
        track_cli_command("auth", subcommand="gh", success=False, error=e)
        sys.exit(1)


@app.command("gh-app")
def github_app_auth(
    app_id: str = typer.Option(
        None, "--app-id", help="GitHub App ID."
    ),
    private_key_path: str = typer.Option(
        None, "--private-key", help="Path to the GitHub App private key file."
    ),
    client_id: str = typer.Option(
        None, "--client-id", help="GitHub OAuth client ID for the GitHub App."
    ),
    client_secret: str = typer.Option(
        None, "--client-secret", help="GitHub OAuth client secret for the GitHub App."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Configure GitHub App authentication.

    This command stores GitHub App credentials in the system keyring.
    These credentials are used to generate installation tokens for repositories
    where the GitHub App is installed.
    """
    configure_logging(debug=debug)

    # Track command usage (don't include any credentials in telemetry)
    track_cli_command("auth", subcommand="gh-app", args={"debug": debug})

    # Check if we already have GitHub App config from environment
    env_config = get_github_app_config_from_env()
    if env_config:
        console.print(
            "[green]GitHub App configuration found in environment variables.[/green]"
        )
        if typer.confirm("Do you want to store this configuration in the system keyring?"):
            if store_github_app_config_in_keyring(env_config):
                console.print(
                    "[green]GitHub App configuration stored in system keyring.[/green]"
                )
            else:
                console.print(
                    "[yellow]Failed to store GitHub App configuration in system keyring. "
                    "You can still use the configuration from environment variables.[/yellow]"
                )
        return

    # Check if we already have GitHub App config in keyring
    keyring_config = get_github_app_config_from_keyring()
    if keyring_config:
        console.print(
            "[green]GitHub App configuration found in system keyring.[/green]"
        )
        if typer.confirm("Do you want to use this configuration?"):
            console.print(
                "[green]Using existing GitHub App configuration from system keyring.[/green]"
            )
            return

    # Check if all required parameters are provided
    if not app_id or not private_key_path or not client_id or not client_secret:
        console.print(
            "[red]Missing required parameters for GitHub App configuration.[/red]"
        )
        console.print(
            "Please provide --app-id, --private-key, --client-id, and --client-secret."
        )
        sys.exit(1)

    # Read private key from file
    try:
        with open(private_key_path, "r") as f:
            private_key = f.read()
    except Exception as e:
        console.print(f"[red]Failed to read private key file: {e}[/red]")
        sys.exit(1)

    # Create and store GitHub App config
    try:
        config = GitHubAppConfig(
            app_id=app_id,
            private_key=private_key,
            client_id=client_id,
            client_secret=client_secret
        )

        if store_github_app_config_in_keyring(config):
            console.print(
                "[green]GitHub App configuration stored in system keyring.[/green]"
            )
            console.print(
                "[green]You can now use GitHub App installation tokens for repositories where the app is installed.[/green]"
            )
            # Track successful configuration
            track_cli_command("auth", subcommand="gh-app", success=True)
        else:
            console.print(
                "[red]Failed to store GitHub App configuration in system keyring.[/red]"
            )
            # Track failure
            track_cli_command("auth", subcommand="gh-app",
                             success=False, error=RuntimeError("Failed to store in keyring"))
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to create GitHub App configuration: {e}[/red]")
        # Track error
        track_cli_command("auth", subcommand="gh-app", success=False, error=e)
        sys.exit(1)


# The github_auth implementation is now directly in the function body


@app.command("linear")
def linear_auth(
    client_id: str = typer.Option(
        None, help="Linear OAuth client ID. Only needed for custom OAuth apps."
    ),
    client_secret: str = typer.Option(
        None, help="Linear OAuth client secret. Only needed for custom OAuth apps."
    ),
    use_api_key: bool = typer.Option(
        False, "--api-key", help="Use API key authentication instead of OAuth."
    ),
    timeout: int = typer.Option(
        300, help="Timeout in seconds for the authentication flow."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Authenticate with Linear.

    By default, this command uses Linear's OAuth 2.0 flow, which will open a browser
    for you to authenticate with Linear. If you prefer to use an API key, you can
    use the --api-key flag.
    """
    configure_logging(debug=debug)

    # Track command usage (don't include client_id in telemetry)
    track_cli_command("auth", subcommand="linear", args={"timeout": timeout, "debug": debug, "use_api_key": use_api_key})

    # Check if we already have a token
    env_token = get_linear_token_from_env()
    if env_token:
        console.print(
            "[green]Linear token found in environment variables.[/green]"
        )
        if typer.confirm("Do you want to store this token in the system keyring?"):
            if store_linear_token_in_keyring(env_token):
                console.print(
                    "[green]Token stored in system keyring.[/green]"
                )
            else:
                console.print(
                    "[yellow]Failed to store token in system keyring. "
                    "You can still use the token from environment variables.[/yellow]"
                )
        return

    keyring_token = get_linear_token_from_keyring()
    if keyring_token:
        console.print(
            "[green]Linear token found in system keyring.[/green]"
        )
        if typer.confirm("Do you want to use this token?"):
            console.print(
                "[green]Using existing token from system keyring.[/green]"
            )
            return

    # Use default Arc Memory app if client ID not provided
    if not client_id:
        # First try environment variables (for development or custom overrides)
        env_client_id = os.environ.get("ARC_LINEAR_CLIENT_ID")

        if env_client_id:
            logger.debug("Using Linear OAuth Client ID from environment variables")
            client_id = env_client_id
        else:
            # Use the default embedded Client ID
            logger.debug("Using default embedded Linear OAuth Client ID")
            client_id = DEFAULT_LINEAR_CLIENT_ID

            # Validate the client ID format
            if not validate_linear_client_id(client_id):
                console.print(
                    "[yellow]Warning: The Linear OAuth Client ID may not be valid.[/yellow]"
                )
                console.print(
                    "If authentication fails, you can provide your own Client ID with --client-id,"
                )
                console.print(
                    "or set the ARC_LINEAR_CLIENT_ID environment variable."
                )
                if not typer.confirm("Do you want to continue with this Client ID?"):
                    sys.exit(1)

            console.print(
                "[green]Using Arc Memory's Linear OAuth app for authentication.[/green]"
            )

    # Use default client secret if not provided
    if not client_secret:
        # First try environment variables (for development or custom overrides)
        env_client_secret = os.environ.get("ARC_LINEAR_CLIENT_SECRET")

        if env_client_secret:
            logger.debug("Using Linear OAuth Client Secret from environment variables")
            client_secret = env_client_secret
        else:
            # Use the default embedded Client Secret
            logger.debug("Using default embedded Linear OAuth Client Secret")
            client_secret = DEFAULT_LINEAR_CLIENT_SECRET

    try:
        if use_api_key:
            # API Key authentication (Device Flow)
            if not client_secret:
                console.print(
                    "[red]Missing required parameter for Linear API key authentication.[/red]"
                )
                console.print(
                    "Please provide --client-secret."
                )
                console.print(
                    "You can create an API key in your Linear account settings under Developer > API > Personal API keys."
                )
                sys.exit(1)

            # Start device flow
            device_code, user_code, verification_uri, interval = start_linear_device_flow(client_id)

            console.print(
                f"[bold blue]Please visit: [link={verification_uri}]{verification_uri}[/link][/bold blue]"
            )
            console.print(
                f"[bold]And enter the code: [green]{user_code}[/green][/bold]"
            )

            # Poll for token
            token = poll_linear_device_flow(
                client_id, client_secret, device_code, interval, timeout
            )
        else:
            # OAuth 2.0 authentication
            # Create app config
            config = LinearAppConfig(
                client_id=client_id,
                client_secret=client_secret,
            )

            # Start OAuth flow
            console.print(
                "[bold blue]Starting OAuth authentication flow...[/bold blue]"
            )
            console.print(
                "A local server will be started to receive the OAuth callback."
            )
            console.print(
                "A browser window will open for you to authenticate with Linear."
            )
            console.print(
                "[yellow]If the browser doesn't open automatically, check the console for a URL to open manually.[/yellow]"
            )

            # This will open a browser and wait for the callback
            try:
                oauth_token = start_oauth_flow(config, timeout=timeout)

                # Use the access token
                token = oauth_token.access_token

                console.print(
                    "[green]OAuth authentication successful![/green]"
                )
                console.print(
                    "You are now authenticated with Linear and can use Arc Memory with your Linear account."
                )
            except LinearAuthError as e:
                # Provide more user-friendly error messages
                if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    console.print(
                        "[red]Authentication timed out.[/red]"
                    )
                    console.print(
                        "The authentication flow took too long to complete. Please try again."
                    )
                elif "callback server" in str(e).lower():
                    console.print(
                        "[red]Failed to start local callback server.[/red]"
                    )
                    console.print(
                        "This may be because port 3000 is already in use. Try closing other applications that might be using this port."
                    )
                else:
                    console.print(
                        f"[red]Authentication failed: {e}[/red]"
                    )
                # Re-raise the exception to be caught by the outer try-except block
                raise

        # Store token in keyring
        if store_linear_token_in_keyring(token):
            console.print(
                "[green]Token stored in system keyring.[/green]"
            )
            # Track successful authentication
            track_cli_command("auth", subcommand="linear", success=True)
        else:
            console.print(
                "[yellow]Authentication successful, but failed to store token in system keyring.[/yellow]"
            )
            console.print(
                f"Your token is: {token}"
            )
            console.print(
                "You can set this as an environment variable: export LINEAR_API_KEY=<token>"
            )
            # Track partial success
            track_cli_command("auth", subcommand="linear",
                             args={"keyring_error": True}, success=True)
    except LinearAuthError as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        # Track authentication failure
        track_cli_command("auth", subcommand="linear", success=False, error=e)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during authentication")
        console.print(f"[red]Unexpected error: {e}[/red]")
        # Track unexpected error
        track_cli_command("auth", subcommand="linear", success=False, error=e)
        sys.exit(1)
