"""Telemetry functionality for Arc Memory.

This module provides functions for tracking usage and measuring MTTR improvements.
"""

import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from arc_memory.config import get_config, update_config
from arc_memory.logging_conf import get_logger
from arc_memory.sql.db import ensure_arc_dir

logger = get_logger(__name__)

# Queue for telemetry events
_telemetry_queue: List[Dict[str, Any]] = []
_telemetry_lock = threading.Lock()


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
            "session_id": session_id
        }

        # Add context if provided (file path, line number, etc.)
        if context:
            properties.update(context)

        # Add to telemetry queue
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
            "timestamp": datetime.now().isoformat()
        }

        # Add to telemetry queue
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

    except Exception as e:
        logger.error(f"Error in flush_telemetry_queue: {e}")


def send_telemetry_to_posthog() -> None:
    """Send telemetry to PostHog if available."""
    try:
        # Check if PostHog is installed
        try:
            import posthog
        except ImportError:
            logger.debug("PostHog not installed, skipping telemetry upload")
            return

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

        # Initialize PostHog client
        posthog.api_key = "phc_YOUR_PROJECT_KEY"  # Replace with actual key in production
        posthog.host = "https://app.posthog.com"  # Or your self-hosted instance
        posthog.disable_geoip = True  # Don't track server IP location

        # Read events from the log file
        events = []
        with open(log_path, "r") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        # Send events to PostHog
        for event in events:
            posthog.capture(
                distinct_id=event["distinct_id"],
                event=event["event"],
                properties=event["properties"]
            )

        # Ensure events are sent
        posthog.flush()

        # Rename the processed log file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_path.rename(log_dir / f"telemetry_{timestamp}.jsonl")

    except Exception as e:
        logger.error(f"Error in send_telemetry_to_posthog: {e}")


# Register atexit handler to flush telemetry queue
import atexit
atexit.register(flush_telemetry_queue)
