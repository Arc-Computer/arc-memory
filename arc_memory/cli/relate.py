"""Relate command for Arc Memory CLI.

This command shows nodes related to a specific entity in the knowledge graph.
"""

import json
import sys
from enum import Enum
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.sdk import Arc
from arc_memory.sdk.progress import LoggingProgressCallback
from arc_memory.telemetry import track_command_usage

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


# This function is no longer needed as we're using the SDK


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
        # Create an Arc instance
        try:
            arc = Arc(repo_path="./")

            # Create a progress callback
            progress_callback = LoggingProgressCallback()

            # Get related entities
            related_entities = arc.get_related_entities(
                entity_id=entity_id,
                relationship_types=[relationship_type] if relationship_type else None,
                direction="both",
                max_results=max_results,
                include_properties=True,
                callback=progress_callback
            )

            # Convert to the format expected by the CLI
            related_nodes = []
            for entity in related_entities:
                # Convert RelatedEntity to dict
                node = {
                    "id": entity.id,
                    "type": entity.type,
                    "title": entity.title or "",
                    "relationship": entity.relationship,
                    "direction": entity.direction
                }

                # Get full entity details
                try:
                    details = arc.get_entity_details(
                        entity_id=entity.id,
                        include_related=False
                    )

                    # Add additional details
                    node["body"] = details.body
                    node["timestamp"] = details.timestamp.isoformat() if details.timestamp else None

                    # Add type-specific properties
                    for key, value in details.properties.items():
                        node[key] = value

                except Exception as e:
                    logger.warning(f"Error getting details for {entity.id}: {e}")

                related_nodes.append(node)

        except Exception as e:
            error_msg = f"Error: {e}"
            if format == Format.JSON:
                # For JSON format, print errors as JSON
                print(json.dumps({"error": error_msg}))
            else:
                # For text format, use rich console
                console.print(f"[red]{error_msg}[/red]")

            # Track error
            track_command_usage("relate_node", success=False, error=e, context=context)
            sys.exit(1)

        if not related_nodes:
            if format == Format.JSON:
                # For JSON format, return empty array
                print("[]")
            else:
                # For text format, use rich console
                console.print(
                    f"[yellow]No related nodes found for {entity_id}[/yellow]"
                )
            # Return with success code
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
