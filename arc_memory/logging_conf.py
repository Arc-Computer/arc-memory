"""Logging configuration for Arc Memory."""

import logging
import os
import sys
from typing import Optional
from rich.console import Console

# Create a rich console for output
console = Console()


def configure_logging(debug: bool = False) -> None:
    """Configure logging for Arc Memory.

    Args:
        debug: Whether to enable debug logging.
    """
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set third-party loggers to a higher level to reduce noise
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("git").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: The name of the logger.

    Returns:
        A logger instance.
    """
    return logging.getLogger(f"arc_memory.{name}")


# Environment variable to control debug mode
def is_debug_mode() -> bool:
    """Return whether debug mode is enabled."""
    return os.environ.get("DEBUG", "").lower() in ("1", "true", "yes", "on")


def get_console() -> Console:
    """Return the rich console instance.
    
    Returns:
        Console: A rich console instance
    """
    return console
