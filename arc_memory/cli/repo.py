"""Repository management commands for Arc Memory CLI.

This module provides commands for managing repositories in the knowledge graph.
"""

from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table

from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode
from arc_memory.sdk.core import Arc
from arc_memory.telemetry import track_cli_command

app = typer.Typer(help="Manage repositories in the knowledge graph")
console = Console()
logger = get_logger(__name__)


@app.callback()
def callback() -> None:
    """Repository management commands for Arc Memory."""
    configure_logging(debug=is_debug_mode())


@app.command()
def list():
    """List all repositories in the knowledge graph.

    Examples:
        arc repo list
    """
    try:
        # Track command usage
        track_cli_command("repo_list")

        # Initialize Arc with current directory
        arc = Arc("./")

        # Get all repositories
        repos = arc.list_repositories()

        if not repos:
            console.print("[yellow]No repositories found in the knowledge graph.[/yellow]")
            return

        # Create a table to display repositories
        table = Table(title="Repositories in Knowledge Graph")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Path", style="blue")
        table.add_column("Default Branch", style="magenta")

        # Add repositories to the table
        for repo in repos:
            table.add_row(
                repo["id"],
                repo["name"],
                repo["local_path"],
                repo["default_branch"]
            )

        # Print the table
        console.print(table)

    except Exception as e:
        logger.exception("Error listing repositories")
        console.print(f"[red]Error listing repositories: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def add(
    path: Path = typer.Argument(
        ..., help="Path to the repository to add."
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Name for the repository. If not provided, uses the directory name."
    )
):
    """Add a repository to the knowledge graph.

    Examples:
        arc repo add /path/to/repo
        arc repo add /path/to/repo --name my-repo
    """
    try:
        # Track command usage
        track_cli_command("repo_add", args={"path": str(path), "name": name})

        # Check if the repository exists
        if not path.exists():
            console.print(f"[red]Error: Repository path {path} does not exist[/red]")
            raise typer.Exit(1)

        # Initialize Arc with current directory
        arc = Arc("./")

        # Add the repository
        repo_id = arc.add_repository(path, name)

        console.print(f"[green]Repository added successfully with ID: {repo_id}[/green]")

    except Exception as e:
        logger.exception("Error adding repository")
        console.print(f"[red]Error adding repository: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def build(
    repo_id: str = typer.Argument(
        ..., help="ID of the repository to build."
    ),
    include_github: bool = typer.Option(
        True, "--github/--no-github", help="Include GitHub data in the graph."
    ),
    include_linear: bool = typer.Option(
        False, "--linear/--no-linear", help="Include Linear data in the graph."
    ),
    include_architecture: bool = typer.Option(
        True, "--architecture/--no-architecture", help="Extract architecture components."
    ),
    use_llm: bool = typer.Option(
        True, "--llm/--no-llm", help="Use an LLM to enhance the graph."
    ),
    llm_provider: str = typer.Option(
        "openai", "--llm-provider", help="The LLM provider to use."
    ),
    llm_model: str = typer.Option(
        "gpt-4.1", "--llm-model", help="The LLM model to use."
    ),
    llm_enhancement_level: str = typer.Option(
        "standard", "--llm-enhancement-level", help="The level of LLM enhancement to apply."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Print verbose output during the build process."
    )
):
    """Build a knowledge graph for a specific repository.

    Examples:
        arc repo build repository:1234abcd
        arc repo build repository:1234abcd --no-github --no-llm
        arc repo build repository:1234abcd --verbose
    """
    try:
        # Track command usage
        track_cli_command("repo_build", args={
            "repo_id": repo_id,
            "include_github": include_github,
            "include_linear": include_linear,
            "include_architecture": include_architecture,
            "use_llm": use_llm,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "llm_enhancement_level": llm_enhancement_level,
            "verbose": verbose
        })

        # Initialize Arc with current directory
        arc = Arc("./")

        # Build the repository
        console.print(f"[bold]Building knowledge graph for repository {repo_id}...[/bold]")
        result = arc.build_repository(
            repo_id=repo_id,
            include_github=include_github,
            include_linear=include_linear,
            include_architecture=include_architecture,
            use_llm=use_llm,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_enhancement_level=llm_enhancement_level,
            verbose=verbose
        )

        # Print result
        console.print(f"[green]Successfully built knowledge graph for repository {repo_id}[/green]")
        console.print(f"Added {result.get('node_count', 0)} nodes and {result.get('edge_count', 0)} edges")

    except Exception as e:
        logger.exception("Error building repository")
        console.print(f"[red]Error building repository: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def active(
    repo_ids: Optional[List[str]] = typer.Argument(
        None, help="Repository IDs to set as active. If none provided, shows current active repositories."
    )
):
    """Set or show active repositories for queries.

    Examples:
        arc repo active
        arc repo active repository:1234abcd repository:5678efgh
    """
    try:
        # Track command usage
        track_cli_command("repo_active", args={"repo_ids": repo_ids})

        # Initialize Arc with current directory
        arc = Arc("./")

        if not repo_ids:
            # Show current active repositories
            active_repos = arc.get_active_repositories()

            if not active_repos:
                console.print("[yellow]No active repositories.[/yellow]")
                return

            # Create a table to display active repositories
            table = Table(title="Active Repositories")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Path", style="blue")

            # Add repositories to the table
            for repo in active_repos:
                table.add_row(
                    repo["id"],
                    repo["name"],
                    repo["local_path"]
                )

            # Print the table
            console.print(table)
        else:
            # Set active repositories
            arc.set_active_repositories(repo_ids)
            console.print(f"[green]Set {len(repo_ids)} repositories as active.[/green]")

    except Exception as e:
        logger.exception("Error managing active repositories")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def remove(
    repo_id: str = typer.Argument(
        ..., help="ID of the repository to remove."
    ),
    delete_nodes: bool = typer.Option(
        False, "--delete-nodes", help="Delete all nodes from this repository."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force removal without confirmation."
    )
):
    """Remove a repository from the knowledge graph.

    Examples:
        arc repo remove repository:1234abcd
        arc repo remove repository:1234abcd --delete-nodes
        arc repo remove repository:1234abcd --force
    """
    try:
        # Track command usage
        track_cli_command("repo_remove", args={
            "repo_id": repo_id,
            "delete_nodes": delete_nodes,
            "force": force
        })

        # Initialize Arc with current directory
        arc = Arc("./")

        # Get repository details for confirmation
        repos = arc.list_repositories()
        repo = next((r for r in repos if r["id"] == repo_id), None)

        if not repo:
            console.print(f"[red]Repository with ID '{repo_id}' does not exist[/red]")
            raise typer.Exit(1)

        # Confirm removal
        if not force:
            message = f"Are you sure you want to remove repository '{repo['name']}' ({repo_id})?"
            if delete_nodes:
                message += " This will delete all nodes from this repository!"

            if not typer.confirm(message):
                console.print("[yellow]Operation cancelled[/yellow]")
                return

        # Remove repository
        arc.remove_repository(repo_id, delete_nodes=delete_nodes)

        if delete_nodes:
            console.print(f"[green]Repository '{repo['name']}' and all its nodes have been removed[/green]")
        else:
            console.print(f"[green]Repository '{repo['name']}' has been removed (nodes preserved)[/green]")

    except Exception as e:
        logger.exception("Error removing repository")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    repo_id: str = typer.Argument(
        ..., help="ID of the repository to update."
    ),
    path: Optional[str] = typer.Option(
        None, "--path", help="New local path for the repository."
    ),
    name: Optional[str] = typer.Option(
        None, "--name", help="New name for the repository."
    ),
    url: Optional[str] = typer.Option(
        None, "--url", help="New URL for the repository."
    ),
    default_branch: Optional[str] = typer.Option(
        None, "--default-branch", help="New default branch for the repository."
    )
):
    """Update repository information.

    Examples:
        arc repo update repository:1234abcd --path /new/path/to/repo
        arc repo update repository:1234abcd --name "New Repository Name"
        arc repo update repository:1234abcd --name "New Name" --url "https://github.com/new/url" --default-branch develop
    """
    try:
        # Track command usage
        track_cli_command("repo_update", args={
            "repo_id": repo_id,
            "path": path,
            "name": name,
            "url": url,
            "default_branch": default_branch
        })

        # Initialize Arc with current directory
        arc = Arc("./")

        # Get repository details for confirmation
        repos = arc.list_repositories()
        repo = next((r for r in repos if r["id"] == repo_id), None)

        if not repo:
            console.print(f"[red]Repository with ID '{repo_id}' does not exist[/red]")
            raise typer.Exit(1)

        # Update repository
        new_repo_id = arc.update_repository(
            repo_id,
            new_path=path,
            new_name=name,
            new_url=url,
            new_default_branch=default_branch
        )

        if new_repo_id != repo_id:
            console.print(f"[green]Repository path changed. New repository ID: {new_repo_id}[/green]")
        else:
            console.print(f"[green]Repository '{repo['name']}' updated successfully[/green]")

    except Exception as e:
        logger.exception("Error updating repository")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
