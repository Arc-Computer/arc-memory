"""Command-line interface for Arc Memory."""

import typer

app = typer.Typer(
    name="arc",
    help="Arc Memory - Local bi-temporal knowledge graph for code repositories.",
    add_completion=False,
)

# Import commands to register them with the app
from arc_memory.cli import auth, build, doctor, version  # noqa

# Import trace command
from arc_memory.cli.trace import app as trace_app

# Add trace command to the main app
app.add_typer(trace_app, name="trace")
