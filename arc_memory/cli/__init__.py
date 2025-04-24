"""Command-line interface for Arc Memory."""

import typer

app = typer.Typer(
    name="arc",
    help="Arc Memory - Local bi-temporal knowledge graph for code repositories.",
    add_completion=False,
)

# Import commands to register them with the app
from arc_memory.cli.auth import app as auth_app
from arc_memory.cli.build import app as build_app
from arc_memory.cli.doctor import app as doctor_app
from arc_memory.cli.trace import app as trace_app
from arc_memory.cli.version import app as version_app

# Add commands to the main app
app.add_typer(auth_app, name="auth")
app.add_typer(build_app, name="build")
app.add_typer(doctor_app, name="doctor")
app.add_typer(trace_app, name="trace")
app.add_typer(version_app, name="version")
