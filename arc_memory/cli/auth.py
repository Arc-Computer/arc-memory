"""Authentication commands for Arc Memory CLI."""

import os
import sys
from typing import Optional

import typer
from rich.console import Console

from arc_memory.auth.default_credentials import DEFAULT_GITHUB_CLIENT_ID
from arc_memory.auth.github import (
    GitHubAppConfig,
    get_github_app_config_from_env,
    get_github_app_config_from_keyring,
    get_token_from_env,
    get_token_from_keyring,
    poll_device_flow,
    start_device_flow,
    store_github_app_config_in_keyring,
    store_token_in_keyring,
)
from arc_memory.errors import GitHubAuthError
from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode

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

    # Check if we already have a token
    env_token = get_token_from_env()
    if env_token:
        console.print(
            "[green]GitHub token found in environment variables.[/green]"
        )
        if typer.confirm("Do you want to store this token in the system keyring?"):
            if store_token_in_keyring(env_token):
                console.print(
                    "[green]Token stored in system keyring.[/green]"
                )
            else:
                console.print(
                    "[yellow]Failed to store token in system keyring. "
                    "You can still use the token from environment variables.[/yellow]"
                )
        return

    keyring_token = get_token_from_keyring()
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

            # Verify that the default Client ID is valid (not a placeholder value)
            if client_id == "YOUR_CLIENT_ID":
                console.print(
                    "[red]Default GitHub OAuth Client ID is not configured.[/red]"
                )
                console.print(
                    "Please provide a Client ID with --client-id,"
                )
                console.print(
                    "or set the ARC_GITHUB_CLIENT_ID environment variable."
                )
                sys.exit(1)
            else:
                # Validate the client ID format
                from arc_memory.auth.github import validate_client_id
                if not validate_client_id(client_id):
                    console.print(
                        "[yellow]Warning: The default GitHub OAuth Client ID may not be valid.[/yellow]"
                    )
                    console.print(
                        "If authentication fails, you can provide your own Client ID with --client-id,"
                    )
                    console.print(
                        "or set the ARC_GITHUB_CLIENT_ID environment variable."
                    )
                    if not typer.confirm("Do you want to continue with the default Client ID?"):
                        sys.exit(1)

                console.print(
                    "[green]Using Arc Memory's GitHub OAuth app for authentication.[/green]"
                )

    try:
        # Start device flow (only requires Client ID)
        device_code, verification_uri, interval = start_device_flow(client_id)

        console.print(
            f"[bold blue]Please visit: [link={verification_uri}]{verification_uri}[/link][/bold blue]"
        )
        console.print(
            f"[bold]And enter the code: [green]{device_code}[/green][/bold]"
        )

        # Poll for token (Client Secret not required for Device Flow)
        token = poll_device_flow(
            client_id, device_code, interval, timeout
        )

        # Store token in keyring
        if store_token_in_keyring(token):
            console.print(
                "[green]Authentication successful! Token stored in system keyring.[/green]"
            )
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
    except GitHubAuthError as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during authentication")
        console.print(f"[red]Unexpected error: {e}[/red]")
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
        else:
            console.print(
                "[red]Failed to store GitHub App configuration in system keyring.[/red]"
            )
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to create GitHub App configuration: {e}[/red]")
        sys.exit(1)


# The github_auth implementation is now directly in the function body
