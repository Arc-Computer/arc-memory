"""Doctor commands for Arc Memory CLI."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.sql.db import (
    decompress_db,
    get_edge_count,
    get_node_count,
    init_db,
    load_build_manifest,
)

app = typer.Typer(help="Check the health of the knowledge graph")
console = Console()
logger = get_logger(__name__)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    db_path: Optional[Path] = typer.Option(
        None, "--db", help="Path to the database file."
    ),
    compressed_path: Optional[Path] = typer.Option(
        None, "--compressed", help="Path to the compressed database file."
    ),
    manifest_path: Optional[Path] = typer.Option(
        None, "--manifest", help="Path to the build manifest file."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Check the health of the knowledge graph."""
    configure_logging(debug=debug or is_debug_mode())

    # If a subcommand was invoked, don't run the default command
    if ctx.invoked_subcommand is not None:
        return

    # Run the doctor command (moved to a separate function)
    check_health(
        db_path=db_path,
        compressed_path=compressed_path,
        manifest_path=manifest_path,
        debug=debug,
    )


def check_health(
    db_path: Optional[Path] = None,
    compressed_path: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
    debug: bool = False,
) -> None:
    """Check the health of the knowledge graph."""
    configure_logging(debug=debug)

    # Use default paths if not provided
    arc_dir = Path.home() / ".arc"
    if db_path is None:
        db_path = arc_dir / "graph.db"
    if compressed_path is None:
        compressed_path = arc_dir / "graph.db.zst"
    if manifest_path is None:
        manifest_path = arc_dir / "build.json"

    # Check if files exist
    db_exists = db_path.exists()
    compressed_exists = compressed_path.exists()
    manifest_exists = manifest_path.exists()

    # Print status
    console.print("[bold]Arc Memory Doctor[/bold]")
    console.print()

    # Check files
    table = Table(title="Files")
    table.add_column("File")
    table.add_column("Status")
    table.add_column("Size")

    table.add_row(
        str(db_path),
        "[green]Exists[/green]" if db_exists else "[red]Missing[/red]",
        f"{db_path.stat().st_size / 1024:.1f} KB" if db_exists else "N/A",
    )
    table.add_row(
        str(compressed_path),
        "[green]Exists[/green]" if compressed_exists else "[red]Missing[/red]",
        f"{compressed_path.stat().st_size / 1024:.1f} KB" if compressed_exists else "N/A",
    )
    table.add_row(
        str(manifest_path),
        "[green]Exists[/green]" if manifest_exists else "[red]Missing[/red]",
        f"{manifest_path.stat().st_size / 1024:.1f} KB" if manifest_exists else "N/A",
    )

    console.print(table)
    console.print()

    # If database doesn't exist but compressed does, decompress it
    if not db_exists and compressed_exists:
        console.print("Decompressing database...")
        try:
            decompress_db(compressed_path, db_path)
            db_exists = True
            console.print("[green]Database decompressed successfully.[/green]")
        except Exception as e:
            console.print(f"[red]Failed to decompress database: {e}[/red]")

    # Check database
    if db_exists:
        try:
            conn = init_db(db_path)
            node_count = get_node_count(conn)
            edge_count = get_edge_count(conn)

            table = Table(title="Database")
            table.add_column("Metric")
            table.add_column("Value")

            table.add_row("Nodes", str(node_count))
            table.add_row("Edges", str(edge_count))

            console.print(table)
            console.print()
        except Exception as e:
            console.print(f"[red]Failed to query database: {e}[/red]")

    # Check manifest
    if manifest_exists:
        try:
            manifest = load_build_manifest(manifest_path)
            if manifest:
                table = Table(title="Build Manifest")
                table.add_column("Metric")
                table.add_column("Value")

                table.add_row("Build Time", str(manifest.build_time))
                table.add_row("Schema Version", manifest.schema_version)
                table.add_row("Node Count", str(manifest.node_count))
                table.add_row("Edge Count", str(manifest.edge_count))
                table.add_row("Last Commit Hash", manifest.commit or "N/A")

                console.print(table)
                console.print()
            else:
                console.print("[red]Failed to parse build manifest.[/red]")
        except Exception as e:
            console.print(f"[red]Failed to load build manifest: {e}[/red]")

    # Overall status
    if db_exists or compressed_exists:
        console.print("[green]Arc Memory is ready to use.[/green]")
    else:
        console.print(
            "[red]Arc Memory is not set up. Run 'arc build' to build the knowledge graph.[/red]"
        )


# Keep the original command for backward compatibility
@app.command(hidden=True)
def doctor(
    db_path: Optional[Path] = typer.Option(
        None, "--db", help="Path to the database file."
    ),
    compressed_path: Optional[Path] = typer.Option(
        None, "--compressed", help="Path to the compressed database file."
    ),
    manifest_path: Optional[Path] = typer.Option(
        None, "--manifest", help="Path to the build manifest file."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Check the health of the knowledge graph."""
    # Call the extracted function
    check_health(
        db_path=db_path,
        compressed_path=compressed_path,
        manifest_path=manifest_path,
        debug=debug,
    )
