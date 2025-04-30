"""Relate command for Arc Memory CLI.

This command shows nodes related to a specific entity in the knowledge graph.
"""

import json
import sys
from enum import Enum
from typing import List, Dict, Any, Optional

import typer
from rich.console import Console
from rich.table import Table

from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.telemetry import track_command_usage
from arc_memory.trace import get_connected_nodes, get_node_by_id, format_trace_results

class Format(str, Enum):
    """Output format for relate results."""
    TEXT = "text"
    JSON = "json"


app = typer.Typer(help="Show related nodes for an entity")
console = Console()
logger = get_logger(__name__)


@app.callback()
def callback() -> None:
    """Show related nodes for an entity."""
    configure_logging(debug=is_debug_mode())


def get_related_nodes(
    conn: Any, entity_id: str, max_results: int = 10, relationship_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get nodes related to a specific entity.

    Args:
        conn: SQLite connection
        entity_id: The ID of the entity
        max_results: Maximum number of results to return
        relationship_type: Optional relationship type to filter by

    Returns:
        A list of related nodes
    """
    try:
        # Check if the entity exists
        entity = get_node_by_id(conn, entity_id)
        if not entity:
            return []

        # Get connected nodes
        connected_nodes = get_connected_nodes(conn, entity_id)

        # Filter by relationship type if specified
        if relationship_type:
            # Query the edges table to get nodes with the specified relationship type
            cursor = conn.cursor()
            cursor.execute(
                "SELECT dst FROM edges WHERE src = ? AND rel = ? UNION SELECT src FROM edges WHERE dst = ? AND rel = ?",
                (entity_id, relationship_type, entity_id, relationship_type)
            )
            filtered_ids = set(row[0] for row in cursor.fetchall())
            # Only keep nodes that have the specified relationship type
            connected_nodes = [node_id for node_id in connected_nodes if node_id in filtered_ids]

        # Get the node details for each connected ID
        related_nodes = []
        for node_id in connected_nodes[:max_results]:
            node = get_node_by_id(conn, node_id)
            if node:
                related_nodes.append(node)

        # Format the results
        return format_trace_results(related_nodes)

    except Exception as e:
        logger.error(f"Error in get_related_nodes: {e}")
        return []


@app.command()
def node(
    entity_id: str = typer.Argument(..., help="ID of the entity (e.g., commit:abc123)"),
    max_results: int = typer.Option(
        10, "--max-results", "-m", help="Maximum number of results to return"
    ),
    relationship_type: Optional[str] = typer.Option(
        None, "--rel", "-r", help="Relationship type to filter by (e.g., MERGES, MENTIONS)"
    ),
    format: Format = typer.Option(
        Format.TEXT, "--format", "-f",
        help="Output format (text or json)"
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging"
    ),
) -> None:
    """Show nodes related to a specific entity.

    This command shows nodes that are directly connected to the specified entity
    in the knowledge graph.

    Examples:
        arc relate node commit:abc123
        arc relate node pr:42 --format json
        arc relate node issue:123 --rel MENTIONS
    """
    configure_logging(debug=debug)

    # Track command usage
    context = {
        "entity_id": entity_id,
        "max_results": max_results,
        "relationship_type": relationship_type,
        "format": format.value
    }
    track_command_usage("relate_node", context=context)

    try:
        # Get the database path
        from arc_memory.sql.db import ensure_arc_dir, get_connection
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

        # Get related nodes
        conn = get_connection(db_path)
        related_nodes = get_related_nodes(conn, entity_id, max_results, relationship_type)

        if not related_nodes:
            if format == Format.JSON:
                # For JSON format, return empty array
                print("[]")
            else:
                # For text format, use rich console
                console.print(
                    f"[yellow]No related nodes found for {entity_id}[/yellow]"
                )
            return

        # Output based on format
        if format == Format.JSON:
            # JSON output - print directly to stdout
            print(json.dumps(related_nodes))
        else:
            # Text output - use rich table
            table = Table(title=f"Nodes related to {entity_id}")
            table.add_column("Type", style="cyan")
            table.add_column("ID", style="green")
            table.add_column("Title", style="white")
            table.add_column("Timestamp", style="dim")
            table.add_column("Details", style="yellow")

            for node in related_nodes:
                # Extract type-specific details
                details = ""
                if node["type"] == "commit":
                    if "author" in node:
                        details += f"Author: {node['author']}\n"
                    if "sha" in node:
                        details += f"SHA: {node['sha']}"
                elif node["type"] == "pr":
                    if "number" in node:
                        details += f"PR #{node['number']}\n"
                    if "state" in node:
                        details += f"State: {node['state']}\n"
                    if "url" in node:
                        details += f"URL: {node['url']}"
                elif node["type"] == "issue":
                    if "number" in node:
                        details += f"Issue #{node['number']}\n"
                    if "state" in node:
                        details += f"State: {node['state']}\n"
                    if "url" in node:
                        details += f"URL: {node['url']}"
                elif node["type"] == "adr":
                    if "status" in node:
                        details += f"Status: {node['status']}\n"
                    if "decision_makers" in node:
                        details += f"Decision Makers: {', '.join(node['decision_makers'])}\n"
                    if "path" in node:
                        details += f"Path: {node['path']}"

                table.add_row(
                    node["type"],
                    node["id"],
                    node["title"],
                    node["timestamp"] or "N/A",
                    details
                )

            console.print(table)

    except Exception as e:
        logger.exception("Error in relate_node command")
        error_msg = f"Error: {e}"
        if format == Format.JSON:
            # For JSON format, print errors to stderr
            print(error_msg, file=sys.stderr)
        else:
            # For text format, use rich console
            console.print(f"[red]{error_msg}[/red]")

        # Track error
        track_command_usage("relate_node", success=False, error=e, context=context)
        sys.exit(1)
