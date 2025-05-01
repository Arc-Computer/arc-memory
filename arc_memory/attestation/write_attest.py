"""Attestation generation for Arc Memory simulations.

This module provides functionality for generating cryptographically verifiable
attestations for simulation results, ensuring the integrity and provenance
of simulation data.
"""

import json
import hashlib
import hmac
import base64
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union

from arc_memory.logging_conf import get_logger
from arc_memory.sql.db import ensure_arc_dir

logger = get_logger(__name__)


def generate_attestation_id(rev_range: str, timestamp: Optional[str] = None) -> str:
    """Generate a unique attestation ID.

    Args:
        rev_range: Git rev-range used for the simulation
        timestamp: Optional timestamp to include in the ID

    Returns:
        A unique attestation ID
    """
    # Clean up the rev_range to make it suitable for a filename
    clean_range = rev_range.replace("..", "_").replace("/", "_")
    
    # Add timestamp if provided
    if timestamp:
        # Extract just the date part if it's an ISO format timestamp
        if "T" in timestamp:
            date_part = timestamp.split("T")[0]
            return f"sim_{clean_range}_{date_part}"
    
    return f"sim_{clean_range}"


def calculate_content_hash(content: Dict[str, Any]) -> str:
    """Calculate a hash of the content.

    Args:
        content: The content to hash

    Returns:
        A hex digest of the content hash
    """
    # Sort keys to ensure consistent hashing
    content_str = json.dumps(content, sort_keys=True)
    return hashlib.sha256(content_str.encode('utf-8')).hexdigest()


def sign_attestation(attestation: Dict[str, Any]) -> Dict[str, Any]:
    """Sign the attestation with a cryptographic signature.

    Args:
        attestation: The attestation to sign

    Returns:
        The attestation with added signature
    """
    # Create a copy of the attestation without the signature field
    content_to_sign = {k: v for k, v in attestation.items() if k != "signature"}
    
    # Calculate content hash
    content_hash = calculate_content_hash(content_to_sign)
    
    # Get signing key from environment or use a default for development
    signing_key = os.environ.get("ARC_SIGNING_KEY", "development_signing_key")
    
    # Create HMAC signature
    signature = hmac.new(
        signing_key.encode('utf-8'),
        content_hash.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Add signature to attestation
    signed_attestation = attestation.copy()
    signed_attestation["signature"] = {
        "algorithm": "hmac-sha256",
        "value": signature,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    return signed_attestation


def create_attestation(
    rev_range: str,
    scenario: str,
    severity: int,
    affected_services: list,
    metrics: Dict[str, Any],
    risk_score: int,
    explanation: str,
    manifest_hash: str,
    commit_target: str,
    timestamp: str,
    diff_hash: str,
    simulation_results: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an attestation for simulation results.

    Args:
        rev_range: Git rev-range used for the simulation
        scenario: The fault scenario that was simulated
        severity: The severity level of the simulation (0-100)
        affected_services: List of services affected by the changes
        metrics: Processed metrics from simulation
        risk_score: Calculated risk score (0-100)
        explanation: Human-readable explanation of results
        manifest_hash: Hash of the simulation manifest
        commit_target: Target commit hash
        timestamp: Timestamp of the simulation
        diff_hash: Hash of the diff
        simulation_results: Optional raw simulation results

    Returns:
        A signed attestation dictionary
    """
    # Generate attestation ID
    sim_id = generate_attestation_id(rev_range, timestamp)
    
    # Create the attestation
    attestation = {
        "sim_id": sim_id,
        "version": "1.0.0",
        "rev_range": rev_range,
        "scenario": scenario,
        "severity": severity,
        "affected_services": affected_services,
        "metrics": metrics,
        "risk_score": risk_score,
        "explanation": explanation,
        "manifest_hash": manifest_hash,
        "commit_target": commit_target,
        "timestamp": timestamp,
        "diff_hash": diff_hash
    }
    
    # Add simulation results hash if provided
    if simulation_results:
        attestation["simulation_results_hash"] = calculate_content_hash(simulation_results)
    
    # Sign the attestation
    signed_attestation = sign_attestation(attestation)
    
    return signed_attestation


def save_attestation(
    attestation: Dict[str, Any],
    output_path: Optional[Union[str, Path]] = None
) -> Path:
    """Save the attestation to a file.

    Args:
        attestation: The attestation to save
        output_path: Optional path to save the attestation to

    Returns:
        The path where the attestation was saved
    """
    # Get the attestation ID
    sim_id = attestation["sim_id"]
    
    # Determine the output path
    if output_path:
        attest_path = Path(output_path)
    else:
        # Use default location in .arc/.attest directory
        arc_dir = ensure_arc_dir()
        attest_dir = arc_dir / ".attest"
        attest_dir.mkdir(exist_ok=True)
        attest_path = attest_dir / f"{sim_id}.json"
    
    # Save the attestation
    with open(attest_path, 'w') as f:
        json.dump(attestation, f, indent=2)
    
    logger.info(f"Saved attestation to {attest_path}")
    return attest_path


def verify_attestation(attestation: Dict[str, Any]) -> bool:
    """Verify the signature of an attestation.

    Args:
        attestation: The attestation to verify

    Returns:
        True if the signature is valid, False otherwise
    """
    # Extract the signature
    if "signature" not in attestation:
        logger.warning("Attestation has no signature")
        return False
    
    signature = attestation["signature"]
    if "value" not in signature or "algorithm" not in signature:
        logger.warning("Invalid signature format")
        return False
    
    # Check the algorithm
    if signature["algorithm"] != "hmac-sha256":
        logger.warning(f"Unsupported signature algorithm: {signature['algorithm']}")
        return False
    
    # Create a copy of the attestation without the signature field
    content_to_verify = {k: v for k, v in attestation.items() if k != "signature"}
    
    # Calculate content hash
    content_hash = calculate_content_hash(content_to_verify)
    
    # Get signing key from environment or use a default for development
    signing_key = os.environ.get("ARC_SIGNING_KEY", "development_signing_key")
    
    # Create HMAC signature
    expected_signature = hmac.new(
        signing_key.encode('utf-8'),
        content_hash.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    if signature["value"] == expected_signature:
        logger.info("Attestation signature verified")
        return True
    else:
        logger.warning("Invalid attestation signature")
        return False


def generate_and_save_attestation(
    rev_range: str,
    scenario: str,
    severity: int,
    affected_services: list,
    metrics: Dict[str, Any],
    risk_score: int,
    explanation: str,
    manifest_hash: str,
    commit_target: str,
    timestamp: str,
    diff_hash: str,
    simulation_results: Optional[Dict[str, Any]] = None,
    output_path: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """Generate and save an attestation for simulation results.

    Args:
        rev_range: Git rev-range used for the simulation
        scenario: The fault scenario that was simulated
        severity: The severity level of the simulation (0-100)
        affected_services: List of services affected by the changes
        metrics: Processed metrics from simulation
        risk_score: Calculated risk score (0-100)
        explanation: Human-readable explanation of results
        manifest_hash: Hash of the simulation manifest
        commit_target: Target commit hash
        timestamp: Timestamp of the simulation
        diff_hash: Hash of the diff
        simulation_results: Optional raw simulation results
        output_path: Optional path to save the attestation to

    Returns:
        The signed attestation
    """
    # Create the attestation
    attestation = create_attestation(
        rev_range=rev_range,
        scenario=scenario,
        severity=severity,
        affected_services=affected_services,
        metrics=metrics,
        risk_score=risk_score,
        explanation=explanation,
        manifest_hash=manifest_hash,
        commit_target=commit_target,
        timestamp=timestamp,
        diff_hash=diff_hash,
        simulation_results=simulation_results
    )
    
    # Save the attestation
    save_attestation(attestation, output_path)
    
    return attestation
