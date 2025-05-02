"""Simulation functionality for Arc Memory.

This package provides functionality for simulating the impact of code changes
by running targeted fault injection experiments in isolated sandbox environments.
"""

from arc_memory.simulate.explanation_utils import (
    generate_explanation_from_module as generate_explanation
)

from arc_memory.simulate.analysis import (
    process_metrics,
    calculate_risk_score,
    identify_risk_factors
)

__all__ = [
    "process_metrics",
    "calculate_risk_score",
    "identify_risk_factors",
    "generate_explanation"
]
