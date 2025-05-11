"""Configuration management for Arc Memory.

This module provides functions for loading and saving configuration settings.
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict

from arc_memory.logging_conf import get_logger
from arc_memory.sql.db import ensure_arc_dir

logger = get_logger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "telemetry": {
        "enabled": False,  # Opt-in by default (disabled until explicitly enabled)
        "installation_id": str(uuid.uuid4()),  # Anonymous installation ID
        "current_session_id": None,  # Current investigation session ID
    },
    "github": {
        "token": None,  # GitHub token for API calls
    },
    "mcp": {
        "host": "127.0.0.1",
        "port": 8000,
    },
    "refresh": {
        "interval_hours": 24,  # Default refresh interval in hours
        "scheduled": False,  # Whether auto-refresh is scheduled
        "last_run": None,  # Last time auto-refresh was run
    },
    "database": {
        "adapter": "sqlite",  # Default database adapter
    }
}


def get_config_path() -> Path:
    """Get the path to the configuration file.

    Returns:
        Path to the configuration file.
    """
    arc_dir = ensure_arc_dir()
    return arc_dir / "config.json"


def get_config() -> Dict[str, Any]:
    """Get the configuration settings.

    Returns:
        The configuration settings.
    """
    config_path = get_config_path()

    # If the config file doesn't exist, create it with default settings
    if not config_path.exists():
        return save_config(DEFAULT_CONFIG)

    # Load the config file
    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        # Ensure all default keys exist
        for section, values in DEFAULT_CONFIG.items():
            if section not in config:
                config[section] = {}
            for key, value in values.items():
                if key not in config[section]:
                    config[section][key] = value

        return config
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        return DEFAULT_CONFIG


def save_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Save the configuration settings.

    Args:
        config: The configuration settings to save.

    Returns:
        The saved configuration settings.
    """
    config_path = get_config_path()

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return config
    except Exception as e:
        logger.error(f"Failed to save config file: {e}")
        return config


def update_config(section: str, key: str, value: Any) -> Dict[str, Any]:
    """Update a specific configuration setting.

    Args:
        section: The configuration section.
        key: The configuration key.
        value: The new value.

    Returns:
        The updated configuration settings.
    """
    config = get_config()
    if section not in config:
        config[section] = {}
    config[section][key] = value
    return save_config(config)


def get_config_value(section: str, key: str, default: Any = None) -> Any:
    """Get a specific configuration value.

    Args:
        section: The configuration section.
        key: The configuration key.
        default: The default value to return if the key doesn't exist.

    Returns:
        The configuration value, or the default if not found.
    """
    config = get_config()
    return config.get(section, {}).get(key, default)
