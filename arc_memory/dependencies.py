"""Dependency checking for Arc Memory."""

import importlib
import sys
from typing import Dict, List, Tuple

from arc_memory.errors import DependencyError
from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Core dependencies that are required for basic functionality
CORE_DEPENDENCIES = [
    "networkx",
    "apsw",
    "pydantic",
    "zstandard",
]

# Optional dependencies for specific features
OPTIONAL_DEPENDENCIES = {
    "github": ["requests", "pyjwt", "cryptography", "keyring"],
    "cli": ["typer", "rich", "tqdm"],
    "git": ["gitpython"],
    "adr": ["pyyaml", "markdown_it_py"],
}


def check_dependency(name: str) -> bool:
    """Check if a dependency is installed.

    Args:
        name: The name of the dependency.

    Returns:
        True if the dependency is installed, False otherwise.
    """
    try:
        importlib.import_module(name.replace("-", "_"))
        return True
    except ImportError:
        return False


def check_dependencies(include_optional: bool = True) -> Tuple[bool, Dict[str, List[str]]]:
    """Check if all required dependencies are installed.

    Args:
        include_optional: Whether to check optional dependencies.

    Returns:
        A tuple of (success, missing_dependencies).
    """
    missing_dependencies = {}

    # Check core dependencies
    missing_core = [dep for dep in CORE_DEPENDENCIES if not check_dependency(dep)]
    if missing_core:
        missing_dependencies["core"] = missing_core

    # Check optional dependencies
    if include_optional:
        for category, deps in OPTIONAL_DEPENDENCIES.items():
            missing_optional = [dep for dep in deps if not check_dependency(dep)]
            if missing_optional:
                missing_dependencies[category] = missing_optional

    return len(missing_dependencies) == 0, missing_dependencies


def validate_dependencies(include_optional: bool = True, raise_error: bool = True) -> Dict[str, List[str]]:
    """Validate that all required dependencies are installed.

    Args:
        include_optional: Whether to check optional dependencies.
        raise_error: Whether to raise an error if dependencies are missing.

    Returns:
        A dictionary of missing dependencies by category.

    Raises:
        DependencyError: If core dependencies are missing and raise_error is True.
    """
    success, missing_dependencies = check_dependencies(include_optional)

    if not success:
        # Format error message
        error_msg = "Missing dependencies:"
        for category, deps in missing_dependencies.items():
            deps_str = ", ".join(deps)
            error_msg += f"\n  {category}: {deps_str}"

        # Add installation instructions
        error_msg += "\n\nTo install missing dependencies, run:"

        if "core" in missing_dependencies:
            core_deps = " ".join(missing_dependencies["core"])
            error_msg += f"\n  pip install {core_deps}"

        for category, deps in missing_dependencies.items():
            if category != "core":
                deps_str = " ".join(deps)
                error_msg += f"\n  pip install {deps_str}  # Optional {category} dependencies"

        logger.error(error_msg)

        # Only raise an error if core dependencies are missing
        if raise_error and "core" in missing_dependencies:
            raise DependencyError(
                "Missing required core dependencies",
                details={"missing_dependencies": missing_dependencies}
            )
        # For optional dependencies, just log a warning
        elif include_optional and any(category != "core" for category in missing_dependencies):
            logger.warning("Some optional dependencies are missing. Functionality may be limited.")

    return missing_dependencies


def get_python_version() -> Tuple[int, int, int]:
    """Get the current Python version.

    Returns:
        A tuple of (major, minor, micro).
    """
    return sys.version_info[:3]


def check_python_version(min_version: Tuple[int, int, int] = (3, 10, 0)) -> bool:
    """Check if the current Python version meets the minimum requirements.

    Args:
        min_version: The minimum required version as a tuple of (major, minor, micro).

    Returns:
        True if the current version meets the requirements, False otherwise.
    """
    current_version = get_python_version()
    return current_version >= min_version


def validate_python_version(min_version: Tuple[int, int, int] = (3, 10, 0), raise_error: bool = True) -> bool:
    """Validate that the current Python version meets the minimum requirements.

    Args:
        min_version: The minimum required version as a tuple of (major, minor, micro).
        raise_error: Whether to raise an error if the version is too old.

    Returns:
        True if the current version meets the requirements, False otherwise.

    Raises:
        DependencyError: If the version is too old and raise_error is True.
    """
    if not check_python_version(min_version):
        current_version = get_python_version()
        min_version_str = ".".join(str(v) for v in min_version)
        current_version_str = ".".join(str(v) for v in current_version)

        error_msg = (
            f"Python version {current_version_str} is too old. "
            f"Arc Memory requires Python {min_version_str} or newer."
        )

        logger.error(error_msg)

        if raise_error:
            raise DependencyError(
                error_msg,
                details={
                    "current_version": current_version_str,
                    "required_version": min_version_str,
                }
            )

        return False

    return True
