"""Build commands for Arc Memory CLI."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from arc_memory.errors import GraphBuildError
from arc_memory.plugins import discover_plugins
from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.schema.models import BuildManifest
from arc_memory.sql.db import (
    compress_db,
    ensure_arc_dir,
    init_db,
    load_build_manifest,
    save_build_manifest,
)

app = typer.Typer(help="Build the knowledge graph from Git, GitHub, and ADRs")
console = Console()
logger = get_logger(__name__)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    repo_path: Path = typer.Option(
        Path.cwd(), "--repo", "-r", help="Path to the Git repository."
    ),
    output_path: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Path to the output database file."
    ),
    max_commits: int = typer.Option(
        5000, "--max-commits", help="Maximum number of commits to process."
    ),
    days: int = typer.Option(
        365, "--days", help="Maximum age of commits to process in days."
    ),
    incremental: bool = typer.Option(
        False, "--incremental", help="Only process new data since last build."
    ),
    pull: bool = typer.Option(
        False, "--pull", help="Pull the latest CI-built graph."
    ),
    token: Optional[str] = typer.Option(
        None, "--token", help="GitHub token to use for API calls."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Build the knowledge graph from Git, GitHub, and ADRs."""
    configure_logging(debug=debug or is_debug_mode())

    # If a subcommand was invoked, don't run the default command
    if ctx.invoked_subcommand is not None:
        return

    # Determine output path
    arc_dir = ensure_arc_dir()
    output_path_to_use = output_path if output_path is not None else arc_dir / "graph.db"

    # Run the build command (moved to a separate function)
    build_graph(
        repo_path=repo_path,
        output_path=output_path_to_use,
        max_commits=max_commits,
        days=days,
        incremental=incremental,
        pull=pull,
        token=token,
        debug=debug,
    )


def build_graph(
    repo_path: Path,
    output_path: Optional[Path] = None,
    max_commits: int = 5000,
    days: int = 365,
    incremental: bool = False,
    pull: bool = False,
    token: Optional[str] = None,
    debug: bool = False,
) -> None:
    """Build the knowledge graph from Git, GitHub, and ADRs."""
    configure_logging(debug=debug)

    # Ensure output directory exists
    arc_dir = ensure_arc_dir()
    if output_path is None:
        output_path = arc_dir / "graph.db"

    # Check if repo_path is a Git repository
    if not (repo_path / ".git").exists():
        console.print(
            f"[red]Error: {repo_path} is not a Git repository.[/red]"
        )
        sys.exit(1)

    # Handle --pull option
    if pull:
        console.print(
            "[yellow]Pulling latest CI-built graph is not implemented yet.[/yellow]"
        )
        sys.exit(1)

    # Load existing manifest for incremental builds
    manifest = None
    if incremental:
        manifest = load_build_manifest()
        if manifest is None:
            console.print(
                "[yellow]No existing build manifest found. Performing full build.[/yellow]"
            )
            incremental = False
        else:
            console.print(f"[green]Found existing build manifest. Last build: {manifest.build_time}[/green]")

    # Initialize database
    try:
        conn = init_db(output_path)
    except Exception as e:
        console.print(f"[red]Failed to initialize database: {e}[/red]")
        sys.exit(1)

    # Build the graph
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        try:
            # Discover plugins
            registry = discover_plugins()
            logger.info(f"Discovered plugins: {registry.list_plugins()}")

            # Initialize lists for all nodes and edges
            all_nodes = []
            all_edges = []
            plugin_metadata = {}

            # Process each plugin
            for plugin in registry.get_all():
                plugin_name = plugin.get_name()
                task = progress.add_task(f"Ingesting {plugin_name} data...", total=None)

                # Get last processed data for this plugin
                last_processed_data = None
                if manifest and incremental and plugin_name in manifest.last_processed:
                    last_processed_data = manifest.last_processed[plugin_name]

                # Special handling for Git plugin (pass max_commits and days)
                if plugin_name == "git":
                    nodes, edges, metadata = plugin.ingest(
                        repo_path,
                        max_commits=max_commits,
                        days=days,
                        last_processed=last_processed_data,
                    )
                # Special handling for GitHub plugin (pass token)
                elif plugin_name == "github":
                    nodes, edges, metadata = plugin.ingest(
                        repo_path,
                        token=token,
                        last_processed=last_processed_data,
                    )
                # Default handling for other plugins
                else:
                    nodes, edges, metadata = plugin.ingest(
                        repo_path,
                        last_processed=last_processed_data,
                    )

                # Add results to the combined lists
                all_nodes.extend(nodes)
                all_edges.extend(edges)
                plugin_metadata[plugin_name] = metadata

                # Update progress
                progress.update(task, completed=True)

            # Write to database
            task = progress.add_task("Writing to database...", total=None)
            from arc_memory.sql.db import add_nodes_and_edges
            add_nodes_and_edges(conn, all_nodes, all_edges)

            # Get the node and edge counts
            from arc_memory.sql.db import get_node_count, get_edge_count
            node_count = get_node_count(conn)
            edge_count = get_edge_count(conn)
            progress.update(task, completed=True)

            # Compress database
            task = progress.add_task("Compressing database...", total=None)
            compressed_path = compress_db(output_path)
            progress.update(task, completed=True)

            # Create and save build manifest
            # Get the last commit hash from the git plugin metadata
            last_commit_hash = None
            if "git" in plugin_metadata and "last_commit_hash" in plugin_metadata["git"]:
                last_commit_hash = plugin_metadata["git"]["last_commit_hash"]

            build_manifest = BuildManifest(
                schema_version="0.1.0",
                build_time=datetime.now(),
                commit=last_commit_hash,
                node_count=node_count,
                edge_count=edge_count,
                last_processed=plugin_metadata,
            )
            save_build_manifest(build_manifest)

            console.print(
                f"[green]Build complete! {node_count} nodes and {edge_count} edges.[/green]"
            )
            console.print(
                f"[green]Database saved to {output_path} and compressed to {compressed_path}[/green]"
            )
        except GraphBuildError as e:
            progress.stop()
            console.print(f"[red]Build failed: {e}[/red]")
            sys.exit(1)
        except Exception as e:
            progress.stop()
            logger.exception("Unexpected error during build")
            console.print(f"[red]Unexpected error: {e}[/red]")
            sys.exit(1)


# Keep the original command for backward compatibility
@app.command(hidden=True)
def build(
    repo_path: Path = typer.Option(
        Path.cwd(), "--repo", "-r", help="Path to the Git repository."
    ),
    output_path: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Path to the output database file."
    ),
    max_commits: int = typer.Option(
        5000, "--max-commits", help="Maximum number of commits to process."
    ),
    days: int = typer.Option(
        365, "--days", help="Maximum age of commits to process in days."
    ),
    incremental: bool = typer.Option(
        False, "--incremental", help="Only process new data since last build."
    ),
    pull: bool = typer.Option(
        False, "--pull", help="Pull the latest CI-built graph."
    ),
    token: Optional[str] = typer.Option(
        None, "--token", help="GitHub token to use for API calls."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging."
    ),
) -> None:
    """Build the knowledge graph from Git, GitHub, and ADRs."""
    # Call the extracted function
    build_graph(
        repo_path=repo_path,
        output_path=output_path,
        max_commits=max_commits,
        days=days,
        incremental=incremental,
        pull=pull,
        token=token,
        debug=debug,
    )
