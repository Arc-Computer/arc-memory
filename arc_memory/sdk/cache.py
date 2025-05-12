"""Caching functionality for Arc Memory SDK.

This module provides caching functionality for Arc Memory SDK methods,
allowing for efficient reuse of query results.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Type variable for the cached function
T = TypeVar("T")


def get_cache_dir() -> Path:
    """Get the cache directory.

    Returns:
        The path to the cache directory.
    """
    from arc_memory.sql.db import ensure_arc_dir
    arc_dir = ensure_arc_dir()
    cache_dir = arc_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def cache_key(func_name: str, args: tuple, kwargs: Dict[str, Any]) -> str:
    """Generate a cache key for a function call.

    Args:
        func_name: The name of the function.
        args: The positional arguments.
        kwargs: The keyword arguments.

    Returns:
        A cache key string.
    """
    # Convert args and kwargs to a JSON-serializable format
    serializable_args = []
    for arg in args:
        if isinstance(arg, Path):
            serializable_args.append(str(arg))
        else:
            serializable_args.append(arg)

    serializable_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, Path):
            serializable_kwargs[key] = str(value)
        elif key == "callback":  # Skip callback parameter
            continue
        else:
            serializable_kwargs[key] = value

    # Create a dictionary with the function name, args, and kwargs
    cache_dict = {
        "func": func_name,
        "args": serializable_args,
        "kwargs": serializable_kwargs
    }

    # Convert to JSON and hash
    cache_json = json.dumps(cache_dict, sort_keys=True, default=str)
    return hashlib.md5(cache_json.encode()).hexdigest()


def cached(ttl: timedelta = timedelta(hours=1)) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for caching function results.

    Args:
        ttl: Time-to-live for cached results.

    Returns:
        A decorator function.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Check if caching is enabled
            cache_enabled = kwargs.pop("cache", True) if "cache" in kwargs else True
            if not cache_enabled:
                return func(*args, **kwargs)

            # Generate cache key
            key = cache_key(func.__name__, args, kwargs)
            cache_file = get_cache_dir() / f"{key}.json"

            # Check if cache file exists and is not expired
            if cache_file.exists():
                try:
                    with open(cache_file, "r") as f:
                        cache_data = json.load(f)

                    # Check if cache is expired
                    cache_time = datetime.fromisoformat(cache_data["timestamp"])
                    if datetime.now() - cache_time < ttl:
                        logger.debug(f"Cache hit for {func.__name__}")
                        return cast(T, cache_data["result"])
                except Exception as e:
                    logger.warning(f"Error reading cache: {e}")

            # Call the function
            result = func(*args, **kwargs)

            # Save to cache
            try:
                cache_data = {
                    "timestamp": datetime.now().isoformat(),
                    "result": result
                }
                with open(cache_file, "w") as f:
                    json.dump(cache_data, f, default=str)
            except Exception as e:
                logger.warning(f"Error writing cache: {e}")

            return result
        return wrapper
    return decorator
