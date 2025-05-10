"""Migration command for Arc Memory."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from arc_memory.logging_conf import get_logger
from arc_memory.migrations.add_timestamp_column import migrate_database
from arc_memory.sql.db import DEFAULT_DB_PATH

app = typer.Typer(help="Migrate the knowledge graph database schema.")
logger = get_logger(__name__)
console = Console()


@app.callback(invoke_without_command=True)
def migrate(
    db_path: Optional[Path] = typer.Option(
        None, "--db", "-d", help="Path to the database file."
    ),
) -> None:
    """Migrate the knowledge graph database schema.

    This command updates the database schema to the latest version.
    It is safe to run multiple times, as it will only apply migrations
    that haven't been applied yet.

    Examples:
        # Migrate the default database
        arc migrate

        # Migrate a specific database
        arc migrate --db /path/to/graph.db
    """
    console.print("\n🔄 Arc Memory Database Migration")
    console.print("================================")

    if db_path is None:
        db_path = DEFAULT_DB_PATH
        console.print(f"Using default database path: {db_path}")
    else:
        console.print(f"Using database path: {db_path}")

    if not db_path.exists():
        console.print(f"[red]Error: Database file not found: {db_path}[/red]")
        console.print("Run 'arc build' to create the database first.")
        return

    console.print("\n[bold]Running migrations...[/bold]")

    # Run the timestamp column migration
    with console.status("Adding timestamp column..."):
        success = migrate_database(db_path)

    if success:
        console.print("[green]✓ Successfully migrated database schema[/green]")
    else:
        console.print("[red]✗ Failed to migrate database schema[/red]")
        console.print("Check the logs for more information.")


if __name__ == "__main__":
    app()
