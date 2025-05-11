"""Scheduler for Arc Memory auto-refresh.

This module provides functionality for scheduling automatic refreshes of the knowledge graph
using the system's native scheduling mechanisms (cron, launchd, Task Scheduler).
"""

import os
import platform
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Union

from arc_memory.config import get_config, update_config
from arc_memory.logging_conf import get_logger
from arc_memory.sql.db import ensure_arc_dir

logger = get_logger(__name__)


def get_scheduler_type() -> str:
    """Get the type of scheduler to use based on the operating system.

    Returns:
        The scheduler type: 'cron' for Linux/macOS, 'task_scheduler' for Windows.
    """
    system = platform.system().lower()
    if system == "darwin":
        return "launchd"
    elif system == "linux":
        return "cron"
    elif system == "windows":
        return "task_scheduler"
    else:
        logger.warning(f"Unknown operating system: {system}, defaulting to cron")
        return "cron"


def get_arc_executable() -> str:
    """Get the path to the Arc Memory executable.

    Returns:
        The path to the Arc Memory executable.
    """
    # If running from a Python module, use the Python executable
    if "python" in sys.executable.lower():
        return f"{sys.executable} -m arc_memory"

    # Otherwise, assume it's installed as a standalone executable
    return "arc"


def get_refresh_command(silent: bool = True) -> str:
    """Get the command to run for refreshing the knowledge graph.

    Args:
        silent: Whether to run the refresh command in silent mode.

    Returns:
        The command to run for refreshing the knowledge graph.
    """
    arc_executable = get_arc_executable()
    silent_flag = "--silent" if silent else ""
    return f"{arc_executable} refresh {silent_flag}"


def schedule_refresh(interval_hours: int = 24) -> bool:
    """Schedule automatic refreshes of the knowledge graph.

    Args:
        interval_hours: The interval in hours between refreshes.

    Returns:
        True if scheduling was successful, False otherwise.
    """
    scheduler_type = get_scheduler_type()
    refresh_command = get_refresh_command(silent=True)

    try:
        if scheduler_type == "cron":
            return _schedule_cron(interval_hours, refresh_command)
        elif scheduler_type == "launchd":
            return _schedule_launchd(interval_hours, refresh_command)
        elif scheduler_type == "task_scheduler":
            return _schedule_task_scheduler(interval_hours, refresh_command)
        else:
            logger.error(f"Unsupported scheduler type: {scheduler_type}")
            return False
    except Exception as e:
        logger.error(f"Failed to schedule refresh: {e}")
        return False


def unschedule_refresh() -> bool:
    """Remove the scheduled auto-refresh task.

    Returns:
        True if unscheduling was successful, False otherwise.
    """
    scheduler_type = get_scheduler_type()

    try:
        if scheduler_type == "cron":
            return _unschedule_cron()
        elif scheduler_type == "launchd":
            return _unschedule_launchd()
        elif scheduler_type == "task_scheduler":
            return _unschedule_task_scheduler()
        else:
            logger.error(f"Unsupported scheduler type: {scheduler_type}")
            return False
    except Exception as e:
        logger.error(f"Failed to unschedule refresh: {e}")
        return False


def is_refresh_scheduled() -> bool:
    """Check if auto-refresh is scheduled.

    Returns:
        True if auto-refresh is scheduled, False otherwise.
    """
    scheduler_type = get_scheduler_type()

    try:
        if scheduler_type == "cron":
            return _is_scheduled_cron()
        elif scheduler_type == "launchd":
            return _is_scheduled_launchd()
        elif scheduler_type == "task_scheduler":
            return _is_scheduled_task_scheduler()
        else:
            logger.error(f"Unsupported scheduler type: {scheduler_type}")
            return False
    except Exception as e:
        logger.error(f"Failed to check if refresh is scheduled: {e}")
        return False


def get_refresh_schedule() -> Optional[Dict[str, Union[str, int]]]:
    """Get the current refresh schedule.

    Returns:
        A dictionary with schedule information, or None if not scheduled.
    """
    if not is_refresh_scheduled():
        return None

    config = get_config()
    interval_hours = config.get("refresh", {}).get("interval_hours", 24)

    # Calculate the next run time (this is an approximation)
    now = datetime.now()
    next_run = now + timedelta(hours=interval_hours)

    return {
        "interval_hours": interval_hours,
        "next_run": next_run.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _schedule_cron(interval_hours: int, command: str) -> bool:
    """Schedule a cron job for auto-refresh on Linux.

    Args:
        interval_hours: The interval in hours between refreshes.
        command: The command to run for refreshing the knowledge graph.

    Returns:
        True if scheduling was successful, False otherwise.
    """
    try:
        # Create a temporary file with the new crontab entry
        temp_file = Path("/tmp/arc_crontab")

        # Get the current crontab
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_crontab = result.stdout if result.returncode == 0 else ""

        # Remove any existing Arc Memory refresh entries
        filtered_lines = [line for line in current_crontab.splitlines()
                         if "arc refresh" not in line and "arc_memory refresh" not in line]

        # Add the new entry
        # Run at a random minute to avoid all users refreshing at the same time
        import random
        minute = random.randint(0, 59)
        hour_expr = f"*/{interval_hours}" if interval_hours < 24 else "0"
        cron_expr = f"{minute} {hour_expr} * * *"

        filtered_lines.append(f"{cron_expr} {command} # Arc Memory auto-refresh")

        # Write the new crontab to the temporary file
        with open(temp_file, "w") as f:
            f.write("\n".join(filtered_lines) + "\n")

        # Install the new crontab
        result = subprocess.run(["crontab", str(temp_file)], capture_output=True, text=True)

        # Clean up
        try:
            temp_file.unlink()
        except FileNotFoundError:
            pass

        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to schedule cron job: {e}")
        return False


def _unschedule_cron() -> bool:
    """Remove the cron job for auto-refresh on Linux.

    Returns:
        True if unscheduling was successful, False otherwise.
    """
    try:
        # Create a temporary file with the new crontab entry
        temp_file = Path("/tmp/arc_crontab")

        # Get the current crontab
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_crontab = result.stdout if result.returncode == 0 else ""

        # Remove any existing Arc Memory refresh entries
        filtered_lines = [line for line in current_crontab.splitlines()
                         if "arc refresh" not in line and "arc_memory refresh" not in line]

        # Write the new crontab to the temporary file
        with open(temp_file, "w") as f:
            f.write("\n".join(filtered_lines) + "\n")

        # Install the new crontab
        result = subprocess.run(["crontab", str(temp_file)], capture_output=True, text=True)

        # Clean up
        try:
            temp_file.unlink()
        except FileNotFoundError:
            pass

        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to unschedule cron job: {e}")
        return False


def _is_scheduled_cron() -> bool:
    """Check if a cron job is scheduled for auto-refresh on Linux.

    Returns:
        True if a cron job is scheduled, False otherwise.
    """
    try:
        # Get the current crontab
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_crontab = result.stdout if result.returncode == 0 else ""

        # Check if there's an Arc Memory refresh entry
        return any("arc refresh" in line or "arc_memory refresh" in line
                  for line in current_crontab.splitlines())
    except Exception as e:
        logger.error(f"Failed to check if cron job is scheduled: {e}")
        return False


def _schedule_launchd(interval_hours: int, command: str) -> bool:
    """Schedule a launchd job for auto-refresh on macOS.

    Args:
        interval_hours: The interval in hours between refreshes.
        command: The command to run for refreshing the knowledge graph.

    Returns:
        True if scheduling was successful, False otherwise.
    """
    try:
        # Create the LaunchAgents directory if it doesn't exist
        launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
        launch_agents_dir.mkdir(parents=True, exist_ok=True)

        # Create the plist file
        plist_path = launch_agents_dir / "io.arc-memory.refresh.plist"

        # Split the command into program and arguments
        parts = command.split()
        program = parts[0]
        args = parts[1:]

        # Create the plist content
        plist_content = (
            f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.arc-memory.refresh</string>
    <key>ProgramArguments</key>
    <array>
        <string>{program}</string>
"""
        )

        for arg in args:
            plist_content += f"        <string>{arg}</string>\n"

        plist_content += (
            f"""    </array>
    <key>StartInterval</key>
    <integer>{interval_hours * 3600}</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{Path.home()}/.arc/refresh.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.arc/refresh.log</string>
</dict>
</plist>
"""
        )

        # Write the plist file
        with open(plist_path, "w") as f:
            f.write(plist_content)

        # Load the plist
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        result = subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True)

        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to schedule launchd job: {e}")
        return False


def _unschedule_launchd() -> bool:
    """Remove the launchd job for auto-refresh on macOS.

    Returns:
        True if unscheduling was successful, False otherwise.
    """
    try:
        # Get the plist path
        plist_path = Path.home() / "Library" / "LaunchAgents" / "io.arc-memory.refresh.plist"

        # Unload the plist if it exists
        if plist_path.exists():
            result = subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
            try:
                plist_path.unlink()
            except FileNotFoundError:
                pass
            return result.returncode == 0

        return True  # Nothing to unschedule
    except Exception as e:
        logger.error(f"Failed to unschedule launchd job: {e}")
        return False


def _is_scheduled_launchd() -> bool:
    """Check if a launchd job is scheduled for auto-refresh on macOS.

    Returns:
        True if a launchd job is scheduled, False otherwise.
    """
    try:
        # Get the plist path
        plist_path = Path.home() / "Library" / "LaunchAgents" / "io.arc-memory.refresh.plist"

        # Check if the plist exists
        if not plist_path.exists():
            return False

        # Check if the job is loaded
        result = subprocess.run(
            ["launchctl", "list", "io.arc-memory.refresh"],
            capture_output=True,
            text=True
        )

        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to check if launchd job is scheduled: {e}")
        return False


def _schedule_task_scheduler(interval_hours: int, command: str) -> bool:
    """Schedule a task for auto-refresh on Windows.

    Args:
        interval_hours: The interval in hours between refreshes.
        command: The command to run for refreshing the knowledge graph.

    Returns:
        True if scheduling was successful, False otherwise.
    """
    try:
        # Split the command into program and arguments
        parts = command.split()
        program = parts[0]
        args = " ".join(parts[1:])

        # Create the task
        task_name = "ArcMemoryAutoRefresh"

        # Remove any existing task with the same name
        subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], capture_output=True)

        # Create the new task
        result = subprocess.run([
            "schtasks", "/Create", "/TN", task_name,
            "/TR", f'"{program}" {args}',
            "/SC", "HOURLY",
            "/MO", str(interval_hours),
            "/ST", "00:00",
            "/RU", "SYSTEM",
            "/F"
        ], capture_output=True)

        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to schedule Windows task: {e}")
        return False


def _unschedule_task_scheduler() -> bool:
    """Remove the scheduled task for auto-refresh on Windows.

    Returns:
        True if unscheduling was successful, False otherwise.
    """
    try:
        # Delete the task
        task_name = "ArcMemoryAutoRefresh"
        result = subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], capture_output=True)

        # Consider it successful if the task was deleted or didn't exist
        return result.returncode == 0 or "The system cannot find the file specified" in result.stderr.decode()
    except Exception as e:
        logger.error(f"Failed to unschedule Windows task: {e}")
        return False


def _is_scheduled_task_scheduler() -> bool:
    """Check if a task is scheduled for auto-refresh on Windows.

    Returns:
        True if a task is scheduled, False otherwise.
    """
    try:
        # Check if the task exists
        task_name = "ArcMemoryAutoRefresh"
        result = subprocess.run(["schtasks", "/Query", "/TN", task_name], capture_output=True)

        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to check if Windows task is scheduled: {e}")
        return False
