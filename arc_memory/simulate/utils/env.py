"""Utilities for environment variable management."""

import os
from pathlib import Path
from dotenv import load_dotenv

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def ensure_env_loaded(dotenv_path: str | None = None) -> None:
    """Load environment variables from .env files.
    
    This function loads environment variables from the following sources in order:
    1. The specified dotenv_path (if provided)
    2. The default .env file
    3. The .env.test file (if it exists and variables are still missing)
    
    Args:
        dotenv_path: Optional path to a specific .env file to load
    """
    # First pass: user-supplied or default .env
    default_env = Path(".env")
    if dotenv_path:
        logger.info(f"Loading environment from {dotenv_path}")
        load_dotenv(dotenv_path, override=False)
    elif default_env.exists():
        logger.info(f"Loading environment from {default_env.absolute()}")
        load_dotenv(default_env, override=False)
    
    # Second pass: .env.test only if it exists and vars still missing
    test_env = Path(".env.test")
    if test_env.exists():
        logger.info(f"Loading environment from {test_env.absolute()}")
        load_dotenv(test_env, override=False)


def get_api_key(api_key: str | None = None, env_var: str = "OPENAI_API_KEY") -> str:
    """Get API key from the provided value or environment variable.
    
    Args:
        api_key: Optional API key provided directly
        env_var: Environment variable name to check if api_key is not provided
        
    Returns:
        The API key
        
    Raises:
        ValueError: If the API key is not found
    """
    # Ensure environment is loaded
    ensure_env_loaded()
    
    # Use provided API key or get from environment
    result = api_key or os.environ.get(env_var)
    
    # Validate API key
    if not result:
        raise ValueError(f"{env_var} not found in environment variables or .env file.")
    
    # Log API key (first and last 4 characters)
    logger.info(f"Using {env_var}: {result[:4]}...{result[-4:]}")
    
    return result
