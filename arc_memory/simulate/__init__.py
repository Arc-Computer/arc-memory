"""Simulation functionality for Arc Memory.

This package provides functionality for simulating the impact of code changes
by running targeted fault injection experiments in isolated sandbox environments.
"""

from arc_memory.simulate.explanation import (
    analyze_simulation_results,
    process_metrics,
    calculate_risk_score,
    generate_explanation
)

__all__ = [
    "analyze_simulation_results",
    "process_metrics",
    "calculate_risk_score",
    "generate_explanation"
]
