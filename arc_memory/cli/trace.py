"""Trace history commands for Arc Memory CLI."""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.trace import trace_history_for_file_line

app = typer.Typer(help="Trace history commands")
console = Console()
logger = get_logger(__name__)


@app.callback()
def callback() -> None:
    """Trace history commands for Arc Memory."""
    configure_logging(debug=is_debug_mode())


@app.command("file")
def trace_file(
    file_path: str = typer.Argument(..., help="Path to the file"),
    line_number: int = typer.Argument(..., help="Line number to trace"),
    # Note: repo_path is determined automatically from the current working directory
    max_results: int = typer.Option(
        3, "--max-results", "-m", help="Maximum number of results to return"
    ),
    max_hops: int = typer.Option(
        2, "--max-hops", "-h", help="Maximum number of hops in the graph traversal"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging"
    ),
) -> None:
    """Trace the history of a specific line in a file."""
    configure_logging(debug=debug)

    try:
        # Get the database path
        from arc_memory.sql.db import ensure_arc_dir
        arc_dir = ensure_arc_dir()
        db_path = arc_dir / "graph.db"

        # Check if the database exists
        if not db_path.exists():
            console.print(
                f"[red]Error: Database not found at {db_path}[/red]"
            )
            console.print(
                "Run [bold]arc build[/bold] to create the knowledge graph."
            )
            sys.exit(1)

        # Trace the history
        results = trace_history_for_file_line(
            db_path,
            file_path,
            line_number,
            max_results,
            max_hops
        )

        if not results:
            console.print(
                f"[yellow]No history found for {file_path}:{line_number}[/yellow]"
            )
            return

        # Display the results
        table = Table(title=f"History for {file_path}:{line_number}")
        table.add_column("Type", style="cyan")
        table.add_column("ID", style="green")
        table.add_column("Title", style="white")
        table.add_column("Timestamp", style="dim")
        table.add_column("Details", style="yellow")

        for result in results:
            # Extract type-specific details
            details = ""
            if result["type"] == "commit":
                if "author" in result:
                    details += f"Author: {result['author']}\n"
                if "sha" in result:
                    details += f"SHA: {result['sha']}"
            elif result["type"] == "pr":
                if "number" in result:
                    details += f"PR #{result['number']}\n"
                if "state" in result:
                    details += f"State: {result['state']}\n"
                if "url" in result:
                    details += f"URL: {result['url']}"
            elif result["type"] == "issue":
                if "number" in result:
                    details += f"Issue #{result['number']}\n"
                if "state" in result:
                    details += f"State: {result['state']}\n"
                if "url" in result:
                    details += f"URL: {result['url']}"
            elif result["type"] == "adr":
                if "status" in result:
                    details += f"Status: {result['status']}\n"
                if "decision_makers" in result:
                    details += f"Decision Makers: {', '.join(result['decision_makers'])}\n"
                if "path" in result:
                    details += f"Path: {result['path']}"

            table.add_row(
                result["type"],
                result["id"],
                result["title"],
                result["timestamp"] or "N/A",
                details
            )

        console.print(table)

    except Exception as e:
        logger.exception("Error in trace_file command")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
