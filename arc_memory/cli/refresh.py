"""Refresh command for Arc Memory CLI.

This command provides functionality for refreshing the knowledge graph with the latest data
from various sources, either manually or automatically on a schedule.
"""

import sys
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from arc_memory.auto_refresh.core import refresh_all_sources
from arc_memory.config import get_config, update_config
from arc_memory.db.metadata import get_all_refresh_timestamps
from arc_memory.errors import AutoRefreshError
from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.scheduler import (
    get_refresh_schedule,
    schedule_refresh,
    unschedule_refresh,
    is_refresh_scheduled,
)
from arc_memory.telemetry import track_cli_command

app = typer.Typer(help="Refresh the knowledge graph with the latest data")
console = Console()
logger = get_logger(__name__)


class Source(str, Enum):
    """Available sources for refresh."""
    GITHUB = "github"
    LINEAR = "linear"
    ADR = "adr"
    ALL = "all"


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    source: Optional[Source] = typer.Option(
        None, "--source", "-s", help="Source to refresh (github, linear, adr, or all)."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force refresh even if not needed."
    ),
    silent: bool = typer.Option(
        False, "--silent", help="Suppress output (useful for scheduled tasks)."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Refresh the knowledge graph with the latest data from various sources.

    This command refreshes the knowledge graph with the latest data from GitHub, Linear,
    and ADRs. By default, it only refreshes sources that need refreshing based on their
    last refresh time.

    Examples:
        arc refresh
        arc refresh --source github
        arc refresh --force
        arc refresh --silent
    """
    configure_logging(debug=debug or is_debug_mode())

    # If a subcommand was invoked, don't run the default command
    if ctx.invoked_subcommand is not None:
        return

    # Track command usage
    track_cli_command("refresh", args={
        "source": source.value if source else "auto",
        "force": force,
        "silent": silent,
        "debug": debug,
    })

    try:
        # Ensure the database is connected and initialized
        from arc_memory.db import get_adapter
        from arc_memory.sql.db import get_db_path

        adapter = get_adapter()
        if not adapter.is_connected():
            db_path = get_db_path()
            adapter.connect({"db_path": str(db_path)})
            # Initialize the database schema to ensure tables exist
            adapter.init_db()

        # Determine which sources to refresh
        sources_to_refresh = None  # Default: auto-detect in refresh_all_sources
        if source is not None:
            if source == Source.ALL:
                # Refresh all sources explicitly
                sources_to_refresh = ["github", "linear", "adr"]
            elif source == Source.GITHUB:
                sources_to_refresh = ["github"]
            elif source == Source.LINEAR:
                sources_to_refresh = ["linear"]
            elif source == Source.ADR:
                sources_to_refresh = ["adr"]

        # Get the refresh interval from config
        config = get_config()
        refresh_interval_hours = config.get("refresh", {}).get("interval_hours", 24)
        min_interval = timedelta(hours=refresh_interval_hours)

        # Refresh the sources
        if not silent:
            console.print(f"\n🔄 [bold]Arc Memory Refresh[/bold]")
            console.print("===================")
            if source is not None:
                console.print(f"Refreshing source: [bold]{source.value}[/bold]")
            else:
                console.print("Refreshing sources that need updating")
            if force:
                console.print("[yellow]Force refresh enabled[/yellow]")

        results = refresh_all_sources(sources_to_refresh, force, min_interval)

        if not silent:
            # Print results
            console.print("\n[bold]Refresh Results:[/bold]")
            table = Table(show_header=True)
            table.add_column("Source")
            table.add_column("Status")

            for source_name, refreshed in results.items():
                status = "[green]Refreshed[/green]" if refreshed else "[yellow]Skipped[/yellow]"
                table.add_row(source_name, status)

            console.print(table)
            console.print("\n[green]✓ Refresh completed successfully[/green]")

    except AutoRefreshError as e:
        if not silent:
            console.print(f"\n[red]Error refreshing knowledge graph: {e}[/red]")
        logger.error(f"Error refreshing knowledge graph: {e}")
        sys.exit(1)


@app.command("status")
def status(
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Show the status of the auto-refresh feature.

    This command shows the last refresh time for each source and whether
    auto-refresh is scheduled.

    Examples:
        arc refresh status
    """
    configure_logging(debug=debug or is_debug_mode())

    # Track command usage
    track_cli_command("refresh", subcommand="status", args={"debug": debug})

    try:
        # Ensure the database is connected and initialized
        from arc_memory.db import get_adapter
        from arc_memory.sql.db import get_db_path

        adapter = get_adapter()
        if not adapter.is_connected():
            db_path = get_db_path()
            adapter.connect({"db_path": str(db_path)})
            # Initialize the database schema to ensure tables exist
            adapter.init_db()

        # Get the last refresh timestamps
        timestamps = get_all_refresh_timestamps()

        # Get the refresh schedule
        is_scheduled = is_refresh_scheduled()
        schedule = get_refresh_schedule() if is_scheduled else None

        # Get the refresh interval from config
        config = get_config()
        refresh_interval_hours = config.get("refresh", {}).get("interval_hours", 24)

        # Print status
        console.print("\n🔄 [bold]Arc Memory Refresh Status[/bold]")
        console.print("==========================")

        # Print last refresh times
        console.print("\n[bold]Last Refresh Times:[/bold]")
        table = Table(show_header=True)
        table.add_column("Source")
        table.add_column("Last Refresh")
        table.add_column("Status")

        now = datetime.now()
        min_interval = timedelta(hours=refresh_interval_hours)

        for source in ["github", "linear", "adr"]:
            last_refresh = timestamps.get(source)
            if last_refresh:
                time_since = now - last_refresh
                needs_refresh = time_since >= min_interval
                status = "[yellow]Needs refresh[/yellow]" if needs_refresh else "[green]Up to date[/green]"
                last_refresh_str = last_refresh.strftime("%Y-%m-%d %H:%M:%S")
                time_since_str = f"({time_since.days}d {time_since.seconds // 3600}h ago)"
                table.add_row(source, f"{last_refresh_str} {time_since_str}", status)
            else:
                table.add_row(source, "[grey]Never[/grey]", "[yellow]Needs refresh[/yellow]")

        console.print(table)

        # Print schedule status
        console.print("\n[bold]Auto-Refresh Schedule:[/bold]")
        if is_scheduled:
            console.print(f"[green]✓ Auto-refresh is scheduled[/green]")
            console.print(f"Interval: Every {refresh_interval_hours} hours")
            if schedule:
                console.print(f"Next run: {schedule.get('next_run', 'Unknown')}")
        else:
            console.print("[yellow]✗ Auto-refresh is not scheduled[/yellow]")
            console.print("Run 'arc refresh schedule' to set up auto-refresh")

    except Exception as e:
        console.print(f"\n[red]Error getting refresh status: {e}[/red]")
        logger.error(f"Error getting refresh status: {e}")
        sys.exit(1)


@app.command("schedule")
def schedule_command(
    interval_hours: int = typer.Option(
        24, "--interval", "-i", help="Refresh interval in hours."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Schedule automatic refreshes of the knowledge graph.

    This command sets up a scheduled task to automatically refresh the knowledge graph
    at the specified interval.

    Examples:
        arc refresh schedule
        arc refresh schedule --interval 12
    """
    configure_logging(debug=debug or is_debug_mode())

    # Track command usage
    track_cli_command("refresh", subcommand="schedule", args={
        "interval_hours": interval_hours,
        "debug": debug,
    })

    try:
        # Ensure the database is connected and initialized
        from arc_memory.db import get_adapter
        from arc_memory.sql.db import get_db_path

        adapter = get_adapter()
        if not adapter.is_connected():
            db_path = get_db_path()
            adapter.connect({"db_path": str(db_path)})
            # Initialize the database schema to ensure tables exist
            adapter.init_db()

        # Update the refresh interval in the config
        update_config("refresh", "interval_hours", interval_hours)

        # Schedule the refresh
        success = schedule_refresh(interval_hours)

        if success:
            console.print(f"\n[green]✓ Auto-refresh scheduled successfully (every {interval_hours} hours)[/green]")
            console.print("The knowledge graph will be automatically refreshed at the specified interval.")
        else:
            console.print("\n[yellow]⚠ Auto-refresh scheduling partially succeeded[/yellow]")
            console.print("The configuration was updated, but the system scheduler could not be set up.")
            console.print("You may need to set up the scheduler manually. See the documentation for details.")

    except Exception as e:
        console.print(f"\n[red]Error scheduling auto-refresh: {e}[/red]")
        logger.error(f"Error scheduling auto-refresh: {e}")
        sys.exit(1)


@app.command("unschedule")
def unschedule_command(
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Remove the scheduled auto-refresh task.

    This command removes the scheduled task for auto-refreshing the knowledge graph.

    Examples:
        arc refresh unschedule
    """
    configure_logging(debug=debug or is_debug_mode())

    # Track command usage
    track_cli_command("refresh", subcommand="unschedule", args={"debug": debug})

    try:
        # Ensure the database is connected and initialized
        from arc_memory.db import get_adapter
        from arc_memory.sql.db import get_db_path

        adapter = get_adapter()
        if not adapter.is_connected():
            db_path = get_db_path()
            adapter.connect({"db_path": str(db_path)})
            # Initialize the database schema to ensure tables exist
            adapter.init_db()

        # Unschedule the refresh
        success = unschedule_refresh()

        if success:
            console.print("\n[green]✓ Auto-refresh unscheduled successfully[/green]")
        else:
            console.print("\n[yellow]⚠ Failed to unschedule auto-refresh[/yellow]")
            console.print("The scheduled task could not be removed. You may need to remove it manually.")

    except Exception as e:
        console.print(f"\n[red]Error unscheduling auto-refresh: {e}[/red]")
        logger.error(f"Error unscheduling auto-refresh: {e}")
        sys.exit(1)
