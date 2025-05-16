"""
Utility functions for the Simple Code Time Machine demo.
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def print_header(title: str) -> None:
    """Print a header with the given title.

    Args:
        title: The title to print
    """
    width = min(os.get_terminal_size().columns, 80)
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width + "\n")


def print_section(title: str) -> None:
    """Print a section header with the given title.

    Args:
        title: The title to print
    """
    width = min(os.get_terminal_size().columns, 80)
    print("\n" + "-" * width)
    print(title)
    print("-" * width + "\n")


def format_date(date_str: str) -> str:
    """Format a date string for display.

    Args:
        date_str: The date string to format

    Returns:
        A formatted date string
    """
    try:
        if isinstance(date_str, datetime):
            return date_str.strftime("%Y-%m-%d")
        elif "T" in date_str:
            # ISO format
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        else:
            # Try different formats
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
    except Exception:
        pass
    
    # Return original if parsing fails
    return date_str


def get_entity_property(entity: Any, property_name: str, default: Any = None) -> Any:
    """Get a property from an entity, handling different entity types.

    Args:
        entity: The entity to get the property from
        property_name: The name of the property to get
        default: The default value to return if the property is not found

    Returns:
        The property value or the default value
    """
    # Handle dictionary-like entities
    if hasattr(entity, "get"):
        return entity.get(property_name, default)
    
    # Handle object-like entities
    if hasattr(entity, property_name):
        return getattr(entity, property_name)
    
    # Handle entities with properties dict
    if hasattr(entity, "properties") and isinstance(entity.properties, dict):
        return entity.properties.get(property_name, default)
    
    return default


def truncate_text(text: str, max_length: int = 80) -> str:
    """Truncate text to the specified maximum length.

    Args:
        text: The text to truncate
        max_length: The maximum length of the text

    Returns:
        The truncated text
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def extract_author(entity: Any) -> str:
    """Extract the author from an entity.

    Args:
        entity: The entity to extract the author from

    Returns:
        The author name
    """
    # Try different property names for author
    for prop in ["author", "user", "creator", "owner"]:
        author = get_entity_property(entity, prop)
        if author:
            # If author is an object, try to get the name
            if isinstance(author, dict):
                return author.get("name", author.get("login", str(author)))
            elif hasattr(author, "name"):
                return author.name
            elif hasattr(author, "login"):
                return author.login
            return str(author)
    
    return "Unknown"


def extract_title(entity: Any) -> str:
    """Extract the title from an entity.

    Args:
        entity: The entity to extract the title from

    Returns:
        The entity title
    """
    # Try different property names for title
    for prop in ["title", "name", "message", "summary"]:
        title = get_entity_property(entity, prop)
        if title:
            return truncate_text(str(title))
    
    # If no title is found, use the ID
    entity_id = get_entity_property(entity, "id", "Unknown")
    return f"Entity {entity_id}"
