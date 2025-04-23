"""Version command for Arc Memory CLI."""

import typer
from rich.console import Console

import arc_memory

app = typer.Typer(help="Version commands")
console = Console()


@app.callback()
def callback() -> None:
    """Version commands for Arc Memory."""
    pass


@app.command()
def version() -> None:
    """Show the version of Arc Memory."""
    console.print(f"Arc Memory version: {arc_memory.__version__}")
