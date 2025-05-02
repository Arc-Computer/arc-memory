"""Diff extraction and analysis module for Arc Memory simulation.

This module provides functions for extracting and analyzing Git diffs to identify
affected files and services for simulation.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from arc_memory.logging_conf import get_logger
from arc_memory.simulate.diff_utils import serialize_diff as _serialize_diff
from arc_memory.simulate.diff_utils import analyze_diff as _analyze_diff
from arc_memory.simulate.diff_utils import GitError

logger = get_logger(__name__)


def extract_diff(
    rev_range: str,
    repo_path: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Dict[str, Any]:
    """Extract the diff for the given rev-range.
    
    Args:
        rev_range: Git revision range
        repo_path: Path to the repository (default: current directory)
        progress_callback: Callback function to update progress (optional)
        
    Returns:
        Dictionary containing the diff data
        
    Raises:
        GitError: If there's an error accessing the Git repository
    """
    # Update progress if callback is available
    if progress_callback:
        progress_callback(f"Extracting diff for range: {rev_range}", 10)
        
    logger.info(f"Extracting diff for range: {rev_range}")

    try:
        # Extract the diff
        diff_data = _serialize_diff(rev_range, repo_path=Path(repo_path) if repo_path else None)
        
        # Update progress if callback is available
        if progress_callback:
            progress_callback(f"Successfully extracted diff with {len(diff_data.get('files', []))} files", 15)

        logger.info(f"Successfully extracted diff with {len(diff_data.get('files', []))} files")
        return diff_data
    except GitError as e:
        logger.error(f"Git error: {e}")
        
        # Update progress if callback is available
        if progress_callback:
            progress_callback(f"Git error: {str(e)[:50]}...", 100)
            
        raise
    except Exception as e:
        logger.error(f"Error extracting diff: {e}")
        
        # Update progress if callback is available
        if progress_callback:
            progress_callback(f"Error extracting diff: {str(e)[:50]}...", 100)
            
        raise GitError(f"Error extracting diff: {e}")


def analyze_changes(
    diff_data: Dict[str, Any],
    db_path: str,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> List[str]:
    """Analyze the diff to identify affected services.
    
    Args:
        diff_data: Dictionary containing the diff data
        db_path: Path to the knowledge graph database
        progress_callback: Callback function to update progress (optional)
        
    Returns:
        List of affected service names
        
    Raises:
        ValueError: If the diff data is invalid
    """
    # Update progress if callback is available
    if progress_callback:
        progress_callback("Analyzing diff to identify affected services", 20)
        
    logger.info("Analyzing diff to identify affected services")

    try:
        # Check if we have diff data
        if not diff_data or "files" not in diff_data:
            error_msg = "No valid diff data available for analysis"
            logger.error(error_msg)
            
            # Update progress if callback is available
            if progress_callback:
                progress_callback(error_msg, 100)
                
            raise ValueError(error_msg)

        # Analyze the diff
        affected_services = _analyze_diff(diff_data, db_path)
        
        # Update progress if callback is available
        if progress_callback:
            progress_callback(f"Identified {len(affected_services)} affected services", 25)

        logger.info(f"Identified {len(affected_services)} affected services")
        return affected_services
    except Exception as e:
        logger.error(f"Error analyzing diff: {e}")
        
        # Update progress if callback is available
        if progress_callback:
            progress_callback(f"Error analyzing diff: {str(e)[:50]}...", 100)
            
        raise ValueError(f"Error analyzing diff: {e}")


def save_diff_to_file(diff_data: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
    """Save the diff data to a file.
    
    Args:
        diff_data: Dictionary containing the diff data
        output_path: Path to save the diff data (default: temporary file)
        
    Returns:
        Path to the saved diff file
        
    Raises:
        IOError: If the diff data cannot be saved
    """
    try:
        # Create a temporary file if output_path is not provided
        if output_path is None:
            from tempfile import NamedTemporaryFile
            
            with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(diff_data, f, indent=2)
                output_path = Path(f.name)
        else:
            # Ensure the directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the diff data
            with open(output_path, 'w') as f:
                json.dump(diff_data, f, indent=2)
        
        logger.info(f"Saved diff data to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error saving diff data: {e}")
        raise IOError(f"Error saving diff data: {e}")


def load_diff_from_file(diff_path: Path) -> Dict[str, Any]:
    """Load the diff data from a file.
    
    Args:
        diff_path: Path to the diff file
        
    Returns:
        Dictionary containing the diff data
        
    Raises:
        FileNotFoundError: If the diff file does not exist
        ValueError: If the diff file contains invalid data
    """
    try:
        # Load the diff data
        with open(diff_path, 'r') as f:
            diff_data = json.load(f)
        
        # Validate the diff data
        if not isinstance(diff_data, dict) or "files" not in diff_data:
            raise ValueError("Invalid diff data format")
        
        logger.info(f"Loaded diff data from {diff_path}")
        return diff_data
    except FileNotFoundError:
        logger.error(f"Diff file not found: {diff_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in diff file: {e}")
        raise ValueError(f"Invalid JSON in diff file: {e}")
    except Exception as e:
        logger.error(f"Error loading diff data: {e}")
        raise ValueError(f"Error loading diff data: {e}")
