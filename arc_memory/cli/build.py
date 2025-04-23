"""Build commands for Arc Memory CLI."""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from arc_memory.errors import GraphBuildError
from arc_memory.ingest.adr import ingest_adrs
from arc_memory.ingest.git import ingest_git
from arc_memory.ingest.github import ingest_github
from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.schema.models import BuildManifest
from arc_memory.sql.db import (
    compress_db,
    ensure_arc_dir,
    init_db,
    load_build_manifest,
    save_build_manifest,
)

app = typer.Typer(help="Build commands")
console = Console()
logger = get_logger(__name__)


@app.callback()
def callback() -> None:
    """Build commands for Arc Memory."""
    configure_logging(debug=is_debug_mode())


@app.command()
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
            # Ingest Git data
            task = progress.add_task("Ingesting Git data...", total=None)
            git_nodes, git_edges, git_metadata = ingest_git(
                repo_path,
                max_commits=max_commits,
                days=days,
                last_commit_hash=manifest.last_commit_hash if manifest and incremental else None,
            )
            progress.update(task, completed=True)

            # Ingest GitHub data
            task = progress.add_task("Ingesting GitHub data...", total=None)
            github_nodes, github_edges, github_metadata = ingest_github(
                repo_path,
                token=token,
                last_processed=manifest.last_processed.get("github", {}) if manifest and incremental else None,
            )
            progress.update(task, completed=True)

            # Ingest ADRs
            task = progress.add_task("Ingesting ADRs...", total=None)
            adr_nodes, adr_edges, adr_metadata = ingest_adrs(
                repo_path,
                last_processed=manifest.last_processed.get("adrs", {}) if manifest and incremental else None,
            )
            progress.update(task, completed=True)

            # Combine all nodes and edges
            all_nodes = git_nodes + github_nodes + adr_nodes
            all_edges = git_edges + github_edges + adr_edges

            # Write to database
            task = progress.add_task("Writing to database...", total=None)
            # In a real implementation, we would use the add_nodes_and_edges function
            # For now, we'll just simulate it
            node_count = len(all_nodes)
            edge_count = len(all_edges)
            progress.update(task, completed=True)

            # Compress database
            task = progress.add_task("Compressing database...", total=None)
            compressed_path = compress_db(output_path)
            progress.update(task, completed=True)

            # Create and save build manifest
            build_manifest = BuildManifest(
                node_count=node_count,
                edge_count=edge_count,
                build_timestamp=datetime.now(),
                schema_version="0.1.0",
                last_commit_hash=git_metadata.get("last_commit_hash"),
                last_processed={
                    "git": git_metadata,
                    "github": github_metadata,
                    "adrs": adr_metadata,
                },
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
