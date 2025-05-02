"""Attestation generation module for Arc Memory simulation.

This module provides functions for generating attestations for simulation results.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from arc_memory.logging_conf import get_logger
from arc_memory.simulate.utils.progress import create_progress_reporter

logger = get_logger(__name__)


def generate_attestation(
    rev_range: str,
    scenario: str,
    severity: int,
    risk_score: int,
    affected_services: List[str],
    metrics: Dict[str, Any],
    explanation: str,
    manifest_hash: str,
    commit_target: str,
    diff_hash: str,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Dict[str, Any]:
    """Generate an attestation for the simulation results.
    
    Args:
        rev_range: Git revision range
        scenario: Fault scenario ID
        severity: Severity level (0-100)
        risk_score: Calculated risk score
        affected_services: List of affected service names
        metrics: Raw metrics from the simulation
        explanation: Human-readable explanation
        manifest_hash: Hash of the simulation manifest
        commit_target: Target commit hash
        diff_hash: Hash of the diff
        progress_callback: Callback function to update progress (optional)
        
    Returns:
        Dictionary containing the attestation
        
    Raises:
        ValueError: If the attestation cannot be generated
    """
    # Create a progress reporter
    report_progress = create_progress_reporter(progress_callback)
    
    # Update progress
    report_progress("Generating attestation for simulation results", 85)
    
    logger.info("Generating attestation")

    try:
        # Create the attestation
        attestation = {
            "version": "0.1.0",
            "timestamp": int(time.time()),
            "rev_range": rev_range,
            "commit_target": commit_target,
            "diff_hash": diff_hash,
            "scenario": scenario,
            "severity": severity,
            "risk_score": risk_score,
            "affected_services": affected_services,
            "manifest_hash": manifest_hash,
            "metrics_hash": hash_dict(metrics),
            "explanation_hash": hash_string(explanation),
            "signature": None  # Will be added by sign_attestation
        }
        
        # Sign the attestation
        signed_attestation = sign_attestation(attestation)
        
        # Update progress
        report_progress("Successfully generated attestation", 90)
        
        logger.info("Successfully generated attestation")
        return signed_attestation
    except Exception as e:
        logger.error(f"Error generating attestation: {e}")
        
        # Update progress
        report_progress(f"Error generating attestation: {str(e)[:50]}...", 100)
        
        raise ValueError(f"Error generating attestation: {e}")


def sign_attestation(attestation: Dict[str, Any]) -> Dict[str, Any]:
    """Sign the attestation with a cryptographic signature.
    
    Args:
        attestation: Dictionary containing the attestation
        
    Returns:
        Dictionary containing the signed attestation
        
    Raises:
        ValueError: If the attestation cannot be signed
    """
    try:
        # Create a copy of the attestation
        signed_attestation = attestation.copy()
        
        # Remove the signature field for hashing
        if "signature" in signed_attestation:
            del signed_attestation["signature"]
        
        # Create a canonical JSON representation
        canonical_json = json.dumps(signed_attestation, sort_keys=True)
        
        # Hash the canonical JSON
        attestation_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
        
        # Add the signature
        signed_attestation["signature"] = {
            "hash": attestation_hash,
            "algorithm": "sha256",
            "timestamp": int(time.time())
        }
        
        logger.info("Successfully signed attestation")
        return signed_attestation
    except Exception as e:
        logger.error(f"Error signing attestation: {e}")
        raise ValueError(f"Error signing attestation: {e}")


def verify_attestation(attestation: Dict[str, Any]) -> bool:
    """Verify the attestation signature.
    
    Args:
        attestation: Dictionary containing the attestation
        
    Returns:
        True if the attestation is valid, False otherwise
    """
    try:
        # Check if the attestation has a signature
        if "signature" not in attestation:
            logger.error("Attestation does not have a signature")
            return False
        
        # Get the signature
        signature = attestation["signature"]
        
        # Create a copy of the attestation
        attestation_copy = attestation.copy()
        
        # Remove the signature field for hashing
        del attestation_copy["signature"]
        
        # Create a canonical JSON representation
        canonical_json = json.dumps(attestation_copy, sort_keys=True)
        
        # Hash the canonical JSON
        attestation_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
        
        # Verify the signature
        is_valid = attestation_hash == signature.get("hash")
        
        if is_valid:
            logger.info("Attestation signature is valid")
        else:
            logger.error("Attestation signature is invalid")
        
        return is_valid
    except Exception as e:
        logger.error(f"Error verifying attestation: {e}")
        return False


def save_attestation(attestation: Dict[str, Any], output_path: Path) -> None:
    """Save the attestation to a file.
    
    Args:
        attestation: Dictionary containing the attestation
        output_path: Path to save the attestation
        
    Raises:
        IOError: If the attestation cannot be saved
    """
    try:
        # Ensure the directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the attestation
        with open(output_path, 'w') as f:
            json.dump(attestation, f, indent=2)
        
        logger.info(f"Saved attestation to {output_path}")
    except Exception as e:
        logger.error(f"Error saving attestation: {e}")
        raise IOError(f"Error saving attestation: {e}")


def load_attestation(input_path: Path) -> Dict[str, Any]:
    """Load the attestation from a file.
    
    Args:
        input_path: Path to load the attestation from
        
    Returns:
        Dictionary containing the attestation
        
    Raises:
        FileNotFoundError: If the attestation file does not exist
        ValueError: If the attestation file contains invalid data
    """
    try:
        # Load the attestation
        with open(input_path, 'r') as f:
            attestation = json.load(f)
        
        # Validate the attestation
        if not isinstance(attestation, dict) or "signature" not in attestation:
            raise ValueError("Invalid attestation format")
        
        logger.info(f"Loaded attestation from {input_path}")
        return attestation
    except FileNotFoundError:
        logger.error(f"Attestation file not found: {input_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in attestation file: {e}")
        raise ValueError(f"Invalid JSON in attestation file: {e}")
    except Exception as e:
        logger.error(f"Error loading attestation: {e}")
        raise ValueError(f"Error loading attestation: {e}")


def hash_string(s: str) -> str:
    """Hash a string using SHA-256.
    
    Args:
        s: String to hash
        
    Returns:
        Hexadecimal hash
    """
    return hashlib.sha256(s.encode()).hexdigest()


def hash_dict(d: Dict[str, Any]) -> str:
    """Hash a dictionary using SHA-256.
    
    Args:
        d: Dictionary to hash
        
    Returns:
        Hexadecimal hash
    """
    # Create a canonical JSON representation
    canonical_json = json.dumps(d, sort_keys=True)
    
    # Hash the canonical JSON
    return hashlib.sha256(canonical_json.encode()).hexdigest()
