"""Serve command for Arc Memory CLI.

This command provides a simple wrapper around the MCP server.
"""

import importlib.util
import subprocess
import sys
from typing import Optional

import typer
from rich.console import Console

from arc_memory.config import get_config, update_config
from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.telemetry import track_command_usage

app = typer.Typer(help="Serve the knowledge graph via MCP protocol")
console = Console()
logger = get_logger(__name__)


@app.callback()
def callback() -> None:
    """Serve the knowledge graph via MCP protocol."""
    configure_logging(debug=is_debug_mode())


@app.command()
def start(
    host: str = typer.Option(
        None, "--host", help="Host to bind the server to (default: from config or 127.0.0.1)"
    ),
    port: Optional[int] = typer.Option(
        None, "--port", "-p", help="Port to bind the server to (default: from config or 8000)"
    ),
    stdio: bool = typer.Option(
        False, "--stdio", help="Use stdio mode instead of HTTP"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug mode"
    ),
    save_config: bool = typer.Option(
        False, "--save-config", help="Save the host and port to the configuration"
    ),
) -> None:
    """Serve the knowledge graph via MCP protocol.

    This command starts the MCP server, which provides access to the knowledge graph
    via the Model Context Protocol.

    Examples:
        arc serve start
        arc serve start --host 0.0.0.0 --port 8080
        arc serve start --stdio
    """
    configure_logging(debug=debug)

    # Get host and port from config if not provided
    config = get_config()
    host_to_use = host or config.get("mcp", {}).get("host", "127.0.0.1")
    port_to_use = port or config.get("mcp", {}).get("port", 8000)

    # Save to config if requested
    if save_config:
        update_config("mcp", "host", host_to_use)
        update_config("mcp", "port", port_to_use)
        console.print(f"[green]Saved MCP server configuration: {host_to_use}:{port_to_use}[/green]")

    # Track command usage
    context = {
        "host": host_to_use,
        "port": port_to_use,
        "stdio": stdio,
        "debug": debug
    }
    track_command_usage("serve_start", context=context)

    try:
        # Check if arc-mcp-server is installed
        has_mcp_server = importlib.util.find_spec("arc_mcp_server") is not None

        if not has_mcp_server:
            console.print("[yellow]arc-mcp-server not found. Installing...[/yellow]")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "arc-mcp-server"])

        # Build the command
        cmd = [sys.executable, "-m", "arc_mcp_server"]
        if host_to_use != "127.0.0.1":
            cmd.extend(["--host", host_to_use])
        if port_to_use != 8000:
            cmd.extend(["--port", str(port_to_use)])
        if stdio:
            cmd.append("--stdio")
        if debug:
            cmd.append("--debug")

        # Run the MCP server as a subprocess
        console.print(f"[green]Starting Arc MCP Server{'in stdio mode' if stdio else f' on {host_to_use}:{port_to_use}'}...[/green]")
        subprocess.run(cmd)

    except Exception as e:
        logger.exception("Error starting MCP server")
        console.print(f"[red]Error starting MCP server: {e}[/red]")
        
        # Track error
        track_command_usage("serve_start", success=False, error=e, context=context)
        sys.exit(1)


@app.command()
def status() -> None:
    """Check the status of the MCP server.

    This command checks if the MCP server is running and displays its configuration.

    Examples:
        arc serve status
    """
    # Track command usage
    track_command_usage("serve_status")

    try:
        # Get configuration
        config = get_config()
        host = config.get("mcp", {}).get("host", "127.0.0.1")
        port = config.get("mcp", {}).get("port", 8000)

        # Check if the server is running
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex((host, port))
        s.close()

        if result == 0:
            console.print(f"[green]MCP server is running on {host}:{port}[/green]")
        else:
            console.print(f"[yellow]MCP server is not running on {host}:{port}[/yellow]")
            console.print("Run [bold]arc serve start[/bold] to start the server.")

    except Exception as e:
        logger.exception("Error checking MCP server status")
        console.print(f"[red]Error checking MCP server status: {e}[/red]")
        
        # Track error
        track_command_usage("serve_status", success=False, error=e)
        sys.exit(1)
