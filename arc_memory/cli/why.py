"""Why command for Arc Memory CLI.

This command provides a user-friendly way to trace the history of a specific line in a file,
showing the decision trail through commits, PRs, issues, and ADRs.
"""

import json
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.telemetry import track_command_usage
from arc_memory.trace import trace_history_for_file_line

class Format(str, Enum):
    """Output format for why results."""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


app = typer.Typer(help="Show decision trail for a file line")
console = Console()
logger = get_logger(__name__)


@app.callback()
def callback() -> None:
    """Show decision trail for a file line."""
    configure_logging(debug=is_debug_mode())


@app.command()
def file(
    file_path: str = typer.Argument(..., help="Path to the file"),
    line_number: int = typer.Argument(..., help="Line number to trace"),
    max_results: int = typer.Option(
        5, "--max-results", "-m", help="Maximum number of results to return"
    ),
    max_hops: int = typer.Option(
        3, "--max-hops", "-h", help="Maximum number of hops in the graph traversal"
    ),
    format: Format = typer.Option(
        Format.TEXT, "--format", "-f",
        help="Output format (text, json, or markdown)"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging"
    ),
) -> None:
    """Show the decision trail for a specific line in a file.

    This command traces the history of a specific line in a file, showing the commit
    that last modified it and related entities such as PRs, issues, and ADRs.

    Examples:
        arc why file src/main.py 42
        arc why file src/main.py 42 --format markdown
        arc why file src/main.py 42 --max-results 10 --max-hops 4
    """
    configure_logging(debug=debug)

    # Track command usage
    context = {
        "file_path": file_path,
        "line_number": line_number,
        "max_results": max_results,
        "max_hops": max_hops,
        "format": format.value
    }
    track_command_usage("why_file", context=context)

    try:
        # Get the database path
        from arc_memory.sql.db import ensure_arc_dir
        arc_dir = ensure_arc_dir()
        db_path = arc_dir / "graph.db"

        # Check if the database exists
        if not db_path.exists():
            error_msg = f"Error: Database not found at {db_path}"
            if format == Format.JSON:
                # For JSON format, print errors to stderr
                print(error_msg, file=sys.stderr)
            else:
                # For text format, use rich console
                console.print(f"[red]{error_msg}[/red]")
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
            if format == Format.JSON:
                # For JSON format, return empty array
                print("[]")
            else:
                # For text format, use rich console
                console.print(
                    f"[yellow]No history found for {file_path}:{line_number}[/yellow]"
                )
            return

        # Output based on format
        if format == Format.JSON:
            # JSON output - print directly to stdout
            print(json.dumps(results))
        elif format == Format.MARKDOWN:
            # Markdown output
            md_content = f"# Decision Trail for {file_path}:{line_number}\n\n"
            
            for result in results:
                md_content += f"## {result['type'].capitalize()}: {result['title']}\n\n"
                md_content += f"**ID**: {result['id']}  \n"
                md_content += f"**Timestamp**: {result['timestamp'] or 'N/A'}  \n\n"
                
                # Add type-specific details
                if result["type"] == "commit":
                    if "author" in result:
                        md_content += f"**Author**: {result['author']}  \n"
                    if "sha" in result:
                        md_content += f"**SHA**: {result['sha']}  \n"
                elif result["type"] == "pr":
                    if "number" in result:
                        md_content += f"**PR**: #{result['number']}  \n"
                    if "state" in result:
                        md_content += f"**State**: {result['state']}  \n"
                    if "url" in result:
                        md_content += f"**URL**: {result['url']}  \n"
                elif result["type"] == "issue":
                    if "number" in result:
                        md_content += f"**Issue**: #{result['number']}  \n"
                    if "state" in result:
                        md_content += f"**State**: {result['state']}  \n"
                    if "url" in result:
                        md_content += f"**URL**: {result['url']}  \n"
                elif result["type"] == "adr":
                    if "status" in result:
                        md_content += f"**Status**: {result['status']}  \n"
                    if "decision_makers" in result:
                        md_content += f"**Decision Makers**: {', '.join(result['decision_makers'])}  \n"
                    if "path" in result:
                        md_content += f"**Path**: {result['path']}  \n"
                
                md_content += "\n---\n\n"
            
            # Print markdown
            console.print(Markdown(md_content))
        else:
            # Text output - use rich table and panels
            console.print(Panel(f"[bold]Decision Trail for {file_path}:{line_number}[/bold]", 
                               style="green"))
            
            for result in results:
                # Create a panel for each result
                title = f"[bold]{result['type'].upper()}[/bold]: {result['title']}"
                content = f"ID: {result['id']}\n"
                content += f"Timestamp: {result['timestamp'] or 'N/A'}\n\n"
                
                # Add type-specific details
                if result["type"] == "commit":
                    if "author" in result:
                        content += f"Author: {result['author']}\n"
                    if "sha" in result:
                        content += f"SHA: {result['sha']}"
                elif result["type"] == "pr":
                    if "number" in result:
                        content += f"PR #{result['number']}\n"
                    if "state" in result:
                        content += f"State: {result['state']}\n"
                    if "url" in result:
                        content += f"URL: {result['url']}"
                elif result["type"] == "issue":
                    if "number" in result:
                        content += f"Issue #{result['number']}\n"
                    if "state" in result:
                        content += f"State: {result['state']}\n"
                    if "url" in result:
                        content += f"URL: {result['url']}"
                elif result["type"] == "adr":
                    if "status" in result:
                        content += f"Status: {result['status']}\n"
                    if "decision_makers" in result:
                        content += f"Decision Makers: {', '.join(result['decision_makers'])}\n"
                    if "path" in result:
                        content += f"Path: {result['path']}"
                
                # Determine panel style based on node type
                style = {
                    "commit": "cyan",
                    "pr": "green",
                    "issue": "yellow",
                    "adr": "blue",
                    "file": "magenta"
                }.get(result["type"], "white")
                
                console.print(Panel(content, title=title, style=style))

    except Exception as e:
        logger.exception("Error in why_file command")
        error_msg = f"Error: {e}"
        if format == Format.JSON:
            # For JSON format, print errors to stderr
            print(error_msg, file=sys.stderr)
        else:
            # For text format, use rich console
            console.print(f"[red]{error_msg}[/red]")
        
        # Track error
        track_command_usage("why_file", success=False, error=e, context=context)
        sys.exit(1)
