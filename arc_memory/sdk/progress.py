"""Progress reporting functionality for Arc Memory SDK.

This module provides progress reporting functionality for Arc Memory SDK methods,
allowing for real-time feedback during long-running operations.
"""

from enum import Enum
from typing import Any, Callable, Dict, Optional

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


class ProgressStage(str, Enum):
    """Stages of progress for SDK operations."""

    INITIALIZING = "initializing"
    QUERYING = "querying"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETING = "completing"


class ProgressCallback:
    """Callback for reporting progress during SDK operations.

    This class provides a standardized way to report progress during long-running
    SDK operations, allowing for real-time feedback to users.
    """

    def __call__(
        self,
        stage: ProgressStage,
        message: str,
        progress: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Report progress.

        Args:
            stage: The current stage of the operation.
            message: A human-readable message describing the current progress.
            progress: A float between 0.0 and 1.0 indicating the overall progress.
            metadata: Additional metadata about the progress.
        """
        pass


class LoggingProgressCallback(ProgressCallback):
    """Progress callback that logs progress to the logger.

    This is a simple implementation of ProgressCallback that logs progress
    messages to the logger.
    """

    def __call__(
        self,
        stage: ProgressStage,
        message: str,
        progress: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Report progress by logging to the logger.

        Args:
            stage: The current stage of the operation.
            message: A human-readable message describing the current progress.
            progress: A float between 0.0 and 1.0 indicating the overall progress.
            metadata: Additional metadata about the progress.
        """
        logger.info(f"[{stage.value}] {message} ({progress:.0%})")
