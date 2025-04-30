"""Telemetry functionality for Arc Memory.

This module provides functions for tracking usage and measuring MTTR improvements
using PostHog for analytics.

Note: This telemetry implementation is designed to be privacy-respecting and does not
collect any personally identifiable information (PII) or sensitive data. All data is
anonymous and opt-in by default.
"""

import atexit
import json
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from arc_memory.config import get_config, update_config
from arc_memory.logging_conf import get_logger
from arc_memory.sql.db import ensure_arc_dir

logger = get_logger(__name__)

# PostHog API key for Arc Memory
# This is a public API key that can be included in the source code
POSTHOG_API_KEY = "phc_kyA8Z4j3H01yqDZly5J3XShAbSrseDtoVS6AxWe8wp9"
POSTHOG_HOST = "https://us.i.posthog.com"  # PostHog Cloud instance

# Queue for telemetry events when PostHog is not available
_telemetry_queue: List[Dict[str, Any]] = []
_telemetry_lock = threading.Lock()
_posthog_client = None


def _get_posthog_client():
    """Get or initialize the PostHog client.

    Returns:
        The PostHog client if available, None otherwise.
    """
    global _posthog_client

    if _posthog_client is not None:
        return _posthog_client

    try:
        # Try to import PostHog
        try:
            import posthog
            from posthog import Posthog
        except ImportError:
            logger.debug("PostHog not installed, using local telemetry queue")
            return None

        # Initialize PostHog client
        _posthog_client = Posthog(
            api_key=POSTHOG_API_KEY,
            host=POSTHOG_HOST,
            disable_geoip=True,  # Don't track server IP location
            debug=False,  # Set to True for debugging
        )

        # Register flush on exit
        atexit.register(_posthog_client.flush)

        return _posthog_client

    except Exception as e:
        logger.error(f"Error initializing PostHog client: {e}")
        return None


def track_command_usage(
    command_name: str,
    success: bool = True,
    error: Optional[Exception] = None,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Track command usage if telemetry is enabled.

    Args:
        command_name: The name of the command.
        success: Whether the command succeeded.
        error: The exception that occurred, if any.
        session_id: The session ID for MTTR tracking.
        context: Additional context for the event.
    """
    try:
        # Check if telemetry is enabled
        config = get_config()
        if not config.get("telemetry", {}).get("enabled", False):
            return

        # Get installation ID (anonymous)
        installation_id = config.get("telemetry", {}).get("installation_id", "unknown")

        # Get or create session ID for tracking investigation sessions (MTTR)
        if session_id is None:
            session_id = config.get("telemetry", {}).get("current_session_id")
            if session_id is None:
                # Create new session ID if none exists
                session_id = str(uuid.uuid4())
                # Store in config for future commands in this session
                update_config("telemetry", "current_session_id", session_id)

                # Track session start for MTTR calculation
                track_session_event("session_start", session_id)

        # Prepare properties
        properties = {
            "command": command_name,
            "success": success,
            "error_type": error.__class__.__name__ if error else None,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "$lib": "arc-memory-python",
            "$lib_version": _get_version(),
        }

        # Add context if provided (file path, line number, etc.)
        if context:
            properties.update(context)

        # Try to send to PostHog
        posthog_client = _get_posthog_client()
        if posthog_client:
            posthog_client.capture(
                distinct_id=installation_id,
                event=f"command_{command_name}",
                properties=properties
            )
        else:
            # Fall back to local queue
            _add_to_telemetry_queue(installation_id, f"command_{command_name}", properties)

    except Exception as e:
        # Never let telemetry errors affect the user
        logger.error(f"Error in track_command_usage: {e}")


def track_session_event(event_type: str, session_id: str) -> None:
    """Track session events for MTTR calculation.

    Args:
        event_type: The type of session event.
        session_id: The session ID.
    """
    try:
        config = get_config()
        if not config.get("telemetry", {}).get("enabled", False):
            return

        installation_id = config.get("telemetry", {}).get("installation_id", "unknown")

        properties = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "$lib": "arc-memory-python",
            "$lib_version": _get_version(),
        }

        # Try to send to PostHog
        posthog_client = _get_posthog_client()
        if posthog_client:
            posthog_client.capture(
                distinct_id=installation_id,
                event=event_type,
                properties=properties
            )
        else:
            # Fall back to local queue
            _add_to_telemetry_queue(installation_id, event_type, properties)

    except Exception as e:
        logger.error(f"Error in track_session_event: {e}")


def end_investigation_session() -> None:
    """End the current investigation session for MTTR calculation."""
    try:
        config = get_config()
        if not config.get("telemetry", {}).get("enabled", False):
            return

        session_id = config.get("telemetry", {}).get("current_session_id")

        if session_id:
            # Track session end for MTTR calculation
            track_session_event("session_end", session_id)

            # Clear session ID
            update_config("telemetry", "current_session_id", None)

    except Exception as e:
        logger.error(f"Error in end_investigation_session: {e}")


def _add_to_telemetry_queue(
    distinct_id: str, event_name: str, properties: Dict[str, Any]
) -> None:
    """Add an event to the telemetry queue.

    Args:
        distinct_id: The installation ID.
        event_name: The name of the event.
        properties: The event properties.
    """
    try:
        with _telemetry_lock:
            _telemetry_queue.append({
                "distinct_id": distinct_id,
                "event": event_name,
                "properties": properties,
                "timestamp": datetime.now().isoformat()
            })

        # Flush queue if it gets too large
        if len(_telemetry_queue) >= 10:
            flush_telemetry_queue()

    except Exception as e:
        logger.error(f"Error in _add_to_telemetry_queue: {e}")


def flush_telemetry_queue() -> None:
    """Flush the telemetry queue to disk."""
    try:
        with _telemetry_lock:
            if not _telemetry_queue:
                return

            # Get the telemetry log path
            arc_dir = ensure_arc_dir()
            log_dir = arc_dir / "log"
            log_dir.mkdir(exist_ok=True)
            log_path = log_dir / "telemetry.jsonl"

            # Write events to the log file
            with open(log_path, "a") as f:
                for event in _telemetry_queue:
                    f.write(json.dumps(event) + "\n")

            # Clear the queue
            _telemetry_queue.clear()

            # Try to send the events to PostHog
            send_telemetry_to_posthog()

    except Exception as e:
        logger.error(f"Error in flush_telemetry_queue: {e}")


def send_telemetry_to_posthog() -> None:
    """Send telemetry to PostHog if available."""
    try:
        # Check if telemetry is enabled
        config = get_config()
        if not config.get("telemetry", {}).get("enabled", False):
            return

        # Get the telemetry log path
        arc_dir = ensure_arc_dir()
        log_dir = arc_dir / "log"
        log_path = log_dir / "telemetry.jsonl"

        if not log_path.exists():
            return

        # Try to get PostHog client
        posthog_client = _get_posthog_client()
        if not posthog_client:
            return

        # Read events from the log file
        events = []
        with open(log_path, "r") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        # Send events to PostHog
        for event in events:
            posthog_client.capture(
                distinct_id=event["distinct_id"],
                event=event["event"],
                properties=event["properties"]
            )

        # Ensure events are sent
        posthog_client.flush()

        # Rename the processed log file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_path.rename(log_dir / f"telemetry_{timestamp}.jsonl")

    except Exception as e:
        logger.error(f"Error in send_telemetry_to_posthog: {e}")


def _get_version() -> str:
    """Get the version of the arc-memory package.

    Returns:
        The version string.
    """
    try:
        from arc_memory import __version__
        return __version__
    except (ImportError, AttributeError):
        return "unknown"


def track_cli_command(
    command_name: str,
    subcommand: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error: Optional[Exception] = None,
) -> None:
    """Track CLI command usage.

    This is a convenience function for tracking CLI command usage.

    Args:
        command_name: The name of the command (e.g., 'build', 'auth', 'why').
        subcommand: The name of the subcommand, if any.
        args: The arguments passed to the command.
        success: Whether the command succeeded.
        error: The exception that occurred, if any.
    """
    # Prepare the full command name
    full_command = command_name
    if subcommand:
        full_command = f"{command_name}_{subcommand}"

    # Prepare the context
    context = {}
    if args:
        # Filter out any sensitive information
        safe_args = {}
        for key, value in args.items():
            # Skip sensitive arguments
            if key.lower() in ("token", "password", "secret", "key", "auth"):
                continue
            # Include safe arguments
            safe_args[key] = value
        context.update(safe_args)

    # Track the command usage
    track_command_usage(full_command, success=success, error=error, context=context)


# Register atexit handler to flush telemetry queue
atexit.register(flush_telemetry_queue)
