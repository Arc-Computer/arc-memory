"""Progress reporting utilities for Arc Memory simulation.

This module provides utilities for reporting progress during simulation.
"""

from typing import Callable, Optional

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def create_progress_reporter(
    progress_callback: Optional[Callable[[str, int], None]] = None,
    verbose: bool = False
) -> Callable[[str, int], None]:
    """Create a progress reporter function.
    
    Args:
        progress_callback: Optional callback function to report progress
        verbose: Whether to log progress messages
        
    Returns:
        A function that reports progress
    """
    def report_progress(message: str, percentage: int) -> None:
        """Report progress.
        
        Args:
            message: Progress message
            percentage: Progress percentage (0-100)
        """
        # Call the progress callback if provided
        if progress_callback:
            progress_callback(message, percentage)
        
        # Log the progress message if verbose
        if verbose:
            logger.info(f"Progress [{percentage}%]: {message}")
    
    return report_progress
