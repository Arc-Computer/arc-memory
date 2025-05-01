"""Attestation functionality for Arc Memory.

This package provides functionality for generating and verifying attestations
for simulation results, ensuring cryptographic verification of the simulation
process and outcomes.
"""

from arc_memory.attestation.write_attest import (
    create_attestation,
    generate_and_save_attestation,
    save_attestation,
    verify_attestation
)

__all__ = [
    "create_attestation",
    "generate_and_save_attestation",
    "save_attestation",
    "verify_attestation"
]
